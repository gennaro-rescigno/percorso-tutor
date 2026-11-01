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


def test_scanner_resumes_tokens_history_and_candles_from_db(db):
    from mci.config import get_settings
    from mci.domain import Candle
    from mci.scanner.service import Scanner

    snap = _seed()
    t0 = int((utcnow() - timedelta(hours=2)).timestamp()) // 60 * 60
    with session_scope() as s:
        repo.upsert_candles(s, snap.token_address, snap.pair_address, "1m",
                            [Candle(t0 + 60 * i, 1.0, 1.1, 0.9, 1.05, 100.0) for i in range(90)])
        old = good_snapshot(token_address="OldDeadMint", symbol="OLD")
        tok = repo.upsert_token(s, old, "test", None)
        tok.status = "dead"
    sc = Scanner(get_settings(), None, None, None, None, None)  # type: ignore[arg-type]
    assert sc.load_from_db() == 1  # the dead token is not resumed
    tt = sc.tokens[snap.token_address]
    assert tt.snapshot.symbol == "GOOD" and tt.source == "db"
    assert len(tt.candles["1m"]) == 90 and len(tt.history) == 1
    assert sc.load_from_db() == 0  # idempotent


def test_import_full_chain_and_truncated_history(db, tmp_path, monkeypatch):
    """Regression (live run on main): positions reference signals; import order and FKs."""
    from mci.database.models import FillRow, Order, SignalRow
    from mci.domain import Signal

    snap = _seed()
    with session_scope() as s:
        sig = repo.record_signal(s, Signal(strategy="B", token_address=snap.token_address, symbol="GOOD",
                                           created_at=utcnow(), reference_price=1e-5, stop_price=9e-6, score=78,
                                           reasons=["r"], risks=[]), "paper", snap, None)
        p = s.scalars(__import__("sqlalchemy").select(Position)).first()
        p.signal_id = sig.id
        o = Order(client_order_id="paper-buy-x", mode="paper", side="buy", token_address=snap.token_address,
                  position_id=p.id, signal_id=sig.id, status="filled", requested_sol=0.08)
        s.add(o)
        s.flush()
        s.add(FillRow(order_id=o.id, side="buy", qty=1000, price=1e-5, sol_amount=0.08, dex_fee_sol=0.001,
                      network_fee_sol=0.0001, slippage_sol=0.0, price_impact_pct=0.01, quote_source="jupiter"))
    export_state(tmp_path / "state.json")
    data = json.loads((tmp_path / "state.json").read_text())
    data["signals"] = []  # simulate a signal older than the exported window
    (tmp_path / "state2.json").write_text(json.dumps(data))
    for name in ("state.json", "state2.json"):
        url2 = f"sqlite:///{tmp_path}/{name}.db"
        monkeypatch.setenv("MCI_DATABASE_URL", url2)
        reset_settings_cache()
        init_engine(url2)
        got = import_state(tmp_path / name)
        assert got["positions"] == 1 and got["orders"] == 1 and got["fills"] == 1
        with session_scope() as s:
            from sqlalchemy import select

            pos = s.scalars(select(Position)).one()
            assert (pos.signal_id is not None) == (name == "state.json")
            assert s.scalars(select(FillRow)).one().order_id == s.scalars(select(Order)).one().id


def test_new_rows_after_import_do_not_reuse_imported_ids(db, tmp_path):
    """Moving the bot to a server: import into an empty PostgreSQL database, then keep working.
    Regression: sequences were not advanced past imported ids -> 'duplicate key events_pkey' at startup."""
    from sqlalchemy import create_engine, func, select

    from mci.database.models import Base, Event

    _seed()
    with session_scope() as s:
        for i in range(5):
            repo.log_event(s, "system", f"evento storico {i}")
    export_state(tmp_path / "state.json")
    eng = create_engine(db)
    Base.metadata.drop_all(eng)  # brand new empty database of the same kind (SQLite or PostgreSQL)
    eng.dispose()
    init_engine(db)
    got = import_state(tmp_path / "state.json")
    assert got["events"] >= 6 and got["positions"] == 1
    with session_scope() as s:
        last_imported = s.scalar(select(func.max(Event.id)))
    with session_scope() as s:
        repo.log_event(s, "system", "worker avviato in modalità paper")
        s.add(Position(mode="paper", token_address="NewMint", symbol="NEW", strategy="C", status="open",
                       opened_at=utcnow(), entry_price=1e-5, qty_initial=1, qty=1, stake_sol=0.01, cost_sol=0.011,
                       stop_price=8e-6, initial_stop=8e-6, take_profits=[], last_price=1e-5, state={}))
    with session_scope() as s:
        assert s.scalar(select(func.max(Event.id))) > last_imported
        assert s.scalar(select(func.count()).select_from(Position)) == 2


def test_publish_static_once_writes_site_and_fresh_data(db, tmp_path, monkeypatch):
    """VPS read-only dashboard: frontend copied, data/ swapped in, no leftovers, secrets scrubbed."""
    import json as _json

    from mci.cli import main

    _seed()
    site = tmp_path / "static-dist"
    (site / "assets").mkdir(parents=True)
    (site / "index.html").write_text("<html>dashboard</html>")
    (site / "assets" / "app.js").write_text("x")
    out = tmp_path / "srv"
    monkeypatch.setenv("MCI_TELEGRAM_BOT_TOKEN", "123456789:SECRET-SECRET-SECRET-SECRET-SECRET")
    monkeypatch.setenv("MCI_FRONTEND_DIST_DIR", "/nonexistent")
    reset_settings_cache()
    for _ in range(2):  # second round replaces the first atomically
        assert main(["publish-static", "--out", str(out), "--site", str(site), "--once"]) == 0
    assert (out / "index.html").read_text() == "<html>dashboard</html>" and (out / "assets" / "app.js").exists()
    overview = _json.loads((out / "data" / "overview.json").read_text())
    assert overview["summary"]["initial_capital_sol"] == 2.0
    assert (out / "data" / "positions.json").exists() and (out / "data" / "meta.json").exists()
    assert not list(out.glob(".data-*")) and not list(out.glob(".old-*"))
    blob = "".join(f.read_text() for f in (out / "data").rglob("*.json"))
    assert "SECRET-SECRET" not in blob
