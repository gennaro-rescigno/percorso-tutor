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
from dataclasses import replace
from typing import Any

from mci.config import Settings
from mci.database import repo
from mci.database.session import session_scope
from mci.domain import Signal, utcnow
from mci.execution.costs import CostModel, dex_fee
from mci.execution.paper import PaperExecutor
from mci.paper_trading.engine import MAX_REFERENCE_DIVERGENCE, NullNotifier, TradingEngine, price_divergence
from mci.risk_management.exits import ExitPolicy
from mci.risk_management.manager import RiskDecision
from mci.risk_management.profiles import LAB
from mci.scanner.service import Scanner, TrackedToken
from mci.strategies.base import Strategy

log = logging.getLogger(__name__)

LAB_MODE = "lab"
# bump when a fix invalidates earlier lab results: the lab then restarts from 2 SOL (main portfolio untouched)
# v2: entries priced from the live market price instead of the last candle close
LAB_VERSION = 2


def reset_lab(s, mode: str = LAB_MODE) -> None:
    """Remove every record of one virtual portfolio (positions, orders, fills, equity, state).
    Main portfolio rows (and the other virtual portfolios) are untouched."""
    from sqlalchemy import delete, select

    from mci.database.models import EquitySnapshot, FillRow, Order, Position

    if mode in ("paper", "live"):
        raise ValueError("reset_lab never touches the main portfolio")
    pre = state_prefix(mode)
    lab_orders = select(Order.id).where(Order.mode == mode)
    s.execute(delete(FillRow).where(FillRow.order_id.in_(lab_orders)))
    s.execute(delete(Order).where(Order.mode == mode))
    s.execute(delete(Position).where(Position.mode == mode))
    s.execute(delete(EquitySnapshot).where(EquitySnapshot.mode == mode))
    for key in (f"portfolio_{mode}", f"{pre}_stats", f"{pre}_skipped", f"{pre}_started_at", f"{pre}_last_scan_at"):
        repo.set_state(s, key, None)


def state_prefix(mode: str) -> str:
    return "lab" if mode == LAB_MODE else mode


class LabExecutor(PaperExecutor):
    def __init__(self, costs: CostModel, mode: str = LAB_MODE):
        super().__init__(costs, jupiter=None, rpc=None, failure_rate=0.0)
        self.mode = mode


class LabEngine(TradingEngine):
    #: bump in a subclass when a fix invalidates its earlier results (that portfolio restarts from 2 SOL)
    version = LAB_VERSION

    def __init__(self, settings: Settings, scanner: Scanner, costs: CostModel,
                 strategies: list[Strategy] | None = None, exit_policy: ExitPolicy | None = None,
                 mode: str = LAB_MODE):
        # same exit rules as the main portfolio (exit_policy is only overridden in tests)
        super().__init__(settings, scanner, LabExecutor(costs, mode), LAB, costs, notifier=NullNotifier(),
                         exit_policy=exit_policy, strategies=strategies)
        self.prefix = state_prefix(mode)
        with session_scope() as s:
            if repo.get_state(s, f"{self.prefix}_version") != self.version:
                reset_lab(s, mode)
                repo.set_state(s, f"{self.prefix}_version", self.version)
            if repo.get_state(s, f"{self.prefix}_started_at") is None:
                repo.set_state(s, f"{self.prefix}_started_at", utcnow().isoformat())
        self.port = self._load_portfolio()

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

    def gate(self, tt: TrackedToken) -> bool:
        """Extra entry condition of an experiment (the Laboratorio itself has none)."""
        return True

    def _count_skip(self, s, reason: str) -> None:
        skipped = repo.get_state(s, f"{self.prefix}_skipped") or {}
        skipped[reason] = skipped.get(reason, 0) + 1
        repo.set_state(s, f"{self.prefix}_skipped", skipped)

    async def on_scan(self, candidates: list[TrackedToken]) -> None:
        await super().on_scan(candidates)
        with session_scope() as s:  # heartbeat shown on the dashboard page
            repo.set_state(s, f"{self.prefix}_last_scan_at", utcnow().isoformat())

    async def _handle_signal(self, tt: TrackedToken, strat: Strategy, sig: Signal, anomaly: str | None,
                             sol_eur: float | None, killed: bool) -> None:
        snap = tt.snapshot
        fee = dex_fee(snap.dex_id, snap.market_cap_usd)
        now = utcnow()
        live = snap.price_native
        div = price_divergence(sig.reference_price, live)
        if live and div is not None and div <= MAX_REFERENCE_DIVERGENCE:
            # simulated fills start from the LIVE market price (the same source the position monitor uses), never
            # from the last candle close, which can be stale or, for non-SOL pools, in another unit
            sig = replace(sig, reference_price=live, stop_price=sig.stop_price * live / sig.reference_price)
            rd = self.risk.check_entry(self.port, sig, now=now, reserve_sol=snap.liquidity_quote, fee_pct=fee)
        elif not live:
            rd = RiskDecision(False, 0.0, ["prezzo attuale non disponibile"])
        else:
            rd = RiskDecision(False, 0.0, [f"prezzo delle candele incoerente con il prezzo attuale ({div:.0%})"])
        if not self.gate(tt):
            return
        with session_scope() as s:
            stats = repo.get_state(s, f"{self.prefix}_stats") or {"signals": 0, "by_strategy": {}}
            stats["signals"] += 1
            stats["by_strategy"][sig.strategy] = stats["by_strategy"].get(sig.strategy, 0) + 1
            stats["last_signal_at"] = now.isoformat()
            stats["last_signal"] = f"{sig.strategy} su {sig.symbol or sig.token_address[:8]}"
            repo.set_state(s, f"{self.prefix}_stats", stats)
            if not rd.allowed:
                # only physical constraints are left (no capital, unknown liquidity, too much price impact):
                # count them so the dashboard can show how many signals could not be simulated and why
                self._count_skip(s, (rd.reasons[-1] if rd.reasons else "non simulabile")[:120])
        if not rd.allowed:
            return
        await self._open_position(tt, strat, sig, None, rd.size_sol, rd.sizing.risk_sol if rd.sizing else 0.0,
                                  sol_eur)
