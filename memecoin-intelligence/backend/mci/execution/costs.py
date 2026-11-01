"""Execution cost model shared by the backtester and the paper executor fallback.

* DEX fee per venue (``config.VENUE_FEES``), with PumpSwap tiering by market cap.
* Constant-product AMM price impact from the quote-side (SOL) reserve.
* Network fees: base fee + priority fee (+ optional Jito tip) per transaction.
* ATA rent (~0.00204 SOL) paid on the first buy and refunded when the account is
  closed after a full exit; lost if the token becomes unsellable.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from mci.config import VENUE_FEES

BASE_FEE_SOL = 0.000005
ATA_RENT_SOL = 0.00203928


def dex_fee(dex_id: str | None, market_cap_usd: float | None = None) -> float:
    dex = (dex_id or "default").lower()
    if dex == "pumpswap" and market_cap_usd:
        # Tiered schedule (reported: 1.25% right after graduation down to 0.30% floor).
        # Approximated log-linearly between $100k and $20M market cap.
        lo, hi = 1e5, 2e7
        mc = min(max(market_cap_usd, lo), hi)
        frac = (math.log(mc) - math.log(lo)) / (math.log(hi) - math.log(lo))
        return 0.0125 - frac * (0.0125 - 0.0030)
    return VENUE_FEES.get(dex, VENUE_FEES["default"])


@dataclass
class CostModel:
    priority_fee_sol: float = 0.0001
    jito_tip_sol: float = 0.0
    ata_rent_sol: float = ATA_RENT_SOL

    @property
    def network_fee_sol(self) -> float:
        return BASE_FEE_SOL + self.priority_fee_sol + self.jito_tip_sol

    def roundtrip_cost_pct(self, size_sol: float, fee_pct: float, impact_pct: float) -> float:
        """Approximate total round-trip cost as a fraction of position size."""
        if size_sol <= 0:
            return 1.0
        fixed = 2 * self.network_fee_sol / size_sol
        return 2 * fee_pct + 2 * impact_pct + fixed


@dataclass
class AmmFill:
    out_amount: float
    effective_price: float  # SOL per token
    impact_pct: float  # price impact as a fraction of mid price
    fee_paid: float  # in input units


def amm_buy(sol_in: float, reserve_sol: float, mid_price: float, fee_pct: float) -> AmmFill:
    """Buy tokens with ``sol_in`` SOL on a constant-product pool.

    Token reserve y = x / p. out = y * dx' / (x + dx'), dx' = dx * (1 - fee).
    """
    if sol_in <= 0 or reserve_sol <= 0 or mid_price <= 0:
        return AmmFill(0.0, mid_price, 1.0, 0.0)
    fee = sol_in * fee_pct
    dx = sol_in - fee
    y = reserve_sol / mid_price
    out = y * dx / (reserve_sol + dx)
    eff = sol_in / out if out > 0 else float("inf")
    return AmmFill(out, eff, dx / (reserve_sol + dx), fee)


def amm_sell(tokens_in: float, reserve_sol: float, mid_price: float, fee_pct: float) -> AmmFill:
    """Sell tokens for SOL on a constant-product pool. Fee charged on SOL output."""
    if tokens_in <= 0 or reserve_sol <= 0 or mid_price <= 0:
        return AmmFill(0.0, 0.0, 1.0, 0.0)
    y = reserve_sol / mid_price
    gross = reserve_sol * tokens_in / (y + tokens_in)
    fee = gross * fee_pct
    out = gross - fee
    return AmmFill(out, out / tokens_in, tokens_in / (y + tokens_in), fee)


def max_size_for_impact(reserve_sol: float, max_impact: float) -> float:
    """Largest SOL input whose price impact stays <= max_impact (impact = dx/(x+dx))."""
    if reserve_sol <= 0 or max_impact <= 0:
        return 0.0
    max_impact = min(max_impact, 0.99)
    return reserve_sol * max_impact / (1 - max_impact)


def reserve_from_liquidity(liquidity_usd: float | None, sol_usd: float | None) -> float | None:
    """Quote-side reserve of a 50/50 constant-product pool: half the TVL, in SOL."""
    if not liquidity_usd or not sol_usd or sol_usd <= 0:
        return None
    return liquidity_usd / 2.0 / sol_usd


def reserve_at_price(reserve0: float, price0: float, price_t: float) -> float:
    """Constant-product reserve evolution without LP changes: x = sqrt(k * p) => x_t = x0 * sqrt(p_t / p0)."""
    if reserve0 <= 0 or price0 <= 0 or price_t <= 0:
        return 0.0
    return reserve0 * math.sqrt(price_t / price0)
