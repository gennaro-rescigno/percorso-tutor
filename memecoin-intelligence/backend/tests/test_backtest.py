from datetime import datetime, timedelta, timezone

import pytest

from mci.backtesting.data import Dataset, DatasetInfo, TokenSeries, load_dataset, save_dataset
from mci.backtesting.engine import BacktestConfig, run_backtest
from mci.backtesting.metrics import compute_metrics, max_drawdown
from mci.backtesting.report import render_report
from mci.backtesting.synthetic import scenario_dataset
from mci.backtesting.walkforward import expand_grid, optimize, split_times
from mci.domain import Candle

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _cfg(**kw):
    base = dict(strategy_codes=["A"], p_fail_entry=0.0, p_fail_exit=0.0, seed=1)
    base.update(kw)
    return BacktestConfig(**base)


def test_engine_runs_and_accounts_for_costs():
    ds = scenario_dataset(["grind", "pnd", "noise"])
    res = run_backtest(ds, _cfg())
    m = res.metrics
    assert m.n_trades >= 1
    assert m.total_fees_sol > 0
    # equity identity: final = initial + sum of trade pnl (minus fees of failed orders, none here)
    assert m.final_capital_sol == pytest.approx(2.0 + sum(t.pnl_sol for t in res.trades), abs=1e-9)
    assert "DATI SINTETICI" in render_report("x", {"r": res})


def test_deterministic_with_seed():
    ds = scenario_dataset(["grind", "pnd", "noise", "rug"])
    a = run_backtest(ds, _cfg(p_fail_entry=0.1, seed=7)).metrics
    b = run_backtest(ds, _cfg(p_fail_entry=0.1, seed=7)).metrics
    assert a.final_capital_sol == b.final_capital_sol and a.n_trades == b.n_trades


def test_rug_losses_are_bounded_by_position_sizing():
    ds = scenario_dataset(["rug"] * 6, seed=11)
    res = run_backtest(ds, _cfg(profile="moderate"))
    m = res.metrics
    # many rugs, but a single position can never lose more than its cap
    for t in res.trades:
        assert t.cost_sol <= 2.0 * 0.15 + 0.01
    assert m.max_drawdown_pct < 0.5


def _flat_then_jump(n=120):
    candles = []
    p = 1e-6
    for i in range(n):
        o = p
        if i == 100:
            p *= 3  # a jump that a look-ahead engine would "buy before"
        c = p
        candles.append(Candle(int(T0.timestamp()) + 60 * i, o, max(o, c) * 1.001, min(o, c) * 0.999, c, 1000 + i))
    return candles


def test_no_lookahead_entry_happens_after_signal_bar():
    s = TokenSeries(token="J", symbol="J", pool="pJ", dex_id="raydium", created_at=T0 - timedelta(hours=1),
                    first_seen_at=T0, candles=_flat_then_jump(), timeframe_s=60, reserve_sol0=500, sol_usd=150)
    ds = Dataset([s], DatasetInfo("test", "unit", True, False))
    res = run_backtest(ds, _cfg(strategy_codes=["A"], strategy_params={"A": {"min_change_h1": -100,
                                                                             "min_vol_accel": 0.0}}))
    for t in res.trades:
        # no trade may be entered at a price that is only known after the entry bar opened
        bar_open = {c.ts: c.open for c in s.candles}[int(t.entry_time.timestamp())]
        assert t.entry_price >= bar_open  # filled at/after the open with impact, never at a past price


def test_token_cannot_be_traded_before_discovery():
    candles = _flat_then_jump()
    s = TokenSeries(token="L", symbol="L", pool="pL", dex_id="raydium", created_at=T0, candles=candles,
                    first_seen_at=T0 + timedelta(minutes=110), timeframe_s=60, reserve_sol0=500)
    ds = Dataset([s], DatasetInfo("test", "unit", True, False))
    res = run_backtest(ds, _cfg(strategy_params={"A": {"min_change_h1": -100, "min_vol_accel": 0.0}}))
    for t in res.trades:
        assert t.entry_time >= T0 + timedelta(minutes=110)


HOLD = {"volume_decay_exit": False, "no_progress_minutes": 0, "max_hold_minutes": 10**6,
        "take_profits": [], "trailing_activation_pct": None, "stop_mode": "fixed", "fixed_stop_pct": 0.35}
