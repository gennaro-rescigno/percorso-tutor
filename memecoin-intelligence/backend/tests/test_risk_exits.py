from datetime import timedelta

import pytest

from mci.domain import Signal, utcnow
from mci.execution.costs import CostModel
from mci.risk_management.exits import EXIT_POLICIES, ExitPolicy, PositionState, evaluate_bar, initial_stop
from mci.risk_management.manager import PortfolioState, RiskManager
from mci.risk_management.profiles import MODERATE


def _pos(entry=1.0, stop=0.8):
    return PositionState(token="T", strategy="B", entry_time=utcnow(), entry_price=entry, qty_initial=100, qty=100,
                         cost_sol=100, stop_price=stop, initial_stop=stop, high_water=entry, entry_volume_ref=1000)


def test_gap_below_stop_fills_at_open():
    p = _pos()
    acts = evaluate_bar(p, ExitPolicy(), now=utcnow(), open_=0.5, high=0.55, low=0.4, close=0.45)
    assert acts[0].reason == "STOP_GAP" and acts[0].price_hint == 0.5


def test_stop_checked_before_take_profit_in_same_bar():
    p = _pos()
    acts = evaluate_bar(p, ExitPolicy(), now=utcnow(), open_=1.0, high=1.6, low=0.7, close=1.0)
    assert [a.reason for a in acts] == ["STOP_LOSS"]


def test_take_profit_ladder_and_trailing_next_bar():
    pol = ExitPolicy(take_profits=((0.5, 0.33), (1.0, 0.33)), trailing_activation_pct=0.4, trailing_pct=0.25,
                     volume_decay_exit=False)
    p = _pos()
    acts = evaluate_bar(p, pol, now=utcnow(), open_=1.0, high=1.55, low=0.95, close=1.5)
    assert [a.reason for a in acts] == ["TAKE_PROFIT_1"]
    assert acts[0].qty == pytest.approx(33)
    p.qty -= acts[0].qty
    # trailing/BE are pending, applied from the next bar only
    assert p.stop_price == 0.8 and p.pending_stop is not None
    evaluate_bar(p, pol, now=utcnow(), open_=1.5, high=1.5, low=1.45, close=1.47)
    assert p.stop_price == pytest.approx(1.55 * 0.75)
    assert p.be_moved


def test_breakeven_never_policy():
    pol = EXIT_POLICIES["ladder_no_be"]
    p = _pos()
    evaluate_bar(p, pol, now=utcnow(), open_=1.0, high=1.3, low=0.99, close=1.2)
    evaluate_bar(p, pol, now=utcnow(), open_=1.2, high=1.2, low=1.1, close=1.15)
    assert not p.be_moved


def test_time_and_no_progress_stops():
    pol = ExitPolicy(no_progress_minutes=30, max_hold_minutes=600, volume_decay_exit=False)
    p = _pos()
    acts = evaluate_bar(p, pol, now=utcnow() + timedelta(minutes=31), open_=1.0, high=1.01, low=0.99, close=1.0)
    assert acts and acts[0].reason == "NO_PROGRESS"


def test_liquidity_drop_exit():
    p = _pos()
    p.entry_reserve_sol = 100
    acts = evaluate_bar(p, ExitPolicy(), now=utcnow(), open_=1.0, high=1.0, low=0.95, close=0.97, reserve_sol=40)
    assert acts[0].reason == "LIQUIDITY_DROP"


def test_initial_stop_clamped():
    pol = ExitPolicy(stop_mode="atr", atr_mult=2.5, min_stop_pct=0.1, max_stop_pct=0.35)
    assert initial_stop(pol, 1.0, None, 0.5) == pytest.approx(0.65)  # clamped to 35%
    assert initial_stop(pol, 1.0, None, 0.001) == pytest.approx(0.9)  # clamped to 10%


def _sig(token="T", score=80):
    return Signal(strategy="B", token_address=token, symbol="T", created_at=utcnow(), reference_price=1.0,
                  stop_price=0.8, score=score, reasons=[], risks=[])


def _rm():
    return RiskManager(MODERATE, CostModel())


def test_risk_manager_limits():
    rm = _rm()
    st = PortfolioState(equity=2.0, cash=2.0, peak_equity=2.0)
    now = utcnow()
    for i in range(MODERATE.max_positions):
        d = rm.check_entry(st, _sig(f"T{i}"), now=now, reserve_sol=300, fee_pct=0.01)
        assert d.allowed, d.reasons
        rm.on_entry(st, f"T{i}", d.size_sol)
    d = rm.check_entry(st, _sig("T9"), now=now, reserve_sol=300, fee_pct=0.01)
    assert not d.allowed and any("posizioni" in r for r in d.reasons)


def test_cooldown_after_loss_and_consecutive_losses_pause():
    rm = _rm()
    st = PortfolioState(equity=2.0, cash=2.0, peak_equity=2.0)
    now = utcnow()
    rm.on_entry(st, "A", 0.1)
    rm.on_exit(st, "A", -0.02, now, closed=True)
    d = rm.check_entry(st, _sig("A"), now=now + timedelta(minutes=5), reserve_sol=300, fee_pct=0.01)
    assert not d.allowed and any("cooldown" in r for r in d.reasons)
    for i in range(MODERATE.max_consecutive_losses):
        rm.on_entry(st, f"L{i}", 0.1)
        rm.on_exit(st, f"L{i}", -0.01, now, closed=True)
    d = rm.check_entry(st, _sig("NEW"), now=now + timedelta(minutes=1), reserve_sol=300, fee_pct=0.01)
    assert not d.allowed and any("pausa" in r for r in d.reasons)


def test_daily_loss_limit_and_drawdown_kill_switch():
    rm = _rm()
    st = PortfolioState(equity=2.0, cash=2.0, peak_equity=2.0)
    now = utcnow()
    rm.roll_day(st, now)
    rm.update_equity(st, 2.0 * (1 - MODERATE.daily_loss_limit_pct - 0.01), 1.8, now)
    d = rm.check_entry(st, _sig(), now=now, reserve_sol=300, fee_pct=0.01)
    assert not d.allowed and any("giornaliero" in r for r in d.reasons)
    alerts = rm.update_equity(st, 2.0 * (1 - MODERATE.max_drawdown_pause_pct - 0.01), 1.3, now)
    assert st.kill_switch and alerts
    RiskManager.resume(st)
    assert not st.kill_switch and st.peak_equity == st.equity


def test_market_anomaly_blocks_entries():
    rm = _rm()
    st = PortfolioState(equity=2.0, cash=2.0, peak_equity=2.0)
    d = rm.check_entry(st, _sig(), now=utcnow(), reserve_sol=300, fee_pct=0.01, market_anomaly="SOL -12%")
    assert not d.allowed


def test_low_score_rejected_by_profile():
    rm = _rm()
    st = PortfolioState(equity=2.0, cash=2.0, peak_equity=2.0)
    d = rm.check_entry(st, _sig(score=50), now=utcnow(), reserve_sol=300, fee_pct=0.01)
    assert not d.allowed
