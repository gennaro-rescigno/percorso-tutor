"""Exit management shared by backtest (bar-by-bar) and paper/live trading (ticks).

Conventions that avoid optimistic bias:
* inside one bar the STOP is checked before take-profits (pessimistic ordering);
* a bar that OPENS below the stop fills at the open (gap), not at the stop;
* trailing-stop / break-even updates computed from a bar's high only apply from the
  NEXT bar (the intrabar order of high and low is unknown).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ExitPolicy:
    name: str = "ladder_trailing"
    stop_mode: str = "atr"  # fixed | atr | structural
    fixed_stop_pct: float = 0.20
    atr_mult: float = 2.5
    min_stop_pct: float = 0.10
    max_stop_pct: float = 0.35
    take_profits: tuple[tuple[float, float], ...] = ((0.5, 0.33), (1.0, 0.33))  # (+gain, fraction of initial qty)
    trailing_activation_pct: float | None = 0.4
    trailing_pct: float = 0.25
    breakeven: str = "after_tp1"  # never | after_r | after_tp1
    breakeven_r: float = 1.5
    breakeven_buffer_pct: float = 0.04  # BE level covers round-trip costs
    max_hold_minutes: int = 360
    no_progress_minutes: int = 60
    no_progress_min_gain: float = 0.05
    volume_decay_exit: bool = True
    volume_decay_ratio: float = 0.2
    volume_decay_min_minutes: int = 30
    liquidity_drop_exit_pct: float = 0.35

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


EXIT_POLICIES: dict[str, ExitPolicy] = {
    # fixed stop, single take profit, no trailing
    "fixed_simple": ExitPolicy(
        name="fixed_simple", stop_mode="fixed", fixed_stop_pct=0.20, take_profits=((0.6, 1.0),),
        trailing_activation_pct=None, breakeven="never", volume_decay_exit=False,
    ),
    # volatility stop + ladder + trailing residual (default)
    "ladder_trailing": ExitPolicy(),
    # trailing only, no partials
    "trailing_only": ExitPolicy(
        name="trailing_only", take_profits=(), trailing_activation_pct=0.25, trailing_pct=0.22, breakeven="after_r",
    ),
    # momentum-driven: quick partial, tight volume decay exit
    "momentum_exit": ExitPolicy(
        name="momentum_exit", take_profits=((0.3, 0.5),), trailing_activation_pct=0.3, trailing_pct=0.18,
        volume_decay_ratio=0.3, volume_decay_min_minutes=20, no_progress_minutes=40,
    ),
    # same as default but break-even never moved (to test the BE question explicitly)
    "ladder_no_be": ExitPolicy(name="ladder_no_be", breakeven="never"),
    "ladder_be_1r": ExitPolicy(name="ladder_be_1r", breakeven="after_r", breakeven_r=1.0),
}


@dataclass
class PositionState:
    token: str
    strategy: str
    entry_time: datetime
    entry_price: float
    qty_initial: float
    qty: float
    cost_sol: float  # total SOL spent, incl. fees and rent
    stop_price: float
    initial_stop: float
    high_water: float
    tp_done: int = 0
    be_moved: bool = False
    trailing_active: bool = False
    entry_volume_ref: float | None = None  # avg volume per bar before entry
    entry_reserve_sol: float | None = None
    pending_stop: float | None = None  # stop update to apply from next bar
    realized_sol: float = 0.0
    fees_sol: float = 0.0
    slippage_sol: float = 0.0
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def r_unit(self) -> float:
        return max(self.entry_price - self.initial_stop, self.entry_price * 1e-6)


@dataclass
class ExitAction:
    qty: float
    reason: str  # code
    description: str
    price_hint: float  # price at which the order is triggered (before impact)


def initial_stop(policy: ExitPolicy, entry_price: float, structural_stop: float | None, atr: float | None) -> float:
    if policy.stop_mode == "fixed" or (policy.stop_mode == "atr" and not atr):
        dist = policy.fixed_stop_pct
    elif policy.stop_mode == "atr":
        dist = policy.atr_mult * atr / entry_price
    else:
        dist = (entry_price - structural_stop) / entry_price if structural_stop else policy.fixed_stop_pct
    dist = min(max(dist, policy.min_stop_pct), policy.max_stop_pct)
    return entry_price * (1 - dist)


def evaluate_bar(
    pos: PositionState,
    policy: ExitPolicy,
    *,
    now: datetime,
    open_: float,
    high: float,
    low: float,
    close: float,
    bar_volume_avg: float | None = None,
    reserve_sol: float | None = None,
    onchain_alert: str | None = None,
) -> list[ExitAction]:
    """Return exit actions for one bar (or one tick with open=high=low=close)."""
    actions: list[ExitAction] = []
    if pos.qty <= 0:
        return actions
    if pos.pending_stop is not None:
        pos.stop_price = max(pos.stop_price, pos.pending_stop)
        pos.pending_stop = None

    # 1) stop (gap-aware)
    if open_ <= pos.stop_price:
        actions.append(ExitAction(pos.qty, "STOP_GAP", "stop superato in gap: eseguito all'apertura", open_))
        return actions
    if low <= pos.stop_price:
        kind = "TRAILING_STOP" if pos.trailing_active else ("BREAKEVEN_STOP" if pos.be_moved else "STOP_LOSS")
        desc = {"TRAILING_STOP": "trailing stop raggiunto", "BREAKEVEN_STOP": "stop a break-even raggiunto",
                "STOP_LOSS": "stop loss raggiunto"}[kind]
        actions.append(ExitAction(pos.qty, kind, desc, pos.stop_price))
        return actions

    # 2) on-chain / liquidity emergencies (exit at close)
    if onchain_alert:
        actions.append(ExitAction(pos.qty, "ONCHAIN_DETERIORATION", f"deterioramento on-chain: {onchain_alert}", close))
        return actions
    if reserve_sol is not None and pos.entry_reserve_sol and policy.liquidity_drop_exit_pct:
        if reserve_sol < pos.entry_reserve_sol * (1 - policy.liquidity_drop_exit_pct):
            actions.append(ExitAction(pos.qty, "LIQUIDITY_DROP", "liquidità in forte calo rispetto all'ingresso", close))
            return actions

    # 3) take profits (ladder)
    remaining = pos.qty
    for i, (gain, frac) in enumerate(policy.take_profits):
        if i < pos.tp_done:
            continue
        level = pos.entry_price * (1 + gain)
        if high >= level:
            q = min(remaining, pos.qty_initial * frac)
            if i == len(policy.take_profits) - 1 and policy.trailing_activation_pct is None:
                q = remaining  # last TP closes everything when there is no trailing
            if q > 0:
                fill_at = max(level, open_)  # opened above level -> filled at open
                actions.append(ExitAction(q, f"TAKE_PROFIT_{i + 1}", f"take profit {i + 1} (+{gain:.0%})", fill_at))
                remaining -= q
            pos.tp_done = i + 1
        else:
            break
    if remaining <= 1e-12:
        return actions

    # 4) time-based exits (at close)
    held_min = (now - pos.entry_time).total_seconds() / 60.0
    if held_min >= policy.max_hold_minutes:
        actions.append(ExitAction(remaining, "TIME_STOP", f"durata massima raggiunta ({policy.max_hold_minutes} min)", close))
        return actions
    if (
        policy.no_progress_minutes
        and held_min >= policy.no_progress_minutes
        and pos.tp_done == 0
        and pos.high_water < pos.entry_price * (1 + policy.no_progress_min_gain)
    ):
        actions.append(ExitAction(remaining, "NO_PROGRESS", "nessun progresso: capitale liberato", close))
        return actions
    if (
        policy.volume_decay_exit
        and bar_volume_avg is not None
        and pos.entry_volume_ref
        and held_min >= policy.volume_decay_min_minutes
        and bar_volume_avg < policy.volume_decay_ratio * pos.entry_volume_ref
    ):
        actions.append(ExitAction(remaining, "VOLUME_DECAY", "volume crollato rispetto all'ingresso (momentum esaurito)", close))
        return actions

    # 5) state updates for next bar (trailing, break-even)
    pos.high_water = max(pos.high_water, high)
    new_stop = pos.stop_price
    if policy.trailing_activation_pct is not None and pos.high_water >= pos.entry_price * (1 + policy.trailing_activation_pct):
        pos.trailing_active = True
        new_stop = max(new_stop, pos.high_water * (1 - policy.trailing_pct))
    be_level = pos.entry_price * (1 + policy.breakeven_buffer_pct)
    if not pos.be_moved:
        if (policy.breakeven == "after_tp1" and pos.tp_done >= 1) or (
            policy.breakeven == "after_r" and pos.high_water >= pos.entry_price + policy.breakeven_r * pos.r_unit
        ):
            new_stop = max(new_stop, be_level)
            pos.be_moved = True
    if new_stop > pos.stop_price:
        pos.pending_stop = new_stop
    return actions
