"""Resilient async HTTP client: per-source rate limiting, retries with backoff,
and a circuit breaker so an unavailable API never blocks the whole system."""

from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass
from typing import Any

import httpx

log = logging.getLogger(__name__)


class SourceUnavailable(Exception):
    """Raised when a data source cannot be reached or returned an unusable answer."""

    def __init__(self, source: str, detail: str):
        super().__init__(f"{source}: {detail}")
        self.source = source
        self.detail = detail


class RateLimiter:
    """Token bucket. ``rate`` tokens per second, ``burst`` maximum stored tokens."""

    def __init__(self, rate: float, burst: float | None = None):
        if rate <= 0:
            raise ValueError("rate must be > 0")
        self.rate = rate
        self.capacity = burst if burst is not None else max(1.0, rate)
        self._tokens = self.capacity
        self._last = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            while True:
                now = time.monotonic()
                self._tokens = min(self.capacity, self._tokens + (now - self._last) * self.rate)
                self._last = now
                if self._tokens >= 1:
                    self._tokens -= 1
                    return
                await asyncio.sleep((1 - self._tokens) / self.rate)


@dataclass
class CircuitBreaker:
    failure_threshold: int = 5
    reset_after_s: float = 120.0
    failures: int = 0
    opened_at: float | None = None

    def allow(self) -> bool:
        if self.opened_at is None:
            return True
        if time.monotonic() - self.opened_at >= self.reset_after_s:
            # half-open: allow one trial
            self.opened_at = None
            self.failures = self.failure_threshold - 1
            return True
        return False

    def record_success(self) -> None:
        self.failures = 0
        self.opened_at = None

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.opened_at = time.monotonic()

    @property
    def is_open(self) -> bool:
        return self.opened_at is not None


class ApiClient:
    """Thin wrapper around ``httpx.AsyncClient`` bound to one data source."""

    def __init__(
        self,
        source: str,
        base_url: str,
        *,
        rate_per_s: float,
        burst: float | None = None,
        timeout_s: float = 15.0,
        max_retries: int = 3,
        headers: dict[str, str] | None = None,
        client: httpx.AsyncClient | None = None,
    ):
        self.source = source
        self.base_url = base_url.rstrip("/")
        self.limiter = RateLimiter(rate_per_s, burst)
        self.breaker = CircuitBreaker()
        self.max_retries = max_retries
        self._own_client = client is None
        self._client = client or httpx.AsyncClient(timeout=timeout_s, headers=headers or {})
        self._headers = headers or {}
        self.stats = {"ok": 0, "errors": 0, "rate_limited": 0}

    async def close(self) -> None:
        if self._own_client:
            await self._client.aclose()

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        headers: dict[str, str] | None = None,
        allow_404: bool = False,
    ) -> Any:
        if not self.breaker.allow():
            raise SourceUnavailable(self.source, "circuit open (too many recent failures)")
        url = path if path.startswith("http") else f"{self.base_url}/{path.lstrip('/')}"
        last_err = "unknown error"
        for attempt in range(self.max_retries + 1):
            await self.limiter.acquire()
            try:
                resp = await self._client.request(
                    method, url, params=params, json=json, headers={**self._headers, **(headers or {})}
                )
            except (httpx.TimeoutException, httpx.TransportError) as e:
                last_err = f"transport error: {type(e).__name__}"
            else:
                if resp.status_code == 404 and allow_404:
                    self.breaker.record_success()
                    return None
                if resp.status_code == 429:
                    self.stats["rate_limited"] += 1
                    retry_after = resp.headers.get("retry-after")
                    wait = float(retry_after) if retry_after and retry_after.isdigit() else 2 ** attempt * 2
                    last_err = "rate limited (429)"
                    await asyncio.sleep(min(wait, 30))
                    continue
                if 500 <= resp.status_code < 600:
                    last_err = f"server error {resp.status_code}"
                elif resp.status_code >= 400:
                    self.stats["errors"] += 1
                    self.breaker.record_failure()
                    raise SourceUnavailable(self.source, f"HTTP {resp.status_code}")
                else:
                    try:
                        data = resp.json()
                    except ValueError:
                        last_err = "invalid JSON"
                    else:
                        self.stats["ok"] += 1
                        self.breaker.record_success()
                        return data
            if attempt < self.max_retries:
                await asyncio.sleep(min(2 ** attempt + random.random(), 20))
        self.stats["errors"] += 1
        self.breaker.record_failure()
        raise SourceUnavailable(self.source, last_err)

    async def get(self, path: str, **kw: Any) -> Any:
        return await self.request("GET", path, **kw)

    async def post(self, path: str, **kw: Any) -> Any:
        return await self.request("POST", path, **kw)


def fnum(x: Any) -> float | None:
    """Parse a number that APIs often send as string. Returns None if not parseable/finite."""
    if x is None or isinstance(x, bool):
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if v != v or v in (float("inf"), float("-inf")):
        return None
    return v


def inum(x: Any) -> int | None:
    v = fnum(x)
    return int(v) if v is not None else None
