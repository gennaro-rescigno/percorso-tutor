"""Backtest performance metrics.

Sharpe/Sortino are reported only when statistically meaningful (enough daily
observations); otherwise ``None`` with an explanation, as required by Fase 6.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

MIN_DAYS_FOR_RATIOS = 30
MIN_TRADES_FOR_ROBUST = 100


@dataclass
class TradeRecord:
    token: str
    symbol: str | None
    strategy: str
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float  # qty-weighted average
    qty: float
    cost_sol: float  # total SOL out (stake + fees + rent)
    proceeds_sol: float  # total SOL in (net of dex fees; incl. rent refund)
    pnl_sol: float
    return_pct: float  # pnl / cost
    fees_sol: float  # dex + network
    slippage_sol: float  # vs mid price
    exit_reasons: list[str]
    mfe_pct: float  # max favourable excursion
    mae_pct: float  # max adverse excursion
    score: float
    reduced_features: bool
    dead_token: bool = False

    @property
    def hold_minutes(self) -> float:
        return (self.exit_time - self.entry_time).total_seconds() / 60.0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["entry_time"] = self.entry_time.isoformat()
        d["exit_time"] = self.exit_time.isoformat()
        d["hold_minutes"] = self.hold_minutes
        return d


@dataclass
class Metrics:
    initial_capital_sol: float
    final_capital_sol: float
    net_profit_sol: float
    return_pct: float
    n_trades: int
    win_rate: float | None
    loss_rate: float | None
    profit_factor: float | None
    expectancy_sol: float | None
    expectancy_pct: float | None
    avg_win_sol: float | None
    avg_loss_sol: float | None
    max_drawdown_pct: float
    sharpe: float | None
    sortino: float | None
    ratio_note: str
    max_consecutive_losses: int
    avg_hold_minutes: float | None
    total_fees_sol: float
    total_slippage_sol: float
    max_capital_used_sol: float
    failed_orders: int = 0
    dead_token_exits: int = 0
    expectancy_ci95_pct: tuple[float, float] | None = None
    mc_max_dd_p50: float | None = None
    mc_max_dd_p95: float | None = None
    robust: bool = False
    robustness_notes: list[str] = field(default_factory=list)
    by_strategy: dict[str, dict[str, Any]] = field(default_factory=dict)
    by_exit_reason: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def max_drawdown(equity: list[float]) -> float:
    peak, mdd = -math.inf, 0.0
    for v in equity:
        peak = max(peak, v)
        if peak > 0:
            mdd = max(mdd, 1 - v / peak)
    return mdd


def _daily_returns(curve: list[tuple[datetime, float]]) -> list[float]:
    by_day: dict[str, float] = {}
    for t, v in curve:
        by_day[t.astimezone(timezone.utc).date().isoformat()] = v  # last value of the day
    vals = [by_day[k] for k in sorted(by_day)]
    return [vals[i] / vals[i - 1] - 1 for i in range(1, len(vals)) if vals[i - 1] > 0]


def _bootstrap_ci(values: list[float], n: int = 2000, seed: int = 7) -> tuple[float, float] | None:
    if len(values) < 10:
        return None
    rng = random.Random(seed)
    means = sorted(sum(rng.choice(values) for _ in values) / len(values) for _ in range(n))
    return means[int(0.025 * n)], means[int(0.975 * n)]


def _mc_drawdowns(returns_frac_of_equity: list[float], start: float, n: int = 1000, seed: int = 11) -> tuple[float, float] | None:
    if len(returns_frac_of_equity) < 10:
        return None
    rng = random.Random(seed)
    dds = []
    for _ in range(n):
        seq = returns_frac_of_equity[:]
        rng.shuffle(seq)
        eq, curve = start, [start]
        for r in seq:
            eq *= 1 + r
            curve.append(eq)
        dds.append(max_drawdown(curve))
    dds.sort()
    return dds[n // 2], dds[int(0.95 * n)]


def compute_metrics(
    trades: list[TradeRecord],
    curve: list[tuple[datetime, float]],
    initial: float,
    *,
    max_capital_used: float = 0.0,
    failed_orders: int = 0,
) -> Metrics:
    final = curve[-1][1] if curve else initial
    pnl = [t.pnl_sol for t in trades]
    wins = [x for x in pnl if x > 0]
    losses = [x for x in pnl if x <= 0]
    n = len(trades)
    gross_win, gross_loss = sum(wins), -sum(losses)
    pf = (gross_win / gross_loss) if gross_loss > 0 else (math.inf if gross_win > 0 else None)

    streak = best = 0
    for x in pnl:
        streak = streak + 1 if x <= 0 else 0
        best = max(best, streak)

    daily = _daily_returns(curve)
    sharpe = sortino = None
    note = ""
    if len(daily) >= MIN_DAYS_FOR_RATIOS and any(daily):
        mu = sum(daily) / len(daily)
        sd = math.sqrt(sum((r - mu) ** 2 for r in daily) / (len(daily) - 1))
        downs = [r for r in daily if r < 0]
        dd_sd = math.sqrt(sum(r * r for r in downs) / len(daily)) if downs else 0.0
        sharpe = (mu / sd * math.sqrt(365)) if sd > 0 else None
        sortino = (mu / dd_sd * math.sqrt(365)) if dd_sd > 0 else None
        note = f"calcolati su {len(daily)} rendimenti giornalieri (annualizzati, 365 gg)"
    else:
        note = f"non significativi: solo {len(daily)} giorni di storico (minimo {MIN_DAYS_FOR_RATIOS})"

    # per-trade returns as fraction of equity at entry for Monte Carlo
    eq_frac = []
    eq = initial
    for t in trades:
        eq_frac.append(t.pnl_sol / eq if eq > 0 else 0.0)
        eq += t.pnl_sol
    mc = _mc_drawdowns(eq_frac, initial)
    ci = _bootstrap_ci([t.return_pct for t in trades])

    by_strat: dict[str, list[TradeRecord]] = defaultdict(list)
    reasons: dict[str, int] = defaultdict(int)
    for t in trades:
        by_strat[t.strategy].append(t)
        for r in t.exit_reasons:
            reasons[r] += 1
    by_strategy = {}
    for k, ts in by_strat.items():
        p = [t.pnl_sol for t in ts]
        w = [x for x in p if x > 0]
        gl = -sum(x for x in p if x <= 0)
        by_strategy[k] = {
            "trades": len(ts),
            "pnl_sol": sum(p),
            "win_rate": len(w) / len(ts),
            "profit_factor": (sum(w) / gl) if gl > 0 else None,
            "expectancy_sol": sum(p) / len(ts),
        }

    notes: list[str] = []
    robust = True
    if n < MIN_TRADES_FOR_ROBUST:
        robust = False
        notes.append(f"campione troppo piccolo: {n} trade (minimo {MIN_TRADES_FOR_ROBUST})")
    if ci and ci[0] <= 0 <= ci[1]:
        robust = False
        notes.append("l'intervallo di confidenza al 95% dell'expectancy include lo zero")
    if any(t.reduced_features for t in trades):
        notes.append("trade generati con soli dati OHLCV (feature on-chain/social non disponibili)")

    return Metrics(
        initial_capital_sol=initial,
        final_capital_sol=final,
        net_profit_sol=final - initial,
        return_pct=(final / initial - 1) if initial else 0.0,
        n_trades=n,
        win_rate=(len(wins) / n) if n else None,
        loss_rate=(len(losses) / n) if n else None,
        profit_factor=pf,
        expectancy_sol=(sum(pnl) / n) if n else None,
        expectancy_pct=(sum(t.return_pct for t in trades) / n) if n else None,
        avg_win_sol=(gross_win / len(wins)) if wins else None,
        avg_loss_sol=(-gross_loss / len(losses)) if losses else None,
        max_drawdown_pct=max_drawdown([v for _, v in curve]) if curve else 0.0,
        sharpe=sharpe,
        sortino=sortino,
        ratio_note=note,
        max_consecutive_losses=best,
        avg_hold_minutes=(sum(t.hold_minutes for t in trades) / n) if n else None,
        total_fees_sol=sum(t.fees_sol for t in trades),
        total_slippage_sol=sum(t.slippage_sol for t in trades),
        max_capital_used_sol=max_capital_used,
        failed_orders=failed_orders,
        dead_token_exits=sum(1 for t in trades if t.dead_token),
        expectancy_ci95_pct=ci,
        mc_max_dd_p50=mc[0] if mc else None,
        mc_max_dd_p95=mc[1] if mc else None,
        robust=robust,
        robustness_notes=notes,
        by_strategy=by_strategy,
        by_exit_reason=dict(reasons),
    )
