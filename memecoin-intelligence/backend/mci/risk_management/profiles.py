"""Risk profiles. Values are STARTING POINTS to be validated by the backtest
(RESEARCH_REPORT §7.3); the backtest compares all three."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any


@dataclass(frozen=True)
class RiskProfile:
    name: str
    risk_per_trade_pct: float  # fraction of current equity at risk per trade
    max_positions: int
    max_exposure_pct: float  # total open exposure / equity
    max_position_pct: float  # single position / equity
    min_cash_reserve_pct: float  # always keep liquid
    daily_loss_limit_pct: float  # stop opening trades for the day
    dd_reduce_threshold_pct: float  # drawdown from peak at which risk is reduced
    dd_risk_multiplier: float  # risk multiplier when above threshold
    max_drawdown_pause_pct: float  # drawdown from peak at which trading pauses (manual resume)
    max_price_impact_pct: float  # max entry price impact
    max_pool_share_pct: float  # position / quote-side reserve
    gap_risk_buffer_pct: float  # added to stop distance when sizing (stops can be gapped)
    min_score: float
    cooldown_same_token_min: int
    max_consecutive_losses: int
    pause_after_losses_min: int
    max_trades_per_day: int
    min_position_sol: float
    max_rug_loss_assumption: float = 1.0  # share of a position assumed lost in a rug (stop gapped)
    # Worst-case cap: position * max_rug_loss_assumption <= equity * max_worst_case_loss_pct.
    # Added after the synthetic rug stress test (reports/STRESS_TEST_SYNTHETIC.md): the stop
    # distance alone under-states memecoin risk because rugs jump through the stop.
    max_worst_case_loss_pct: float = 0.04

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def with_overrides(self, **kw: Any) -> "RiskProfile":
        return replace(self, **kw)


CONSERVATIVE = RiskProfile(
    name="conservative",
    risk_per_trade_pct=0.0075,
    max_positions=2,
    max_exposure_pct=0.20,
    max_position_pct=0.10,
    min_cash_reserve_pct=0.50,
    daily_loss_limit_pct=0.03,
    dd_reduce_threshold_pct=0.10,
    dd_risk_multiplier=0.5,
    max_drawdown_pause_pct=0.20,
    max_price_impact_pct=0.015,
    max_pool_share_pct=0.01,
    gap_risk_buffer_pct=0.10,
    min_score=75.0,
    cooldown_same_token_min=24 * 60,
    max_consecutive_losses=3,
    pause_after_losses_min=240,
    max_trades_per_day=4,
    min_position_sol=0.03,
    max_worst_case_loss_pct=0.025,
)

MODERATE = RiskProfile(
    name="moderate",
    risk_per_trade_pct=0.0125,
    max_positions=3,
    max_exposure_pct=0.35,
    max_position_pct=0.15,
    min_cash_reserve_pct=0.40,
    daily_loss_limit_pct=0.05,
    dd_reduce_threshold_pct=0.15,
    dd_risk_multiplier=0.5,
    max_drawdown_pause_pct=0.30,
    max_price_impact_pct=0.02,
    max_pool_share_pct=0.015,
    gap_risk_buffer_pct=0.08,
    min_score=70.0,
    cooldown_same_token_min=12 * 60,
    max_consecutive_losses=4,
    pause_after_losses_min=120,
    max_trades_per_day=6,
    min_position_sol=0.03,
    max_worst_case_loss_pct=0.04,
)

AGGRESSIVE = RiskProfile(
    name="aggressive",
    risk_per_trade_pct=0.02,
    max_positions=3,
    max_exposure_pct=0.50,
    max_position_pct=0.20,
    min_cash_reserve_pct=0.30,
    daily_loss_limit_pct=0.08,
    dd_reduce_threshold_pct=0.20,
    dd_risk_multiplier=0.5,
    max_drawdown_pause_pct=0.35,
    max_price_impact_pct=0.03,
    max_pool_share_pct=0.02,
    gap_risk_buffer_pct=0.06,
    min_score=65.0,
    cooldown_same_token_min=6 * 60,
    max_consecutive_losses=5,
    pause_after_losses_min=60,
    max_trades_per_day=8,
    min_position_sol=0.03,
    max_worst_case_loss_pct=0.06,
)

PROFILES = {p.name: p for p in (CONSERVATIVE, MODERATE, AGGRESSIVE)}


def get_profile(name: str) -> RiskProfile:
    return PROFILES[name.lower()]
