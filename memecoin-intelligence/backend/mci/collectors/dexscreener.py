"""DexScreener public API collector.

Endpoints used (public, no key). Documented limits: 60 rpm for profile/boost
endpoints, 300 rpm for pair endpoints (third-party docs, verify with
``mci check-sources``):

* ``GET /token-profiles/latest/v1``      latest token profiles (paid listing info)
* ``GET /token-boosts/latest/v1``         latest boosted tokens (paid promotion)
* ``GET /token-boosts/top/v1``            most boosted tokens
* ``GET /tokens/v1/{chainId}/{addrs}``    pairs for up to 30 token addresses
* ``GET /latest/dex/pairs/{chainId}/{pairAddress}``
* ``GET /latest/dex/search?q=``

DexScreener does NOT provide 15-minute windows or unique buyers; those come from
GeckoTerminal or are derived from our own snapshots.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from mci.domain import TokenSnapshot, utcnow
from mci.utils.http import ApiClient, fnum, inum

SOL_QUOTES = {"SOL", "WSOL"}


class DexScreenerCollector:
    def __init__(self, base_url: str, client: ApiClient | None = None):
        # 300 rpm on pair endpoints -> stay at 4/s with burst; profile endpoints are called rarely
        self.api = client or ApiClient("dexscreener", base_url, rate_per_s=3.0, burst=5)

    async def close(self) -> None:
        await self.api.close()

    async def latest_profiles(self) -> list[dict[str, Any]]:
        data = await self.api.get("/token-profiles/latest/v1")
        return data if isinstance(data, list) else []

    async def latest_boosts(self) -> list[dict[str, Any]]:
        data = await self.api.get("/token-boosts/latest/v1")
        return data if isinstance(data, list) else []

    async def top_boosts(self) -> list[dict[str, Any]]:
        data = await self.api.get("/token-boosts/top/v1")
        return data if isinstance(data, list) else []

    async def pairs_for_tokens(self, chain: str, addresses: list[str]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for i in range(0, len(addresses), 30):
            chunk = addresses[i : i + 30]
            data = await self.api.get(f"/tokens/v1/{chain}/{','.join(chunk)}")
            if isinstance(data, list):
                out.extend(p for p in data if isinstance(p, dict))
            elif isinstance(data, dict) and isinstance(data.get("pairs"), list):
                out.extend(data["pairs"])
        return out

    async def pair(self, chain: str, pair_address: str) -> dict[str, Any] | None:
        data = await self.api.get(f"/latest/dex/pairs/{chain}/{pair_address}", allow_404=True)
        if isinstance(data, dict):
            pairs = data.get("pairs") or ([data["pair"]] if data.get("pair") else [])
            return pairs[0] if pairs else None
        return None

    async def search(self, query: str) -> list[dict[str, Any]]:
        data = await self.api.get("/latest/dex/search", params={"q": query})
        return (data or {}).get("pairs") or [] if isinstance(data, dict) else []

    # ----------------------------------------------------------------------------
    @staticmethod
    def best_pair_per_token(pairs: list[dict[str, Any]], chain: str = "solana") -> dict[str, dict[str, Any]]:
        """Pick the most liquid pair for each base token (prefer SOL-quoted pairs)."""
        best: dict[str, dict[str, Any]] = {}
        for p in pairs:
            if p.get("chainId") != chain:
                continue
            base = (p.get("baseToken") or {}).get("address")
            if not base:
                continue
            liq = fnum((p.get("liquidity") or {}).get("usd")) or 0.0
            quote_sym = ((p.get("quoteToken") or {}).get("symbol") or "").upper()
            key = (quote_sym in SOL_QUOTES, liq)
            cur = best.get(base)
            if cur is None:
                best[base] = p
                continue
            cur_liq = fnum((cur.get("liquidity") or {}).get("usd")) or 0.0
            cur_key = (((cur.get("quoteToken") or {}).get("symbol") or "").upper() in SOL_QUOTES, cur_liq)
            if key > cur_key:
                best[base] = p
        return best

    @staticmethod
    def pair_to_snapshot(p: dict[str, Any], observed_at: datetime | None = None) -> TokenSnapshot:
        base = p.get("baseToken") or {}
        quote = p.get("quoteToken") or {}
        txns = p.get("txns") or {}
        vol = p.get("volume") or {}
        chg = p.get("priceChange") or {}
        liq = p.get("liquidity") or {}
        info = p.get("info") or {}
        created_ms = inum(p.get("pairCreatedAt"))
        created = datetime.fromtimestamp(created_ms / 1000, tz=timezone.utc) if created_ms else None
        quote_sym = (quote.get("symbol") or "").upper()

        socials: dict[str, str] = {}
        for s in info.get("socials") or []:
            t, u = (s.get("type") or "").lower(), s.get("url")
            if t and u:
                socials[t] = u
        for w in info.get("websites") or []:
            if w.get("url"):
                socials.setdefault("website", w["url"])

        windows = {"m5": "m5", "h1": "h1", "h6": "h6", "h24": "h24"}
        snap = TokenSnapshot(
            chain=p.get("chainId") or "solana",
            token_address=base.get("address", ""),
            observed_at=observed_at or utcnow(),
            symbol=base.get("symbol"),
            name=base.get("name"),
            pair_address=p.get("pairAddress"),
            dex_id=(p.get("dexId") or "").lower() or None,
            quote_symbol=quote_sym or None,
            created_at=created,
            price_usd=fnum(p.get("priceUsd")),
            price_native=fnum(p.get("priceNative")) if quote_sym in SOL_QUOTES else None,
            market_cap_usd=fnum(p.get("marketCap")),
            fdv_usd=fnum(p.get("fdv")),
            liquidity_usd=fnum(liq.get("usd")),
            liquidity_quote=fnum(liq.get("quote")) if quote_sym in SOL_QUOTES else None,
            volume_usd={w: fnum(vol.get(k)) for w, k in windows.items()},
            buys={w: inum((txns.get(k) or {}).get("buys")) for w, k in windows.items()},
            sells={w: inum((txns.get(k) or {}).get("sells")) for w, k in windows.items()},
            price_change_pct={w: fnum(chg.get(k)) for w, k in windows.items()},
            socials=socials,
            has_profile=bool(info) or None,
            boosts_active=inum((p.get("boosts") or {}).get("active")),
        )
        snap.sources["market"] = "dexscreener"
        return snap
