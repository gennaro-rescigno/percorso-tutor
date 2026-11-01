"""Risk-based position sizing.

size = min(
    risk_budget / effective_stop_distance,      # risk per trade on CURRENT equity
    max_position_pct * equity,                  # concentration cap
    remaining exposure budget,                  # portfolio cap
    cash - reserve - fees,                      # liquidity reserve
    size keeping price impact <= max impact,    # market impact
    max_pool_share * pool reserve,              # don't be the pool
)
effective_stop_distance = stop distance + round-trip costs + gap-risk buffer.
No martingale: risk never increases after losses (it is reduced in drawdown).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from mci.execution.costs import CostModel, max_size_for_impact
from mci.risk_management.profiles import RiskProfile


@dataclass
class SizeDecision:
    size_sol: float
    rejected: bool
    reasons: list[str] = field(default_factory=list)
    binding_constraint: str = ""
    risk_sol: float = 0.0
    effective_stop_pct: float = 0.0


def size_position(
    *,
    equity: float,
    cash: float,
    open_exposure: float,
    stop_distance_pct: float,
    reserve_sol: float | None,
    fee_pct: float,
    profile: RiskProfile,
    costs: CostModel,
    drawdown_pct: float = 0.0,
) -> SizeDecision:
    reasons: list[str] = []
    if equity <= 0 or cash <= 0:
        return SizeDecision(0.0, True, ["capitale non disponibile"], "capital")
    if stop_distance_pct <= 0 or stop_distance_pct >= 1:
        return SizeDecision(0.0, True, ["distanza dello stop non valida"], "stop")

    risk_mult = profile.dd_risk_multiplier if drawdown_pct >= profile.dd_reduce_threshold_pct else 1.0
    if risk_mult < 1:
        reasons.append(f"rischio ridotto x{risk_mult} per drawdown {drawdown_pct:.0%}")
    risk_budget = equity * profile.risk_per_trade_pct * risk_mult

    # Impact is unknown until size is known: iterate twice with the AMM approximation.
    impact = 0.0
    eff_stop = stop_distance_pct
    size_risk = 0.0
    for _ in range(3):
        eff_stop = stop_distance_pct + 2 * fee_pct + 2 * impact + profile.gap_risk_buffer_pct
        size_risk = risk_budget / eff_stop
        if reserve_sol:
            impact = size_risk / (reserve_sol + size_risk)

    caps: dict[str, float] = {
        "rischio per trade": size_risk,
        "massimo per posizione": equity * profile.max_position_pct,
        "esposizione massima": equity * profile.max_exposure_pct - open_exposure,
        "riserva di liquidità": cash - equity * profile.min_cash_reserve_pct - 2 * costs.network_fee_sol - costs.ata_rent_sol,
        "perdita massima in caso di rug": equity * profile.max_worst_case_loss_pct * (risk_mult if risk_mult < 1 else 1.0)
        / max(profile.max_rug_loss_assumption, 1e-9),
    }
    if reserve_sol:
        caps["impatto di prezzo"] = max_size_for_impact(reserve_sol, profile.max_price_impact_pct)
        caps["quota del pool"] = reserve_sol * profile.max_pool_share_pct
    else:
        reasons.append("riserva del pool sconosciuta: limite di impatto non verificabile")
        return SizeDecision(0.0, True, reasons + ["dimensione non calcolabile senza liquidità nota"], "liquidity")

    binding = min(caps, key=lambda k: caps[k])
    size = max(0.0, caps[binding])
    if size < profile.min_position_sol:
        reasons.append(
            f"dimensione {size:.4f} SOL sotto il minimo {profile.min_position_sol} SOL (vincolo: {binding})"
        )
        return SizeDecision(size, True, reasons, binding, 0.0, eff_stop)
    fixed_cost_pct = (2 * costs.network_fee_sol) / size
    if fixed_cost_pct > 0.01:
        reasons.append(f"costi fissi di rete {fixed_cost_pct:.1%} della posizione: troppo alti")
        return SizeDecision(size, True, reasons, "fees", 0.0, eff_stop)
    reasons.append(f"dimensione limitata da: {binding}")
    size = math.floor(size * 1e6) / 1e6  # round DOWN: never exceed the risk budget
    return SizeDecision(size, False, reasons, binding, size * eff_stop, eff_stop)
