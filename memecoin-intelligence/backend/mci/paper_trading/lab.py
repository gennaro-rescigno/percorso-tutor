"""Laboratorio: a second, virtual paper portfolio WITHOUT risk limits.

It sees the same candidates, runs the same strategies and the same exit rules as the main portfolio, but every
strategy signal is taken (no maximum positions or trades per day, no cooldown, no minimum score, no daily-loss
or drawdown stop). Its purpose is to measure what each strategy would do on its own: trades, win rate and how
the balance would move. It is fully separate from the main portfolio:

* positions, orders and equity are stored with ``mode="lab"`` and its own ``portfolio_lab`` state;
* it never sends Telegram messages, never writes to the activity log and ignores /pause and /kill
  (it does not consume them either: those commands stay with the main portfolio);
* fills use the constant-product pool model on the observed liquidity (no Jupiter calls, so it never slows
  down the main portfolio); fees, price impact and landing slippage are included, random failures are not.
"""

from __future__ import annotations

import logging
from typing import Any

from mci.config import Settings
from mci.database import repo
from mci.database.session import session_scope
from mci.domain import Signal, utcnow
from mci.execution.costs import CostModel, dex_fee
from mci.execution.paper import PaperExecutor
from mci.paper_trading.engine import NullNotifier, TradingEngine
from mci.risk_management.exits import ExitPolicy
from mci.risk_management.profiles import LAB
from mci.scanner.service import Scanner, TrackedToken
from mci.strategies.base import Strategy

log = logging.getLogger(__name__)

LAB_MODE = "lab"


class LabExecutor(PaperExecutor):
    mode = LAB_MODE

    def __init__(self, costs: CostModel):
        super().__init__(costs, jupiter=None, rpc=None, failure_rate=0.0)


class LabEngine(TradingEngine):
    def __init__(self, settings: Settings, scanner: Scanner, costs: CostModel,
                 strategies: list[Strategy] | None = None, exit_policy: ExitPolicy | None = None):
        # same exit rules as the main portfolio (exit_policy is only overridden in tests)
        super().__init__(settings, scanner, LabExecutor(costs), LAB, costs, notifier=NullNotifier(),
                         exit_policy=exit_policy, strategies=strategies)
        with session_scope() as s:
            if repo.get_state(s, "lab_started_at") is None:
                repo.set_state(s, "lab_started_at", utcnow().isoformat())

    # no limits, no controls, no messages, no activity-log entries
    def control_flags(self) -> tuple[bool, bool]:
        return False, False

    def _market_anomaly(self) -> str | None:
        return None

    def _log(self, s, category: str, message: str, **kw: Any) -> None:
        return None

    async def _token_alerts(self, candidates: list[TrackedToken]) -> None:
        return None

    async def flush_alerts(self) -> None:
        self._pending_alerts.clear()

    def track_signal_outcomes(self) -> int:
        return 0

    async def _handle_signal(self, tt: TrackedToken, strat: Strategy, sig: Signal, anomaly: str | None,
                             sol_eur: float | None, killed: bool) -> None:
        snap = tt.snapshot
        fee = dex_fee(snap.dex_id, snap.market_cap_usd)
        rd = self.risk.check_entry(self.port, sig, now=utcnow(), reserve_sol=snap.liquidity_quote, fee_pct=fee)
        if not rd.allowed:
            # only physical constraints are left (no capital, unknown liquidity, too much price impact):
            # count them so the dashboard can show how many signals could not be simulated and why
            with session_scope() as s:
                skipped = repo.get_state(s, "lab_skipped") or {}
                key = (rd.reasons[-1] if rd.reasons else "non simulabile")[:120]
                skipped[key] = skipped.get(key, 0) + 1
                repo.set_state(s, "lab_skipped", skipped)
            return
        await self._open_position(tt, strat, sig, None, rd.size_sol, rd.sizing.risk_sol if rd.sizing else 0.0,
                                  sol_eur)
