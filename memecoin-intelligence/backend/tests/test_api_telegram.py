import time

import pytest
from conftest import good_snapshot
from fastapi.testclient import TestClient

from mci.api import auth
from mci.config import reset_settings_cache
from mci.database import repo
from mci.database.session import session_scope
from mci.scoring.scorer import score_token
from mci.telegram import formatters as fm
from mci.telegram.bot import TelegramBot
from mci.telegram.client import TelegramClient


@pytest.fixture()
def client(db, monkeypatch):
    monkeypatch.setenv("MCI_DASHBOARD_PASSWORD", "s3cret-pass")
    monkeypatch.setenv("MCI_API_SECRET_KEY", "k" * 40)
    monkeypatch.setenv("MCI_FRONTEND_DIST_DIR", "/nonexistent")
    reset_settings_cache()
    auth._failures.clear()
    from mci.api.app import create_app

    return TestClient(create_app())


def _login(c):
    r = c.post("/api/auth/login", json={"username": "admin", "password": "s3cret-pass"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_auth_required_and_login(client):
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/overview").status_code == 401
    assert client.post("/api/auth/login", json={"username": "admin", "password": "bad"}).status_code == 401
    h = _login(client)
    r = client.get("/api/overview", headers=h)
    assert r.status_code == 200 and r.json()["summary"]["initial_capital_sol"] == 2.0
    assert client.get("/api/overview", headers={"Authorization": "Bearer forged"}).status_code == 401


def test_login_rate_limited(client):
    for _ in range(auth.MAX_FAILURES):
        client.post("/api/auth/login", json={"username": "admin", "password": "x"})
    assert client.post("/api/auth/login", json={"username": "admin", "password": "s3cret-pass"}).status_code == 429


def test_expired_token_rejected(client, monkeypatch):
    from mci.config import get_settings

    tok, _ = auth.issue_token(get_settings(), "admin")
    monkeypatch.setattr(time, "time", lambda: 10**12)
    assert auth.verify_token(get_settings(), tok) is None


def test_scanner_token_and_control_endpoints(client):
    h = _login(client)
    snap = good_snapshot()
    with session_scope() as s:
        tok = repo.upsert_token(s, snap, "test", score_token(snap))
        repo.add_snapshot(s, tok, snap, None)
    rows = client.get("/api/scanner?sort=liquidity", headers=h).json()["tokens"]
    assert rows and rows[0]["symbol"] == "GOOD" and rows[0]["score"] > 0
    d = client.get(f"/api/tokens/{snap.token_address}", headers=h).json()
    assert d["score"]["categories"]["liquidity"]["max"] == 20 and d["history"]
    assert client.get("/api/tokens/unknown", headers=h).status_code == 404
    for path in ("positions", "signals", "performance", "risk", "logs", "backtests", "config/options"):
        assert client.get(f"/api/{path}", headers=h).status_code == 200, path
    assert client.post("/api/control/pause", headers=h).status_code == 200
    with session_scope() as s:
        assert repo.get_state(s, "control_paused") is True
    assert client.post("/api/control/explode", headers=h).status_code == 400


def test_backtest_lab_synthetic_run(client):
    h = _login(client)
    r = client.post("/api/backtests", headers=h, json={"name": "lab", "strategies": ["A"], "dataset": "synthetic"})
    assert r.status_code == 200
    rid = r.json()["id"]
    for _ in range(100):
        st = client.get(f"/api/backtests/{rid}", headers=h).json()
        if st["status"] in ("done", "failed"):
            break
        time.sleep(0.1)
    assert st["status"] == "done", st.get("error")
    assert "DATI SINTETICI" in st["report_md"]
    assert client.post("/api/backtests", headers=h, json={"strategies": ["Z"]}).status_code == 400


def test_message_formats_distinguish_modes():
    p = {"symbol": "PEPE", "token": "M", "entry_price": 1e-7, "score": 87, "stake_sol": 0.15, "reasons": ["volume"],
         "risks": ["volatilità"], "sol_eur": 140.0}
    paper = fm.buy_message("paper", p)
    live = fm.buy_message("live", p)
    assert "PAPER" in paper and "REALE" in live
    assert "87/100" in paper and "0,1500 SOL" in paper and "21,00 €" in paper
    closed = fm.close_message("paper", {"symbol": "PEPE", "return_pct": 0.185, "net_pnl_sol": 0.02})
    assert "+18,5%" in closed


class FakeTG(TelegramClient):
    def __init__(self):
        super().__init__("token", {111})
        self.out = []

    async def get_updates(self, offset, timeout=30):
        return self._updates

    async def send(self, text, chat_id=None):
        self.out.append((chat_id, text))
        return True


@pytest.mark.asyncio
async def test_bot_commands_and_authorization(db):
    from mci.config import get_settings

    tg = FakeTG()
    bot = TelegramBot(tg, get_settings(), "paper", status_provider=lambda: {"sol_eur": 140.0})
    tg._updates = [
        {"update_id": 0, "message": {"chat": {"id": 999}, "text": "/start"}},  # not authorized: gets its chat id
        {"update_id": 1, "message": {"chat": {"id": 999}, "text": "/pause"}},  # not authorized: ignored
        {"update_id": 2, "message": {"chat": {"id": 111}, "text": "/balance"}},
        {"update_id": 3, "message": {"chat": {"id": 111}, "text": "/pause"}},
        {"update_id": 4, "message": {"chat": {"id": 111}, "text": "/paper"}},
    ]
    await bot.poll_once()
    assert [c for c, _ in tg.out] == [999, 111, 111, 111]
    assert "999" in tg.out[0][1] and "MCI_TELEGRAM_CHAT_IDS" in tg.out[0][1]
    tg.out.pop(0)
    with session_scope() as s:
        assert repo.get_state(s, "control_paused") is True  # set by the AUTHORIZED /pause only
    assert "2,0000 SOL" in tg.out[0][1]
    with session_scope() as s:
        assert repo.get_state(s, "control_paused") is True
    assert "NON può essere attivato da Telegram" in tg.out[2][1]
    for cmd in ("/start", "/status", "/positions", "/signals", "/history", "/performance", "/daily", "/risk",
                "/resume", "/kill", "/help", "/boh"):
        assert bot.handle(cmd)


@pytest.mark.asyncio
async def test_telegram_send_failure_reason_is_recorded_without_token():
    import httpx
    import respx

    token = "123456789:SECRET-SECRET-SECRET-SECRET-SECRET"
    with respx.mock:
        respx.post(f"https://api.telegram.org/bot{token}/sendMessage").mock(
            return_value=httpx.Response(401, json={"ok": False, "description": "Unauthorized"}))
        c = TelegramClient(token, {1})
        assert await c.send("ciao") is False
        await c.close()
    assert c.failed == 1 and c.last_error == "HTTP 401 Unauthorized" and token not in c.last_error


@pytest.mark.asyncio
@pytest.mark.parametrize("setting,expected", [
    ("trades", ["buy", "partial", "close"]),
    ("all", ["buy", "partial", "close", "signal", "token_alert", "anomaly", "text", "stop_hit"]),
])
async def test_only_buys_and_sells_are_notified_by_default(db, monkeypatch, setting, expected):
    from mci.config import get_settings
    from mci.telegram.bot import TelegramNotifier

    monkeypatch.setenv("MCI_TELEGRAM_NOTIFY", setting)
    reset_settings_cache()
    tg = FakeTG()
    n = TelegramNotifier(tg, get_settings(), "paper")
    trade = {"symbol": "PEPE", "token": "M", "entry_price": 1e-7, "score": 87, "stake_sol": 0.15, "reasons": [],
             "risks": [], "sol_eur": 140.0, "return_pct": 0.1, "net_pnl_sol": 0.01, "title": "TAKE PROFIT",
             "fraction": 0.5, "price": 2e-7, "proceeds_sol": 0.08, "new_stop": 1e-7, "reason": "tp"}
    sent = []
    for kind in ("buy", "partial", "close", "signal", "token_alert", "anomaly", "text", "stop_hit"):
        before = len(tg.out)
        payload = dict(trade, text="avviso", strategy="B", name="Pepe", address="M", liquidity_usd=1e5)
        try:
            await n.notify(kind, payload)
        except Exception:
            pass
        if len(tg.out) > before:
            sent.append(kind)
    assert sent == expected


def test_status_shows_why_a_source_is_down(db):
    from mci.config import get_settings

    bot = TelegramBot(FakeTG(), get_settings(), "paper", status_provider=lambda: {
        "sol_eur": 140.0, "sources": {"dexscreener": {"ok": True},
                                      "geckoterminal": {"ok": False, "error": "geckoterminal: rate limited (429)"}}})
    out = bot.handle("/status")
    assert "dexscreener:ok" in out and "geckoterminal:KO (geckoterminal: rate limited (429))" in out


class FakeTGDel(FakeTG):
    def __init__(self):
        super().__init__()
        self.deleted = []

    async def delete_message(self, chat_id, message_id):
        self.deleted.append((chat_id, message_id))
        return True


@pytest.mark.asyncio
async def test_jupiterkey_command_is_private_deleted_and_never_echoed(db):
    from mci.config import get_settings

    key = "jup-free-key-0123456789abcdef"
    tg = FakeTGDel()
    bot = TelegramBot(tg, get_settings(), "paper", status_provider=lambda: {})
    got = []

    async def hook(k):
        got.append(k)
        return "✅ ok"

    bot.on_jupiter_key = hook
    tg._updates = [
        {"update_id": 1, "message": {"message_id": 10, "chat": {"id": 999}, "text": f"/jupiterkey {key}"}},  # stranger
        {"update_id": 2, "message": {"message_id": 11, "chat": {"id": 111}, "text": "/jupiterkey bad key!"}},
        {"update_id": 3, "message": {"message_id": 12, "chat": {"id": 111}, "text": "/jupiterkey"}},
        {"update_id": 4, "message": {"message_id": 13, "chat": {"id": 111}, "text": f"/jupiterkey {key}"}},
    ]
    await bot.poll_once()
    assert got == [key]  # only the owner's well-formed key reaches the worker
    assert tg.deleted == [(111, 11), (111, 12), (111, 13)]  # owner's messages removed, stranger's untouched
    replies = [t for c, t in tg.out if c == 111]
    assert "non valido" in replies[0] and "Uso:" in replies[1] and replies[2] == "✅ ok"
    assert all(key not in t for _, t in tg.out)
    with session_scope() as s:
        from sqlalchemy import select

        from mci.database.models import Event
        assert all(key not in (e.message or "") + str(e.data) for e in s.scalars(select(Event)))


@pytest.mark.asyncio
async def test_jupiter_key_is_verified_before_switching():
    import httpx
    import respx

    from mci.collectors.jupiter import JupiterCollector
    from mci.utils.http import SourceUnavailable

    jc = JupiterCollector("https://lite-api.jup.ag", "", 0.5)
    old = jc.api
    with respx.mock:
        respx.get("https://api.jup.ag/price/v3").mock(return_value=httpx.Response(401, json={"error": "bad key"}))
        with pytest.raises(SourceUnavailable):
            await jc.use_key("wrong-key-0123456789")
    assert jc.api is old and not jc.has_key  # nothing changed
    with respx.mock:
        route = respx.get("https://api.jup.ag/price/v3").mock(return_value=httpx.Response(200, json={}))
        await jc.use_key("good-key-0123456789", rps=1.0)
        assert route.calls.last.request.headers["x-api-key"] == "good-key-0123456789"
    assert jc.has_key and jc.api.base_url == "https://api.jup.ag" and abs(jc.api.limiter.rate - 1.0) < 1e-9
    await jc.close()
    await old.close()


def test_stored_key_is_private_and_scrubbed_from_exports(db, tmp_path, monkeypatch):
    import os
    import stat

    from mci.config import get_settings
    from mci.secrets_store import JUPITER_KEY, jupiter_key, read_secret, write_secret
    from mci.state_io import scrub

    monkeypatch.setenv("MCI_DATA_DIR", str(tmp_path / "data"))
    reset_settings_cache()
    s = get_settings()
    assert jupiter_key(s) == ""
    write_secret(s, JUPITER_KEY, "stored-key-0123456789")
    p = tmp_path / "data" / "secrets" / JUPITER_KEY
    assert stat.S_IMODE(os.stat(p).st_mode) == 0o600
    assert read_secret(s, JUPITER_KEY) == jupiter_key(s) == "stored-key-0123456789"
    assert scrub("errore con stored-key-0123456789") == "errore con ***"
    monkeypatch.setenv("MCI_JUPITER_API_KEY", "env-key-0123456789")  # .env wins over the stored key
    reset_settings_cache()
    assert jupiter_key(get_settings()) == "env-key-0123456789"
