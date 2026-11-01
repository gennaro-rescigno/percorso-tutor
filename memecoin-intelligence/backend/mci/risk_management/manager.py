"""Portfolio-level risk manager: decides whether a new trade is allowed.

Guards implemented (Fase 5):
* kill switch (manual or automatic) and pause/resume;
* daily loss limit, drawdown circuit breakers (reduce risk, then pause);
* max concurrent positions, one position per token, cooldown on the same token;
* anti-overtrading: max trades per day, pause after consecutive losses;
* no re-entry right after a loss on the same token (no revenge trading);
* anomalous market conditions (data outages / SOL crash) block new entries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from mci.domain import Signal
from mci.execution.costs import CostModel
from mci.risk_management.profiles import RiskProfile
from mci.risk_management.sizing import SizeDecision, size_position


@dataclass
class PortfolioState:
    equity: float
    cash: float
    peak_equity: float
    exposure: dict[str, float] = field(default_factory=dict)  # token -> current value in SOL
    day: date | None = None
    day_start_equity: float = 0.0
    trades_today: int = 0
    consecutive_losses: int = 0
    paused_until: datetime | None = None
    kill_switch: bool = False
    kill_reason: str = ""
    last_exit: dict[str, tuple[datetime, float]] = field(default_factory=dict)  # token -> (time, pnl)

    @property
    def open_exposure(self) -> float:
        return sum(self.exposure.values())

    @property
    def drawdown_pct(self) -> float:
        if self.peak_equity <= 0:
            return 0.0
        return max(0.0, 1 - self.equity / self.peak_equity)

    def to_dict(self) -> dict[str, Any]:
        return {
            "equity": self.equity,
            "cash": self.cash,
            "peak_equity": self.peak_equity,
            "exposure": dict(self.exposure),
            "day": self.day.isoformat() if self.day else None,
            "day_start_equity": self.day_start_equity,
            "trades_today": self.trades_today,
            "consecutive_losses": self.consecutive_losses,
            "paused_until": self.paused_until.isoformat() if self.paused_until else None,
            "kill_switch": self.kill_switch,
            "kill_reason": self.kill_reason,
            "last_exit": {k: [v[0].isoformat(), v[1]] for k, v in self.last_exit.items()},
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "PortfolioState":
        st = cls(equity=d["equity"], cash=d["cash"], peak_equity=d["peak_equity"])
        st.exposure = dict(d.get("exposure") or {})
        st.day = date.fromisoformat(d["day"]) if d.get("day") else None
        st.day_start_equity = d.get("day_start_equity") or st.equity
        st.trades_today = d.get("trades_today") or 0
        st.consecutive_losses = d.get("consecutive_losses") or 0
        st.paused_until = datetime.fromisoformat(d["paused_until"]) if d.get("paused_until") else None
        st.kill_switch = bool(d.get("kill_switch"))
        st.kill_reason = d.get("kill_reason") or ""
        st.last_exit = {k: (datetime.fromisoformat(v[0]), float(v[1])) for k, v in (d.get("last_exit") or {}).items()}
        return st


@dataclass
class RiskDecision:
    allowed: bool
    size_sol: float
    reasons: list[str]
    sizing: SizeDecision | None = None


class RiskManager:
    def __init__(self, profile: RiskProfile, costs: CostModel):
        self.profile = profile
        self.costs = costs

    # ------------------------------------------------------------------ daily roll
    def roll_day(self, st: PortfolioState, now: datetime) -> None:
        d = now.date()
        if st.day != d:
            st.day = d
            st.day_start_equity = st.equity
            st.trades_today = 0

    def update_equity(self, st: PortfolioState, equity: float, cash: float, now: datetime) -> list[str]:
        """Update marks and trip automatic breakers. Returns alert messages."""
        alerts: list[str] = []
        st.equity, st.cash = equity, cash
        st.peak_equity = max(st.peak_equity, equity)
        self.roll_day(st, now)
        if not st.kill_switch and st.drawdown_pct >= self.profile.max_drawdown_pause_pct:
            st.kill_switch = True
            st.kill_reason = f"drawdown {st.drawdown_pct:.1%} oltre il limite {self.profile.max_drawdown_pause_pct:.0%}"
            alerts.append("KILL SWITCH attivato: " + st.kill_reason)
        return alerts

    def daily_pnl_pct(self, st: PortfolioState) -> float:
        if st.day_start_equity <= 0:
            return 0.0
        return st.equity / st.day_start_equity - 1

    # ------------------------------------------------------------------ entries
    def check_entry(
        self,
        st: PortfolioState,
        signal: Signal,
        *,
        now: datetime,
        reserve_sol: float | None,
        fee_pct: float,
        market_anomaly: str | None = None,
    ) -> RiskDecision:
        p = self.profile
        self.roll_day(st, now)
        no: list[str] = []
        if st.kill_switch:
            no.append(f"kill switch attivo ({st.kill_reason})")
        if st.paused_until and now < st.paused_until:
            no.append(f"trading in pausa fino alle {st.paused_until:%H:%M} UTC")
        if market_anomaly:
            no.append(f"condizioni di mercato anomale: {market_anomaly}")
        if self.daily_pnl_pct(st) <= -p.daily_loss_limit_pct:
            no.append(f"limite di perdita giornaliero raggiunto ({self.daily_pnl_pct(st):.1%})")
        if len(st.exposure) >= p.max_positions:
            no.append(f"numero massimo di posizioni ({p.max_positions}) raggiunto")
        if signal.token_address in st.exposure:
            no.append("posizione già aperta su questo token")
        last = st.last_exit.get(signal.token_address)
        if last and now - last[0] < timedelta(minutes=p.cooldown_same_token_min):
            tag = "dopo una perdita" if last[1] < 0 else "dopo un'uscita recente"
            no.append(f"cooldown sul token {tag}")
        if st.trades_today >= p.max_trades_per_day:
            no.append(f"numero massimo di operazioni giornaliere ({p.max_trades_per_day}) raggiunto")
        if not signal.reduced_features and signal.score < p.min_score:
            no.append(f"score {signal.score:.0f} sotto il minimo del profilo ({p.min_score:.0f})")
        if no:
            return RiskDecision(False, 0.0, no)

        sz = size_position(
            equity=st.equity,
            cash=st.cash,
            open_exposure=st.open_exposure,
            stop_distance_pct=signal.stop_distance_pct,
            reserve_sol=reserve_sol,
            fee_pct=fee_pct,
            profile=p,
            costs=self.costs,
            drawdown_pct=st.drawdown_pct,
        )
        if sz.rejected:
            return RiskDecision(False, 0.0, sz.reasons, sz)
        return RiskDecision(True, sz.size_sol, sz.reasons, sz)

    # ------------------------------------------------------------------ events
    def on_entry(self, st: PortfolioState, token: str, value_sol: float) -> None:
        st.exposure[token] = value_sol
        st.trades_today += 1

    def on_exit(self, st: PortfolioState, token: str, pnl_sol: float, now: datetime, closed: bool) -> None:
        if not closed:
            return
        st.exposure.pop(token, None)
        st.last_exit[token] = (now, pnl_sol)
        if pnl_sol < 0:
            st.consecutive_losses += 1
            if st.consecutive_losses >= self.profile.max_consecutive_losses:
                st.paused_until = now + timedelta(minutes=self.profile.pause_after_losses_min)
                st.consecutive_losses = 0
        else:
            st.consecutive_losses = 0

    @staticmethod
    def activate_kill_switch(st: PortfolioState, reason: str) -> None:
        st.kill_switch = True
        st.kill_reason = reason

    @staticmethod
    def resume(st: PortfolioState, reset_drawdown_reference: bool = True) -> None:
        """Manual resume. The drawdown reference is reset to current equity, otherwise
        the drawdown breaker would immediately trip again."""
        st.kill_switch = False
        st.kill_reason = ""
        st.paused_until = None
        if reset_drawdown_reference:
            st.peak_equity = st.equity
