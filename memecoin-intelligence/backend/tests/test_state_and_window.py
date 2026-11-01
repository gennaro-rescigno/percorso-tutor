"""State persistence across scheduled runs (GitHub Actions mode) and static dashboard export."""

from __future__ import annotations

import json
from datetime import timedelta

import pytest
from conftest import good_snapshot

from mci.config import reset_settings_cache
from mci.database import repo
from mci.database.models import Position
from mci.database.session import init_engine, session_scope
from mci.domain import utcnow
from mci.scoring.scorer import score_token
from mci.state_io import export_state, export_static, import_state


def _seed():
    now = utcnow()
    snap = good_snapshot()
    with session_scope() as s:
        tok = repo.upsert_token(s, snap, "test", score_token(snap))
        repo.add_snapshot(s, tok, snap, None)
        repo.set_state(s, "portfolio_paper", {"equity": 2.1, "cash": 1.9, "peak_equity": 2.2, "exposure": {},
                                              "kill_switch": False, "day_start_equity": 2.0})
        repo.set_state(s, "telegram_offset", 12345)
        s.add(Position(mode="paper", token_address=snap.token_address, symbol="GOOD", strategy="B", status="open",
                       opened_at=now - timedelta(hours=1), entry_price=1e-5, qty_initial=1000, qty=1000,
                       stake_sol=0.05, cost_sol=0.052, stop_price=8e-6, initial_stop=8e-6, take_profits=[],
                       last_price=1.1e-5, state={"entry_time": now.isoformat(), "x": 1}))
        repo.add_equity_snapshot(s, "paper", 2.1, 1.9, 0.2, 0.0, 140.0, 150.0)
        repo.log_event(s, "system", "seed")
    return snap


def test_state_roundtrip_restores_portfolio_after_cache_loss(db, tmp_path, monkeypatch):
    _seed()
    counts = export_state(tmp_path / "state.json")
    assert counts["positions"] == 1 and counts["system_state"] >= 2
    # simulate cache eviction: brand new empty database
    url2 = f"sqlite:///{tmp_path}/fresh.db"
    monkeypatch.setenv("MCI_DATABASE_URL", url2)
    reset_settings_cache()
    init_engine(url2)
    got = import_state(tmp_path / "state.json")
    assert got["positions"] == 1
    with session_scope() as s:
        assert repo.get_state(s, "portfolio_paper")["equity"] == 2.1
        assert repo.get_state(s, "telegram_offset") == 12345
        p = repo.open_positions(s, "paper")[0]
        assert p.symbol == "GOOD" and p.state["x"] == 1 and p.opened_at is not None
    # a second import never overwrites a live database
    assert import_state(tmp_path / "state.json") == {"skipped": 1}


def test_export_static_writes_dashboard_json(db, tmp_path, monkeypatch):
    snap = _seed()
    monkeypatch.setenv("MCI_FRONTEND_DIST_DIR", "/nonexistent")
    n = export_static(tmp_path / "site")
    assert n >= 9
    ov = json.loads((tmp_path / "site" / "overview.json").read_text())
    assert ov["summary"]["equity_sol"] == 2.1
    assert (tmp_path / "site" / "tokens" / f"{snap.token_address}.json").exists()
    assert json.loads((tmp_path / "site" / "positions.json").read_text())["positions"][0]["symbol"] == "GOOD"
    assert json.loads((tmp_path / "site" / "meta.json").read_text())["static"] is True
    # no secrets in the exported files
    blob = "".join(p.read_text() for p in (tmp_path / "site").rglob("*.json"))
    assert "s3cret" not in blob and "MCI_TELEGRAM_BOT_TOKEN" not in blob


@pytest.mark.asyncio
async def test_run_window_persists_and_sends_daily_report_once(db, monkeypatch):
    monkeypatch.setenv("MCI_PUMPPORTAL_ENABLED", "false")
    monkeypatch.setenv("MCI_DAILY_REPORT_HOUR_UTC", "0")
    monkeypatch.setenv("MCI_SCAN_INTERVAL_SECONDS", "1")
    monkeypatch.setenv("MCI_POSITION_MONITOR_INTERVAL_SECONDS", "1")
    reset_settings_cache()
    from mci.worker import Worker

    w = Worker()
    calls = {"scan": 0, "monitor": 0}
    sent: list[str] = []

    async def scan():
        calls["scan"] += 1

    async def monitor():
        calls["monitor"] += 1

    async def fx_get():
        return None

    async def notify(kind, payload):
        sent.append(kind)

    monkeypatch.setattr(w, "scan_once", scan)
    monkeypatch.setattr(w, "monitor_once", monitor)
    monkeypatch.setattr(w.fx, "get", fx_get)
    monkeypatch.setattr(w.notifier, "notify", notify)
    w.bot.offset = None
    await w.run_window(2)
    assert calls["scan"] >= 1 and calls["monitor"] >= 1
    assert sent.count("daily") == 1
    with session_scope() as s:
        assert repo.get_state(s, "last_daily_report") == utcnow().date().isoformat()
        assert repo.get_state(s, "worker_status")["run_mode"] == "server"
    # next window the same day: no second daily report
    w2 = Worker()
    monkeypatch.setattr(w2, "scan_once", scan)
    monkeypatch.setattr(w2, "monitor_once", monitor)
    monkeypatch.setattr(w2.fx, "get", fx_get)
    monkeypatch.setattr(w2.notifier, "notify", notify)
    await w2.run_window(1)
    assert sent.count("daily") == 1


def test_secrets_never_published(db, tmp_path, monkeypatch):
    token = "1234567890:AAH-very-secret-telegram-token"
    monkeypatch.setenv("MCI_TELEGRAM_BOT_TOKEN", token)
    monkeypatch.setenv("MCI_FRONTEND_DIST_DIR", "/nonexistent")
    reset_settings_cache()
    _seed()
    with session_scope() as s:  # simulate an error message that leaked the bot URL
        repo.log_event(s, "error", f"ConnectError https://api.telegram.org/bot{token}/getUpdates", level="error")
    export_state(tmp_path / "state.json")
    export_static(tmp_path / "site")
    blob = (tmp_path / "state.json").read_text() + "".join(p.read_text() for p in (tmp_path / "site").rglob("*.json"))
    assert token not in blob and "***" in blob
