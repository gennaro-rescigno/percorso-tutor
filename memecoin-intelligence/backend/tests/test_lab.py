"""Laboratorio: virtual portfolio without risk limits, fully separate from the main one."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import func, select
from test_paper_engine import FakeDex, FakeFx, Notes, _candles, _engine, _tracked

from mci.config import get_settings
from mci.database import repo
from mci.database.models import Event, Position, SignalRow
from mci.database.session import session_scope
from mci.execution.costs import CostModel
from mci.paper_trading.lab import LabEngine
from mci.risk_management.exits import ExitPolicy
from mci.scanner.service import Scanner
from mci.strategies.library import build_strategy

POLICY = ExitPolicy(stop_mode="fixed", fixed_stop_pct=0.2, take_profits=(), trailing_activation_pct=None,
                    volume_decay_exit=False, no_progress_minutes=0)


def _lab(sc=None):
    s = get_settings()
    dex = FakeDex()
    sc = sc or Scanner(s, dex, None, None, None, FakeFx())  # type: ignore[arg-type]
    return LabEngine(s, sc, CostModel(), strategies=[build_strategy("A")], exit_policy=POLICY), sc, sc.dex


def _count(model, **where):
    with session_scope() as s:
        q = select(func.count()).select_from(model)
        for k, v in where.items():
            q = q.where(getattr(model, k) == v)
        return s.scalar(q)


@pytest.mark.asyncio
async def test_lab_trades_when_the_main_portfolio_is_blocked_and_leaves_controls_alone(db):
    notes = Notes()
    main, sc, _ = _engine(notes)
    lab, _, _ = _lab(sc)
    tt = _tracked(sc)
    with session_scope() as s:
        repo.set_state(s, "control_kill", "test")  # main portfolio stopped by the owner
    lab.port.trades_today = 10**6  # far beyond any daily limit
    await lab.on_scan([tt])  # the lab runs first: it must not consume the /kill request
    await main.on_scan([tt])
    assert main.port.kill_switch and not lab.port.kill_switch
    assert _count(Position, mode="lab") == 1 and _count(Position, mode="paper") == 0
    assert main.port.cash == pytest.approx(2.0) and lab.port.cash < 2.0
    # silent: no Telegram, no activity-log entries, no extra signal rows from the lab
    assert "buy" not in notes.kinds()
    assert _count(SignalRow) == 0 or all(m != "lab" for (m,) in _signal_modes())
    with session_scope() as s:
        assert not [e for e in s.scalars(select(Event)) if "APERTA" in e.message]
        assert repo.get_state(s, "portfolio_lab")["cash"] == pytest.approx(lab.port.cash)


def _signal_modes():
    with session_scope() as s:
        return s.execute(select(SignalRow.mode)).all()


@pytest.mark.asyncio
async def test_lab_has_no_cooldown_and_uses_the_same_exit_rules(db, monkeypatch):
    from datetime import timedelta

    import mci.paper_trading.engine as engine_mod

    lab, sc, dex = _lab()
    tt = _tracked(sc)
    await lab.on_scan([tt])
    with session_scope() as s:
        p = repo.open_positions(s, "lab")[0]
        entry = p.entry_price
    dex.price_native = entry * 0.7  # below the 20% stop
    await lab.monitor_positions()
    with session_scope() as s:
        closed = repo.closed_positions(s, "lab")
        assert len(closed) == 1 and closed[0].realized_pnl_sol < 0 and "stop" in closed[0].exit_reason.lower()
    # the main portfolio would wait 12 h (cooldown); the lab re-enters on the next signal
    # (a few minutes later: two buys of the same token in the same minute are blocked as duplicate orders)
    later = engine_mod.utcnow() + timedelta(minutes=3)
    monkeypatch.setattr(engine_mod, "utcnow", lambda: later)
    tt.candles["1m"] = _candles(start_price=entry * 0.7 / 1.2)
    tt.snapshot.price_native = tt.candles["1m"][-1].close
    await lab.on_scan([tt])
    assert _count(Position, mode="lab") == 2


@pytest.mark.asyncio
async def test_lab_counts_signals_it_cannot_simulate(db):
    lab, sc, _ = _lab()
    tt = _tracked(sc)
    lab.port.cash = 0.0  # capital exhausted: a physical limit, not a risk rule
    await lab.on_scan([tt])
    with session_scope() as s:
        assert repo.get_state(s, "lab_skipped") == {"capitale non disponibile": 1}
    assert _count(Position, mode="lab") == 0


@pytest.mark.asyncio
async def test_lab_page_data_and_static_export(db, tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from mci.api import auth
    from mci.config import reset_settings_cache
    from mci.state_io import export_static

    lab, sc, dex = _lab()
    tt = _tracked(sc)
    await lab.on_scan([tt])
    with session_scope() as s:
        entry = repo.open_positions(s, "lab")[0].entry_price
    dex.price_native = entry * 0.7
    await lab.monitor_positions()
    lab.mark_to_market(140.0, 150.0, record=True)

    monkeypatch.setenv("MCI_DASHBOARD_PASSWORD", "s3cret-pass")
    monkeypatch.setenv("MCI_API_SECRET_KEY", "k" * 40)
    monkeypatch.setenv("MCI_FRONTEND_DIST_DIR", "/nonexistent")
    reset_settings_cache()
    auth._failures.clear()
    from mci.api.app import create_app

    c = TestClient(create_app())
    tok = c.post("/api/auth/login", json={"username": "admin", "password": "s3cret-pass"}).json()["token"]
    d = c.get("/api/lab", headers={"Authorization": f"Bearer {tok}"}).json()
    assert d["enabled"] and d["started_at"] and d["summary"]["mode"] == "lab"
    a = {r["strategy"]: r for r in d["by_strategy"]}["A"]
    assert a["trades"] == 1 and a["losses"] == 1 and a["win_rate"] == 0.0 and a["avg_return"] < 0
    assert len(d["positions"]) == 1 and d["positions"][0]["status"] == "closed"
    assert d["equity_curve"] and d["main_by_strategy"] == []
    assert c.get("/api/lab").status_code == 401  # login required on the private API

    export_static(tmp_path / "site")
    pub = json.loads((tmp_path / "site" / "lab.json").read_text())
    assert pub["by_strategy"][0]["strategy"] == "A"


def test_zero_cooldown_never_blocks_even_with_clock_skew():
    """Lab profile: cooldown 0 must not block a re-entry, even if the last exit looks 'in the future'."""
    from datetime import timedelta

    from mci.domain import Signal, utcnow
    from mci.risk_management.manager import PortfolioState, RiskManager
    from mci.risk_management.profiles import LAB

    st = PortfolioState(equity=2.0, cash=2.0, peak_equity=2.0, day_start_equity=2.0)
    st.last_exit["T"] = (utcnow() + timedelta(minutes=5), -0.01)
    sig = Signal(strategy="A", token_address="T", symbol="T", created_at=utcnow(), reference_price=1.0,
                 stop_price=0.8, score=10.0, reasons=[], risks=[])
    rd = RiskManager(LAB, CostModel()).check_entry(st, sig, now=utcnow(), reserve_sol=500.0, fee_pct=0.0025)
    assert not any("cooldown" in r for r in rd.reasons), rd.reasons
