"""SOL price in EUR/USD, refreshed dynamically (never a fixed conversion).

Primary: CoinGecko simple price (keyless, low rate limit).
Fallback: Kraken public ticker SOLEUR / SOLUSD.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from mci.utils.http import ApiClient, SourceUnavailable, fnum

log = logging.getLogger(__name__)


@dataclass
class SolPrice:
    eur: float | None
    usd: float | None
    source: str
    fetched_at: float

    @property
    def stale(self) -> bool:
        return time.time() - self.fetched_at > 15 * 60


class SolPriceFeed:
    def __init__(self, coingecko_url: str, kraken_url: str, ttl_s: float = 120.0):
        self.cg = ApiClient("coingecko", coingecko_url, rate_per_s=0.1, burst=1, max_retries=1)
        self.kr = ApiClient("kraken", kraken_url, rate_per_s=0.5, burst=1, max_retries=1)
        self.ttl_s = ttl_s
        self._last: SolPrice | None = None

    async def close(self) -> None:
        await self.cg.close()
        await self.kr.close()

    @property
    def last(self) -> SolPrice | None:
        return self._last

    async def get(self) -> SolPrice | None:
        if self._last and time.time() - self._last.fetched_at < self.ttl_s:
            return self._last
        price = await self._coingecko() or await self._kraken()
        if price:
            self._last = price
        return self._last  # may be stale; callers check .stale

    async def _coingecko(self) -> SolPrice | None:
        try:
            data = await self.cg.get("/simple/price", params={"ids": "solana", "vs_currencies": "eur,usd"})
        except SourceUnavailable as e:
            log.info("coingecko unavailable: %s", e)
            return None
        sol = (data or {}).get("solana") or {}
        eur, usd = fnum(sol.get("eur")), fnum(sol.get("usd"))
        if eur is None and usd is None:
            return None
        return SolPrice(eur=eur, usd=usd, source="coingecko", fetched_at=time.time())

    async def _kraken(self) -> SolPrice | None:
        out: dict[str, float | None] = {"eur": None, "usd": None}
        for cur, pair in (("eur", "SOLEUR"), ("usd", "SOLUSD")):
            try:
                data = await self.kr.get("/0/public/Ticker", params={"pair": pair})
            except SourceUnavailable:
                continue
            res = (data or {}).get("result") or {}
            for v in res.values():
                last = (v or {}).get("c") or [None]
                out[cur] = fnum(last[0])
        if out["eur"] is None and out["usd"] is None:
            return None
        return SolPrice(eur=out["eur"], usd=out["usd"], source="kraken", fetched_at=time.time())
