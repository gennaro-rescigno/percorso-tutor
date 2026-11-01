"""GeckoTerminal public API collector (CoinGecko on-chain data).

Documented public limit: 30 calls/minute. Free plan OHLCV history: up to 6 months
per request window, with ``before_timestamp`` pagination (paid plans go further).

Endpoints used:
* ``GET /networks/{network}/new_pools?page=N``
* ``GET /networks/{network}/trending_pools``
* ``GET /networks/{network}/pools/{address}``
* ``GET /networks/{network}/pools/{address}/ohlcv/{timeframe}`` (minute|hour|day + aggregate)
* ``GET /networks/{network}/pools/{address}/trades``
* ``GET /networks/{network}/tokens/{address}/info``

Gecko adds what DexScreener lacks: 15m/30m windows and *unique* buyers/sellers.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from mci.domain import Candle, TokenSnapshot, to_utc, utcnow
from mci.utils.http import ApiClient, fnum, inum

ACCEPT = {"Accept": "application/json;version=20230302"}

TIMEFRAMES = {
    "1m": ("minute", 1),
    "5m": ("minute", 5),
    "15m": ("minute", 15),
    "1h": ("hour", 1),
    "4h": ("hour", 4),
    "1d": ("day", 1),
}


def _parse_dt(s: Any) -> datetime | None:
    if not s or not isinstance(s, str):
        return None
    try:
        return to_utc(datetime.fromisoformat(s.replace("Z", "+00:00")))
    except ValueError:
        return None


def _strip_prefix(gid: str | None) -> str | None:
    # Gecko ids look like "solana_<address>"
    if not gid:
        return None
    return gid.split("_", 1)[1] if "_" in gid else gid


class GeckoTerminalCollector:
    def __init__(self, base_url: str, calls_per_minute: int = 12, client: ApiClient | None = None):
        # evenly spaced calls (no bursts): the public API answered 429 to short bursts even from a dedicated IP
        self.api = client or ApiClient(
            "geckoterminal", base_url, rate_per_s=calls_per_minute / 60.0, burst=1, headers=ACCEPT
        )

    async def close(self) -> None:
        await self.api.close()

    async def new_pools(self, network: str = "solana", page: int = 1) -> list[dict[str, Any]]:
        data = await self.api.get(
            f"/networks/{network}/new_pools", params={"page": page, "include": "base_token,quote_token,dex"}
        )
        return (data or {}).get("data") or []

    async def trending_pools(self, network: str = "solana", page: int = 1, duration: str = "1h") -> list[dict]:
        data = await self.api.get(
            f"/networks/{network}/trending_pools", params={"page": page, "duration": duration}
        )
        return (data or {}).get("data") or []

    async def pool(self, pool_address: str, network: str = "solana") -> dict[str, Any] | None:
        data = await self.api.get(f"/networks/{network}/pools/{pool_address}", allow_404=True)
        return (data or {}).get("data") if data else None

    async def token_pools(self, token_address: str, network: str = "solana") -> list[dict[str, Any]]:
        """Pools trading a token (``GET /networks/{network}/tokens/{address}/pools``)."""
        data = await self.api.get(f"/networks/{network}/tokens/{token_address}/pools",
                                  params={"include": "dex"}, allow_404=True)
        return (data or {}).get("data") or [] if data else []

    async def ohlcv_window(self, pool_address: str, timeframe: str, start_ts: int, end_ts: int, *,
                           network: str = "solana", currency: str = "token", max_pages: int = 10) -> list[Candle]:
        """Candles in [start_ts, end_ts], paging backwards from end_ts."""
        out: dict[int, Candle] = {}
        before = int(end_ts)
        for _ in range(max_pages):
            batch = await self.ohlcv(pool_address, timeframe, network=network, before_timestamp=before,
                                     currency=currency)
            if not batch:
                break
            for c in batch:
                if start_ts <= c.ts <= end_ts:
                    out[c.ts] = c
            oldest = batch[0].ts
            if oldest <= start_ts or oldest >= before:
                break
            before = oldest
        return [out[k] for k in sorted(out)]

    async def token_info(self, token_address: str, network: str = "solana") -> dict[str, Any] | None:
        data = await self.api.get(f"/networks/{network}/tokens/{token_address}/info", allow_404=True)
        return (data or {}).get("data") if data else None

    async def trades(self, pool_address: str, network: str = "solana", min_usd: float = 0) -> list[dict]:
        data = await self.api.get(
            f"/networks/{network}/pools/{pool_address}/trades",
            params={"trade_volume_in_usd_greater_than": min_usd},
            allow_404=True,
        )
        return (data or {}).get("data") or [] if data else []

    async def ohlcv(
        self,
        pool_address: str,
        timeframe: str = "1m",
        *,
        network: str = "solana",
        before_timestamp: int | None = None,
        limit: int = 1000,
        currency: str = "usd",
    ) -> list[Candle]:
        """Candles oldest -> newest. ``currency='token'`` returns prices in the quote token."""
        tf, agg = TIMEFRAMES[timeframe]
        params: dict[str, Any] = {"aggregate": agg, "limit": limit, "currency": currency}
        if before_timestamp:
            params["before_timestamp"] = int(before_timestamp)
        data = await self.api.get(
            f"/networks/{network}/pools/{pool_address}/ohlcv/{tf}", params=params, allow_404=True
        )
        rows = (((data or {}).get("data") or {}).get("attributes") or {}).get("ohlcv_list") or []
        candles = []
        for r in rows:
            if not isinstance(r, (list, tuple)) or len(r) < 6:
                continue
            c = Candle(int(r[0]), *(fnum(x) or 0.0 for x in r[1:6]))
            if c.is_valid():
                candles.append(c)
        return sorted({c.ts: c for c in candles}.values(), key=lambda c: c.ts)  # dedupe repeated timestamps

    async def ohlcv_history(
        self, pool_address: str, timeframe: str, since_ts: int, *, network: str = "solana",
        currency: str = "usd", max_pages: int = 50,
    ) -> list[Candle]:
        """Page backwards with ``before_timestamp`` until ``since_ts`` or no more data."""
        out: dict[int, Candle] = {}
        before: int | None = None
        for _ in range(max_pages):
            batch = await self.ohlcv(
                pool_address, timeframe, network=network, before_timestamp=before, currency=currency
            )
            if not batch:
                break
            for c in batch:
                out[c.ts] = c
            oldest = batch[0].ts
            if oldest <= since_ts or (before is not None and oldest >= before):
                break
            before = oldest
        return [out[k] for k in sorted(out) if k >= since_ts]

    # ----------------------------------------------------------------------------
    @staticmethod
    def pool_to_snapshot(pool: dict[str, Any], observed_at: datetime | None = None) -> TokenSnapshot:
        a = pool.get("attributes") or {}
        rel = pool.get("relationships") or {}
        base_id = ((rel.get("base_token") or {}).get("data") or {}).get("id")
        dex_id = ((rel.get("dex") or {}).get("data") or {}).get("id")
        tx = a.get("transactions") or {}
        vol = a.get("volume_usd") or {}
        chg = a.get("price_change_percentage") or {}
        windows = ("m5", "m15", "h1", "h6", "h24")
        name = a.get("name") or ""
        symbol = name.split("/")[0].strip() if "/" in name else None
        quote_sym = name.split("/")[1].strip().upper() if "/" in name else None
        snap = TokenSnapshot(
            chain="solana",
            token_address=_strip_prefix(base_id) or "",
            observed_at=observed_at or utcnow(),
            symbol=symbol,
            pair_address=a.get("address"),
            dex_id=(dex_id or "").lower() or None,
            quote_symbol=quote_sym,
            created_at=_parse_dt(a.get("pool_created_at")),
            price_usd=fnum(a.get("base_token_price_usd")),
            price_native=fnum(a.get("base_token_price_quote_token")) if quote_sym in ("SOL", "WSOL") else None,
            market_cap_usd=fnum(a.get("market_cap_usd")),
            fdv_usd=fnum(a.get("fdv_usd")),
            liquidity_usd=fnum(a.get("reserve_in_usd")),
            volume_usd={w: fnum(vol.get(w)) for w in windows},
            buys={w: inum((tx.get(w) or {}).get("buys")) for w in windows},
            sells={w: inum((tx.get(w) or {}).get("sells")) for w in windows},
            buyers={w: inum((tx.get(w) or {}).get("buyers")) for w in windows},
            sellers={w: inum((tx.get(w) or {}).get("sellers")) for w in windows},
            price_change_pct={w: fnum(chg.get(w)) for w in windows},
        )
        snap.sources["market_gecko"] = "geckoterminal"
        return snap

    @staticmethod
    def apply_token_info(snap: TokenSnapshot, info: dict[str, Any] | None) -> TokenSnapshot:
        """Token info may include holders count and distribution (fields parsed defensively)."""
        if not info:
            return snap
        a = info.get("attributes") or {}
        holders = a.get("holders") or {}
        if isinstance(holders, dict):
            cnt = inum(holders.get("count"))
            if cnt is not None:
                snap.holders_count = cnt
                snap.sources["holders_count"] = "geckoterminal"
            dist = holders.get("distribution_percentage") or {}
            top10 = fnum(dist.get("top_10"))
            # Gecko's top_10 may include pools; only used if RugCheck/RPC analysis is unavailable.
            if top10 is not None and snap.top10_pct is None:
                snap.social_metrics["gecko_top10_pct_raw"] = top10
        for k in ("mint_authority", "freeze_authority"):
            v = a.get(k)
            if isinstance(v, str):
                revoked = v.lower() in ("no", "none", "revoked", "")
                if k == "mint_authority" and snap.mint_authority_revoked is None:
                    snap.mint_authority_revoked = revoked
                    snap.sources["mint_authority"] = "geckoterminal"
                if k == "freeze_authority" and snap.freeze_authority_revoked is None:
                    snap.freeze_authority_revoked = revoked
                    snap.sources["freeze_authority"] = "geckoterminal"
        for k in ("twitter_handle", "telegram_handle", "websites"):
            v = a.get(k)
            if isinstance(v, str) and v:
                snap.socials.setdefault(k.replace("_handle", ""), v)
            elif isinstance(v, list) and v:
                snap.socials.setdefault("website", v[0])
        return snap

    @staticmethod
    def parse_trades(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Normalize trade rows to {ts, wallet, side, usd, tx}."""
        out = []
        for r in rows:
            a = r.get("attributes") or {}
            ts = _parse_dt(a.get("block_timestamp"))
            if ts is None:
                continue
            out.append(
                {
                    "ts": ts,
                    "wallet": a.get("tx_from_address"),
                    "side": (a.get("kind") or "").lower(),
                    "usd": fnum(a.get("volume_in_usd")) or 0.0,
                    "tx": a.get("tx_hash"),
                }
            )
        out.sort(key=lambda t: t["ts"])
        return out
