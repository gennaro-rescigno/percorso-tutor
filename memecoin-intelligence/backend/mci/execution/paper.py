"""Paper executor: simulates fills with REAL observed liquidity.

Price source priority:
1. Jupiter quote for the exact amount (real route, pool fees and price impact);
2. constant-product AMM model on the observed pool reserve (labelled ``amm_model``);
3. otherwise the order fails: we never invent a price.

Extra realism: configurable landing slippage (price moves between quote and block
inclusion) and a small simulated transaction failure rate (fees are still charged).
"""

from __future__ import annotations

import logging
import random

from mci.collectors.jupiter import JupiterCollector
from mci.collectors.solana_rpc import SolanaRpc
from mci.domain import LAMPORTS_PER_SOL, Fill, utcnow
from mci.execution.base import ExecResult, Executor, TradeRequest
from mci.execution.costs import CostModel, amm_buy, amm_sell, dex_fee
from mci.utils.http import SourceUnavailable

log = logging.getLogger(__name__)


class PaperExecutor(Executor):
    mode = "paper"

    def __init__(
        self,
        costs: CostModel,
        jupiter: JupiterCollector | None = None,
        rpc: SolanaRpc | None = None,
        *,
        landing_slippage_pct: float = 0.003,
        failure_rate: float = 0.02,
        seed: int | None = None,
    ):
        self.costs = costs
        self.jupiter = jupiter
        self.rpc = rpc
        self.landing_slippage_pct = landing_slippage_pct
        self.failure_rate = failure_rate
        self.rng = random.Random(seed)

    async def _decimals(self, mint: str, hint: int | None) -> int | None:
        if hint is not None:
            return hint
        if self.jupiter and (d := self.jupiter.known_decimals(mint)) is not None:
            return d
        if self.rpc:
            try:
                info = await self.rpc.mint_info(mint)
            except SourceUnavailable:
                return None
            if info and info.get("decimals") is not None:
                if self.jupiter:
                    self.jupiter.remember_decimals(mint, info["decimals"])
                return info["decimals"]
        return None

    async def execute(self, req: TradeRequest) -> ExecResult:
        network = self.costs.network_fee_sol
        if self.rng.random() < self.failure_rate:
            return ExecResult(
                ok=False, error="transazione fallita (simulazione paper)", simulated_failure=True,
                fill=Fill(side=req.side, qty=0.0, price=0.0, sol_amount=0.0, dex_fee_sol=0.0,
                          network_fee_sol=network, slippage_sol=0.0, price_impact_pct=0.0, quote_source="none"),
            )
        if req.side == "buy":
            return await self._buy(req)
        return await self._sell(req)

    async def _buy(self, req: TradeRequest) -> ExecResult:
        amt = float(req.sol_amount or 0)
        if amt <= 0:
            return ExecResult(False, error="importo non valido")
        fee_pct = dex_fee(req.dex_id, req.market_cap_usd)
        rent = self.costs.ata_rent_sol if req.first_buy else 0.0
        decimals = await self._decimals(req.token, req.decimals)
        if self.jupiter and decimals is not None:
            try:
                q = await self.jupiter.buy_quote(req.token, amt, req.slippage_bps)
            except SourceUnavailable as e:
                q = None
                log.info("jupiter quote unavailable: %s", e)
            if q and q.out_amount > 0:
                qty = q.out_amount / 10**decimals * (1 - self.landing_slippage_pct)
                price = amt / qty
                ref = req.reference_price or price
                fee = amt * fee_pct  # embedded in the quote; reported separately as an estimate
                return ExecResult(
                    True,
                    Fill(side="buy", qty=qty, price=price, sol_amount=amt, dex_fee_sol=fee,
                         network_fee_sol=self.costs.network_fee_sol, slippage_sol=amt - fee - qty * ref,
                         price_impact_pct=q.price_impact_pct, quote_source="jupiter", rent_sol=rent, ts=utcnow()),
                    quote={"in": q.in_amount, "out": q.out_amount, "impact": q.price_impact_pct, "route": q.route_labels},
                    extra={"decimals": decimals},
                )
        if req.reserve_sol and req.reference_price:
            mid = req.reference_price * (1 + self.landing_slippage_pct)
            f = amm_buy(amt, req.reserve_sol, mid, fee_pct)
            if f.out_amount > 0:
                return ExecResult(
                    True,
                    Fill(side="buy", qty=f.out_amount, price=f.effective_price, sol_amount=amt, dex_fee_sol=f.fee_paid,
                         network_fee_sol=self.costs.network_fee_sol,
                         slippage_sol=amt - f.fee_paid - f.out_amount * req.reference_price,
                         price_impact_pct=f.impact_pct, quote_source="amm_model", rent_sol=rent, ts=utcnow()),
                    extra={"decimals": decimals},
                )
        return ExecResult(False, error="nessuna quote reale e liquidità sconosciuta: ordine non simulabile")

    async def _sell(self, req: TradeRequest) -> ExecResult:
        qty = float(req.qty or 0)
        if qty <= 0:
            return ExecResult(False, error="quantità non valida")
        fee_pct = dex_fee(req.dex_id, req.market_cap_usd)
        rent_refund = -self.costs.ata_rent_sol if req.close_account else 0.0
        decimals = await self._decimals(req.token, req.decimals)
        ref = req.reference_price
        if self.jupiter and decimals is not None:
            try:
                q = await self.jupiter.sell_quote(req.token, int(qty * 10**decimals), req.slippage_bps)
            except SourceUnavailable as e:
                q = None
                log.info("jupiter quote unavailable: %s", e)
            if q is not None and q.out_amount > 0:
                out = q.out_amount / LAMPORTS_PER_SOL * (1 - self.landing_slippage_pct)
                fee = out * fee_pct
                ref = ref or out / qty
                return ExecResult(
                    True,
                    Fill(side="sell", qty=qty, price=out / qty, sol_amount=out, dex_fee_sol=fee,
                         network_fee_sol=self.costs.network_fee_sol, slippage_sol=qty * ref - out - fee,
                         price_impact_pct=q.price_impact_pct, quote_source="jupiter", rent_sol=rent_refund, ts=utcnow()),
                    quote={"in": q.in_amount, "out": q.out_amount, "impact": q.price_impact_pct, "route": q.route_labels},
                )
            if q is None and self.jupiter is not None:
                # Jupiter answered but found no route: the token may be unsellable
                pass
        if req.reserve_sol and ref:
            mid = ref * (1 - self.landing_slippage_pct)
            f = amm_sell(qty, req.reserve_sol, mid, fee_pct)
            if f.out_amount > 0:
                return ExecResult(
                    True,
                    Fill(side="sell", qty=qty, price=f.effective_price, sol_amount=f.out_amount, dex_fee_sol=f.fee_paid,
                         network_fee_sol=self.costs.network_fee_sol, slippage_sol=qty * ref - f.out_amount - f.fee_paid,
                         price_impact_pct=f.impact_pct, quote_source="amm_model", rent_sol=rent_refund, ts=utcnow()),
                )
        return ExecResult(False, error="vendita non eseguibile: nessuna rotta e liquidità sconosciuta (possibile rug/honeypot)")
