"""Solana JSON-RPC pool for the analytics side (security, wallet intelligence, simulations).

Free public endpoints are rate limited per IP (api.mainnet-beta: 100 requests / 10 s, 40 / 10 s per method,
heavier methods throttle earlier). The pool therefore:

* keeps per-endpoint pacing and cool-downs after 429 / transport errors (failover to the next endpoint);
* enforces per-method budgets per minute, so wallet analysis can never starve the security checks;
* caches read results with a per-method TTL;
* counts everything (calls, cache hits, 429s, budget refusals) for the "Salute del sistema" page.

Endpoint URLs may contain API keys (optional free plans the owner adds): they are never logged or exported,
endpoints are reported as ``rpc#1``, ``rpc#2``...
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from typing import Any

import httpx

from mci.utils.http import RateLimiter, SourceUnavailable

log = logging.getLogger(__name__)

# per-method budget (calls per minute) on the whole pool
DEFAULT_BUDGETS = {
    "getAccountInfo": 60,
    "getMultipleAccounts": 30,
    "getTransaction": 40,
    "getSignaturesForAddress": 30,
    "getTokenLargestAccounts": 6,
    "getTokenAccountsByOwner": 20,
    "simulateTransaction": 10,
    "getRecentPrioritizationFees": 4,
    "getBalance": 30,
}
# cache TTL (seconds) for read methods
DEFAULT_TTL = {
    "getAccountInfo": 60.0,
    "getMultipleAccounts": 30.0,
    "getTransaction": 86400.0,  # finalized transactions never change
    "getSignaturesForAddress": 300.0,
    "getTokenLargestAccounts": 120.0,
    "getRecentPrioritizationFees": 30.0,
}
RATE_LIMIT_CODES = {-32005, -32429, 429}


class BudgetExceeded(SourceUnavailable):
    pass


@dataclass
class Endpoint:
    url: str
    name: str
    limiter: RateLimiter
    cooldown_until: float = 0.0
    strikes: int = 0
    stats: dict[str, int] = field(default_factory=lambda: {"ok": 0, "rate_limited": 0, "errors": 0})

    @property
    def available(self) -> bool:
        return time.monotonic() >= self.cooldown_until

    def penalize(self, base: float) -> None:
        self.strikes += 1
        self.cooldown_until = time.monotonic() + min(base * 2 ** (self.strikes - 1), 300.0)


class RpcPool:
    def __init__(self, urls: list[str], rps: float = 2.0, budgets: dict[str, int] | None = None,
                 ttl: dict[str, float] | None = None, client: httpx.AsyncClient | None = None,
                 timeout_s: float = 20.0, cache_size: int = 5000, extra_rps: float | None = None):
        urls = [u for u in dict.fromkeys(u.strip() for u in urls) if u]
        if not urls:
            raise ValueError("at least one RPC endpoint is required")
        self.endpoints = [Endpoint(u, f"rpc#{i + 1}", RateLimiter(rps if i == 0 or extra_rps is None else extra_rps, 2))
                          for i, u in enumerate(urls)]
        self.budgets = {**DEFAULT_BUDGETS, **(budgets or {})}
        self.ttl = {**DEFAULT_TTL, **(ttl or {})}
        self._calls: dict[str, deque] = {}
        self._cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._cache_size = cache_size
        self._own = client is None
        self._client = client or httpx.AsyncClient(timeout=timeout_s)
        self._id = 0
        self.stats: dict[str, Any] = {"calls": 0, "cache_hits": 0, "budget_refused": 0, "failed": 0, "by_method": {}}
        self.last_errors: dict[str, str] = {}  # method -> last failure (shown on the system health page)

    async def close(self) -> None:
        if self._own:
            await self._client.aclose()

    # ------------------------------------------------------------------ budget / cache
    def budget_left(self, method: str) -> int:
        limit = self.budgets.get(method)
        if limit is None:
            return 1_000_000
        q = self._calls.setdefault(method, deque())
        now = time.monotonic()
        while q and now - q[0] > 60:
            q.popleft()
        return max(limit - len(q), 0)

    def _spend(self, method: str) -> None:
        self._calls.setdefault(method, deque()).append(time.monotonic())

    def _cache_get(self, key: str) -> tuple[bool, Any]:
        hit = self._cache.get(key)
        if hit and hit[0] > time.monotonic():
            self._cache.move_to_end(key)
            return True, hit[1]
        if hit:
            del self._cache[key]
        return False, None

    def _cache_put(self, key: str, ttl: float, value: Any) -> None:
        self._cache[key] = (time.monotonic() + ttl, value)
        self._cache.move_to_end(key)
        while len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)

    # ------------------------------------------------------------------ calls
    async def call(self, method: str, params: list[Any] | None = None, *, cache_ttl: float | None = None) -> Any:
        params = params or []
        ttl = self.ttl.get(method) if cache_ttl is None else cache_ttl
        key = method + json.dumps(params, sort_keys=True, separators=(",", ":"))
        if ttl:
            hit, val = self._cache_get(key)
            if hit:
                self.stats["cache_hits"] += 1
                return val
        if self.budget_left(method) <= 0:
            self.stats["budget_refused"] += 1
            raise BudgetExceeded("solana_rpc", f"budget per minuto esaurito per {method}")
        self._spend(method)
        m = self.stats["by_method"].setdefault(method, 0)
        self.stats["by_method"][method] = m + 1
        self.stats["calls"] += 1
        last = "no endpoint available"
        order = sorted(self.endpoints, key=lambda e: (not e.available, e.strikes))
        for ep in order:
            if not ep.available and ep is not order[0]:
                continue
            if not ep.available:  # every endpoint is cooling down: wait for the first one (bounded)
                wait = ep.cooldown_until - time.monotonic()
                if wait > 15:
                    break
                await asyncio.sleep(max(wait, 0))
            await ep.limiter.acquire()
            self._id += 1
            try:
                resp = await self._client.post(ep.url, json={"jsonrpc": "2.0", "id": self._id, "method": method,
                                                             "params": params})
            except (httpx.TimeoutException, httpx.TransportError) as e:
                ep.stats["errors"] += 1
                ep.penalize(10.0)
                last = f"{ep.name}: {type(e).__name__}"
                continue
            if resp.status_code == 429:
                ep.stats["rate_limited"] += 1
                ep.penalize(20.0)
                last = f"{ep.name}: 429"
                continue
            if resp.status_code >= 500:
                ep.stats["errors"] += 1
                ep.penalize(10.0)
                last = f"{ep.name}: HTTP {resp.status_code}"
                continue
            try:
                data = resp.json()
            except ValueError:
                ep.stats["errors"] += 1
                ep.penalize(10.0)
                last = f"{ep.name}: invalid JSON"
                continue
            err = data.get("error") if isinstance(data, dict) else {"message": "invalid response"}
            if err:
                code = err.get("code") if isinstance(err, dict) else None
                msg = str((err or {}).get("message", err))[:160] if isinstance(err, dict) else str(err)[:160]
                if code in RATE_LIMIT_CODES or "rate" in msg.lower() or "too many" in msg.lower():
                    ep.stats["rate_limited"] += 1
                    ep.penalize(20.0)
                    last = f"{ep.name}: {msg}"
                    continue
                ep.stats["ok"] += 1  # the endpoint works; the request itself is invalid
                self.stats["failed"] += 1
                self.last_errors[method] = f"rpc error {code}: {msg}"[:200]
                raise SourceUnavailable("solana_rpc", f"rpc error {code}: {msg}")
            ep.stats["ok"] += 1
            ep.strikes = 0
            result = data.get("result")
            if ttl:
                self._cache_put(key, ttl, result)
            return result
        self.stats["failed"] += 1
        self.last_errors[method] = last[:200]
        raise SourceUnavailable("solana_rpc", last)

    def health(self) -> dict[str, Any]:
        return {
            **{k: v for k, v in self.stats.items() if k != "by_method"},
            "by_method": dict(self.stats["by_method"]),
            "budget_left": {m: self.budget_left(m) for m in self.budgets},
            "last_errors": dict(self.last_errors),
            "endpoints": [{"name": e.name, "available": e.available, **e.stats} for e in self.endpoints],
        }

    # ------------------------------------------------------------------ helpers
    async def account(self, pubkey: str, encoding: str = "jsonParsed") -> dict[str, Any] | None:
        res = await self.call("getAccountInfo", [pubkey, {"encoding": encoding, "commitment": "confirmed"}])
        return (res or {}).get("value")

    async def multiple_accounts(self, pubkeys: list[str], encoding: str = "base64") -> list[dict[str, Any] | None]:
        res = await self.call("getMultipleAccounts", [pubkeys, {"encoding": encoding, "commitment": "confirmed"}])
        return list((res or {}).get("value") or [None] * len(pubkeys))

    async def transaction(self, signature: str) -> dict[str, Any] | None:
        return await self.call("getTransaction", [signature, {"encoding": "jsonParsed", "commitment": "confirmed",
                                                              "maxSupportedTransactionVersion": 1}])

    async def signatures(self, address: str, limit: int = 1000, before: str | None = None) -> list[dict[str, Any]]:
        opts: dict[str, Any] = {"limit": limit, "commitment": "confirmed"}
        if before:
            opts["before"] = before
        return list(await self.call("getSignaturesForAddress", [address, opts]) or [])

    async def largest_accounts(self, mint: str) -> list[dict[str, Any]]:
        res = await self.call("getTokenLargestAccounts", [mint, {"commitment": "confirmed"}])
        return list((res or {}).get("value") or [])

    async def token_balance_raw(self, owner: str, mint: str) -> int:
        res = await self.call("getTokenAccountsByOwner", [owner, {"mint": mint}, {"encoding": "jsonParsed",
                                                                                 "commitment": "confirmed"}],
                              cache_ttl=0)
        total = 0
        for acc in (res or {}).get("value") or []:
            info = (((acc.get("account") or {}).get("data") or {}).get("parsed") or {}).get("info") or {}
            try:
                total += int((info.get("tokenAmount") or {}).get("amount") or 0)
            except (TypeError, ValueError):
                pass
        return total

    async def priority_fees(self, accounts: list[str] | None = None) -> list[int]:
        res = await self.call("getRecentPrioritizationFees", [accounts or []])
        return [int(x.get("prioritizationFee") or 0) for x in (res or []) if isinstance(x, dict)]

    async def simulate(self, tx_base64: str) -> dict[str, Any] | None:
        res = await self.call("simulateTransaction", [tx_base64, {"encoding": "base64", "sigVerify": False,
                                                                  "replaceRecentBlockhash": True,
                                                                  "commitment": "confirmed"}], cache_ttl=0)
        return (res or {}).get("value")