EASY_A = {"A": {"min_change_h1": -100, "min_vol_accel": 0.0}}


def _series(candles, token="S", first_seen=T0):
    return TokenSeries(token=token, symbol=token, pool=f"p{token}", dex_id="raydium", created_at=T0 - timedelta(hours=1),
                       first_seen_at=first_seen, candles=candles, timeframe_s=60, reserve_sol0=500, sol_usd=150)


def _clock(n):
    return _series([Candle(int(T0.timestamp()) + 60 * i, 1e-6, 1e-6, 1e-6, 1e-6, 0.0) for i in range(n)], "CLOCK")


def test_dead_token_position_is_total_loss():
    # flat token with volume that simply stops trading (delisted / abandoned) while we hold it
    t0 = int(T0.timestamp())
    candles = [Candle(t0 + 60 * i, 1e-6, 1.001e-6, 0.999e-6, 1e-6, 1000.0 + i) for i in range(90)]
    ds = Dataset([_series(candles, "D"), _clock(400)], DatasetInfo("test", "unit", True, False))
    res = run_backtest(ds, _cfg(strategy_params=EASY_A, exit_overrides=HOLD))
    dead = [t for t in res.trades if t.dead_token]
    assert dead, res.trades
    assert dead[0].proceeds_sol == 0 and dead[0].pnl_sol == pytest.approx(-dead[0].cost_sol)


def test_rug_while_holding_fills_at_crash_price_not_at_stop():
    t0 = int(T0.timestamp())
    candles = [Candle(t0 + 60 * i, 1e-6, 1.001e-6, 0.999e-6, 1e-6, 1000.0 + i) for i in range(70)]
    candles.append(Candle(t0 + 60 * 70, 1e-6, 1e-6, 2e-8, 3e-8, 50_000))  # liquidity pulled: -97%
    candles += [Candle(t0 + 60 * i, 3e-8, 3.01e-8, 2.99e-8, 3e-8, 5.0) for i in range(71, 120)]
    ds = Dataset([_series(candles, "R"), _clock(200)], DatasetInfo("test", "unit", True, False))
    res = run_backtest(ds, _cfg(strategy_params=EASY_A, exit_overrides=HOLD))
    assert res.trades
    t = res.trades[0]
    assert t.return_pct < -0.9  # the stop at -35% does NOT protect from a rug
    # but the loss is bounded by position sizing: at most the position, a small share of equity
    assert res.metrics.final_capital_sol > 2.0 * (1 - 0.16)


def test_survivorship_and_reduced_warnings():
    ds = scenario_dataset(["grind"])
    ds.info.survivorship_free = False
    res = run_backtest(ds, _cfg())
    assert any("survivorship" in w for w in res.warnings)
    assert any("OHLCV" in w for w in res.warnings)


def test_small_sample_is_never_declared_robust():
    ds = scenario_dataset(["grind", "pnd"])
    m = run_backtest(ds, _cfg()).metrics
    assert m.robust is False
    assert m.sharpe is None and "non significativi" in m.ratio_note


def test_dataset_roundtrip(tmp_path):
    ds = scenario_dataset(["grind"])
    save_dataset(ds, tmp_path / "d.json")
    ds2 = load_dataset(tmp_path / "d.json")
    assert len(ds2.series) == len(ds.series)
    assert ds2.series[0].candles[5] == ds.series[0].candles[5]


def test_walkforward_helpers():
    ds = scenario_dataset(["grind", "pnd", "noise"])
    sp = split_times(ds)
    assert sp["train"][1] == sp["validation"][0] and sp["validation"][1] == sp["test"][0]
    grid = {"min_vol_accel": [1.0, 1.3], "min_change_h1": [0.0, 5.0]}
    assert len(expand_grid(grid)) == 4
    cands = optimize(ds, _cfg(), "A", grid, *sp["train"], min_trades=1)
    assert len(cands) == 4


def test_metrics_basic():
    assert max_drawdown([1, 2, 1, 3]) == pytest.approx(0.5)
    m = compute_metrics([], [(T0, 2.0)], 2.0)
    assert m.n_trades == 0 and m.win_rate is None
