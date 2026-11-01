"""Train / validation / out-of-sample splits and walk-forward analysis.

Parameter selection is deliberately conservative:
* candidates with too few trades are discarded;
* the objective is return / max drawdown (Calmar-like), capped, not raw profit;
* the chosen candidate maximizes the MEDIAN objective of itself and its grid
  neighbours, so isolated "lucky" parameter spikes are not selected.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field, replace
from typing import Any

from mci.backtesting.data import Dataset
from mci.backtesting.engine import BacktestConfig, BacktestResult, run_backtest


@dataclass
class Candidate:
    params: dict[str, Any]
    result: BacktestResult | None = None
    objective: float = float("-inf")
    smoothed: float = float("-inf")


@dataclass
class WalkForwardWindow:
    train: tuple[int, int]
    test: tuple[int, int]
    chosen_params: dict[str, Any]
    train_objective: float
    test_result: BacktestResult


@dataclass
class WalkForwardReport:
    windows: list[WalkForwardWindow] = field(default_factory=list)
    oos_trades: int = 0
    oos_pnl_sol: float = 0.0
    notes: list[str] = field(default_factory=list)


def objective(res: BacktestResult, min_trades: int) -> float:
    m = res.metrics
    if m.n_trades < min_trades:
        return float("-inf")
    dd = max(m.max_drawdown_pct, 0.05)
    return max(-5.0, min(5.0, m.return_pct / dd))


def expand_grid(grid: dict[str, list[Any]]) -> list[dict[str, Any]]:
    keys = sorted(grid)
    return [dict(zip(keys, vals)) for vals in itertools.product(*(grid[k] for k in keys))]


def _neighbours(i: int, combos: list[dict[str, Any]], grid: dict[str, list[Any]]) -> list[int]:
    base = combos[i]
    out = [i]
    for j, c in enumerate(combos):
        if j == i:
            continue
        diff = [k for k in grid if c[k] != base[k]]
        if len(diff) == 1:
            k = diff[0]
            if abs(grid[k].index(c[k]) - grid[k].index(base[k])) == 1:
                out.append(j)
    return out


def _apply(cfg: BacktestConfig, strategy: str, params: dict[str, Any], start: int, end: int) -> BacktestConfig:
    sp = {**cfg.strategy_params, strategy: {**cfg.strategy_params.get(strategy, {}), **params}}
    return replace(cfg, strategy_params=sp, entry_start_ts=start, entry_end_ts=end)


def optimize(
    ds: Dataset, base: BacktestConfig, strategy: str, grid: dict[str, list[Any]], start: int, end: int,
    min_trades: int = 20,
) -> list[Candidate]:
    combos = expand_grid(grid)
    cands = []
    window = ds.slice(start, end)
    for params in combos:
        res = run_backtest(window, _apply(base, strategy, params, start, end))
        cands.append(Candidate(params, res, objective(res, min_trades)))
    for i, c in enumerate(cands):
        vals = sorted(cands[j].objective for j in _neighbours(i, combos, grid))
        c.smoothed = vals[len(vals) // 2]
    return sorted(cands, key=lambda c: c.smoothed, reverse=True)


def split_times(ds: Dataset, train: float = 0.6, validation: float = 0.2) -> dict[str, tuple[int, int]]:
    ts = sorted({c.ts for s in ds.series for c in s.candles})
    if not ts:
        raise ValueError("dataset vuoto")
    a, b = ts[0], ts[-1] + 1
    t1 = a + int((b - a) * train)
    t2 = a + int((b - a) * (train + validation))
    return {"train": (a, t1), "validation": (t1, t2), "test": (t2, b)}


def walk_forward(
    ds: Dataset, base: BacktestConfig, strategy: str, grid: dict[str, list[Any]], *,
    n_windows: int = 4, train_frac: float = 0.7, min_trades: int = 20,
) -> WalkForwardReport:
    ts = sorted({c.ts for s in ds.series for c in s.candles})
    rep = WalkForwardReport()
    if len(ts) < 2:
        rep.notes.append("dati insufficienti per il walk-forward")
        return rep
    a, b = ts[0], ts[-1] + 1
    span = (b - a) / n_windows
    for w in range(n_windows):
        ws, we = a + int(w * span), a + int((w + 1) * span)
        tr_end = ws + int((we - ws) * train_frac)
        cands = optimize(ds, base, strategy, grid, ws, tr_end, min_trades=min_trades)
        best = cands[0]
        if best.smoothed == float("-inf"):
            rep.notes.append(f"finestra {w + 1}: nessuna combinazione con almeno {min_trades} trade in training")
            continue
        test_res = run_backtest(ds.slice(tr_end, we), _apply(base, strategy, best.params, tr_end, we))
        rep.windows.append(WalkForwardWindow((ws, tr_end), (tr_end, we), best.params, best.smoothed, test_res))
        rep.oos_trades += test_res.metrics.n_trades
        rep.oos_pnl_sol += test_res.metrics.net_profit_sol
    return rep
