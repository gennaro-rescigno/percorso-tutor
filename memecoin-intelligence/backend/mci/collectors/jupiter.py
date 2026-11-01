"""Jupiter aggregator: executable quotes, prices and swap transactions.

* Quote: ``GET {base}/swap/v1/quote?inputMint&outputMint&amount&slippageBps``
* Swap:  ``POST {base}/swap/v1/swap`` -> base64 serialized VersionedTransaction (unsigned)
* Price: ``GET {base}/price/v3?ids=`` (falls back to parsing the v2 shape)

Rate limits (2026 docs): keyless 0.5 RPS, free key 1 RPS. ``lite-api.jup.ag`` is being
phased out in favour of ``api.jup.ag`` (same paths) - both are configurable.

Quotes are the most realistic price source available for paper trading: they reflect
the real route, pool fees and price impact *for the exact amount* we would trade.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mci.domain import LAMPORTS_PER_SOL, SOL_MINT
from mci.utils.http import ApiClient, SourceUnavailable, fnum, inum


@dataclass
class Quote:
    input_mint: str
    output_mint: str
    in_amount: int  # raw units
    out_amount: int  # raw units
    other_amount_threshold: int
    price_impact_pct: float  # fraction, e.g. 0.012 = 1.2%
    slippage_bps: int
    route_labels: list[str]
    raw: dict[str, Any]


class JupiterCollector:
    def __init__(self, base_url: str, api_key: str = "", rps: float = 0.5, client: ApiClient | None = None):
        headers = {"x-api-key": api_key} if api_key else {}
        self.api = client or ApiClient("jupiter", base_url, rate_per_s=rps, burst=1, headers=headers)
        self._decimals: dict[str, int] = {SOL_MINT: 9}

    async def close(self) -> None:
        await self.api.close()

    async def quote(
        self, input_mint: str, output_mint: str, amount_raw: int, slippage_bps: int = 300
    ) -> Quote | None:
        if amount_raw <= 0:
            return None
        try:
            data = await self.api.get(
                "/swap/v1/quote",
                params={
                    "inputMint": input_mint,
                    "outputMint": output_mint,
                    "amount": str(int(amount_raw)),
                    "slippageBps": slippage_bps,
                    "restrictIntermediateTokens": "true",
                },
            )
        except SourceUnavailable as e:
            # 400 responses are how Jupiter reports "no route" -> treat as no quote
            if "HTTP 400" in e.detail:
                return None
            raise
        if not isinstance(data, dict) or "outAmount" not in data:
            return None
        impact = fnum(data.get("priceImpactPct"))
        return Quote(
            input_mint=input_mint,
            output_mint=output_mint,
            in_amount=inum(data.get("inAmount")) or amount_raw,
            out_amount=inum(data.get("outAmount")) or 0,
            other_amount_threshold=inum(data.get("otherAmountThreshold")) or 0,
            price_impact_pct=abs(impact) if impact is not None else 0.0,
            slippage_bps=inum(data.get("slippageBps")) or slippage_bps,
            route_labels=[
                ((r.get("swapInfo") or {}).get("label") or "?") for r in (data.get("routePlan") or [])
            ],
            raw=data,
        )

    async def buy_quote(self, token_mint: str, sol_amount: float, slippage_bps: int = 300) -> Quote | None:
        return await self.quote(SOL_MINT, token_mint, int(sol_amount * LAMPORTS_PER_SOL), slippage_bps)

    async def sell_quote(self, token_mint: str, token_raw_amount: int, slippage_bps: int = 300) -> Quote | None:
        return await self.quote(token_mint, SOL_MINT, int(token_raw_amount), slippage_bps)

    async def prices(self, mints: list[str]) -> dict[str, dict[str, float | None]]:
        """Return {mint: {"usd": price, "decimals": d}} for known mints (missing = absent)."""
        out: dict[str, dict[str, float | None]] = {}
        for i in range(0, len(mints), 50):
            chunk = mints[i : i + 50]
            data = await self.api.get("/price/v3", params={"ids": ",".join(chunk)})
            if not isinstance(data, dict):
                continue
            body = data.get("data") if isinstance(data.get("data"), dict) else data  # v2 vs v3 shape
            for mint, v in body.items():
                if not isinstance(v, dict):
                    continue
                price = fnum(v.get("usdPrice", v.get("price")))
                dec = inum(v.get("decimals"))
                if dec is not None:
                    self._decimals[mint] = dec
                out[mint] = {"usd": price, "decimals": dec}
        return out

    def known_decimals(self, mint: str) -> int | None:
        return self._decimals.get(mint)

    def remember_decimals(self, mint: str, decimals: int) -> None:
        self._decimals[mint] = decimals

    async def swap_transaction(self, quote: Quote, user_public_key: str, priority_fee_lamports: int) -> str:
        """Build (not sign, not send) a swap transaction. Returns base64 string."""
        data = await self.api.post(
            "/swap/v1/swap",
            json={
                "quoteResponse": quote.raw,
                "userPublicKey": user_public_key,
                "wrapAndUnwrapSol": True,
                "dynamicComputeUnitLimit": True,
                "prioritizationFeeLamports": int(priority_fee_lamports),
            },
        )
        tx = (data or {}).get("swapTransaction") if isinstance(data, dict) else None
        if not tx:
            raise SourceUnavailable("jupiter", "swap transaction missing in response")
        return tx
