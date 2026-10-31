"""End-to-end test of the scanner loop against a mocked HTTP transport.

The payloads are synthetic test fixtures shaped like the documented API-Football responses;
they exercise the real code path (HTTP client -> parsing -> DB -> model -> filters ->
opportunity lifecycle -> settlement) without network access. Nothing here is used by the app.
"""
import datetime as dt
import json

import httpx
import pytest

from app import db as dbmod
from app.config import Settings
from app.engine.model import DEFAULT_MODEL_PATH, ModelBundle
from tests.test_providers import fixture_payload

pytestmark = pytest.mark.skipif(not DEFAULT_MODEL_PATH.exists(), reason="model not trained")


class FakeApi:
    def __init__(self):
        self.live = True
        self.odds_values: list[dict] = []
        self.calls: list[str] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        p = request.url.path
        q = dict(request.url.params)
        self.calls.append(f"{p}?{request.url.query.decode()}")
        assert request.headers.get("x-apisports-key") == "test-key"
        now = dt.datetime.now(dt.timezone.utc).isoformat()
        resp: list = []
        if p == "/fixtures" and q.get("live"):
            resp = [fixture_payload(with_stats=False)] if self.live else []
        elif p == "/fixtures" and q.get("ids"):
            resp = [fixture_payload()]
        elif p == "/fixtures" and q.get("team"):
            tid = int(q["team"])
            resp = []
            for i in range(10):
                item = fixture_payload(fid=5000 + i + 100 * tid, status="FT", elapsed=90, gh=2, ga=1)
                item["teams"]["home"]["id"] = tid
                item["score"]["fulltime"] = {"home": 2, "away": 1}
                item["fixture"]["date"] = f"2026-10-{10 + i:02d}T18:00:00+00:00"
                resp.append(item)
        elif p == "/fixtures" and q.get("id"):
            item = fixture_payload(status="FT", elapsed=90, gh=3, ga=2)
            item["score"]["fulltime"] = {"home": 3, "away": 2}
            resp = [item]
        elif p == "/odds/live":
            resp = [{"fixture": {"id": 1001, "status": {"elapsed": 72}},
                     "teams": {"home": {"id": 1, "goals": 2}, "away": {"id": 2, "goals": 2}},
                     "status": {"stopped": False, "blocked": False, "finished": False}, "update": now,
                     "odds": [{"id": 36, "name": "Over/Under Line", "values": self.odds_values}]}]
        body = {"get": p, "parameters": q, "errors": [], "results": len(resp), "paging": {"current": 1, "total": 1},
                "response": resp}
        return httpx.Response(200, json=body, headers={"x-ratelimit-requests-limit": "7500",
                                                       "x-ratelimit-requests-remaining": "7000"})


@pytest.fixture()
def scanner(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    from app.config import get_settings
    get_settings.cache_clear()
    dbmod.reset_engine_for_tests()
    from app.services.scanner import Scanner
    s = Settings(api_football_key="test-key", the_odds_api_key=None, database_url=f"sqlite:///{tmp_path / 'test.db'}",
                 n_param_draws=60)
    sc = Scanner(s, ModelBundle.load(DEFAULT_MODEL_PATH))
    fake = FakeApi()
    sc.af.client = httpx.Client(base_url="https://v3.football.api-sports.io", transport=httpx.MockTransport(fake.handler),
                                headers={"x-apisports-key": "test-key"})
    yield sc, fake
    dbmod.reset_engine_for_tests()
    get_settings.cache_clear()


def test_full_cycle(scanner):
    sc, fake = scanner
    fake.odds_values = [{"value": "Over", "odd": "2.10", "handicap": "4.5", "main": True, "suspended": False},
                        {"value": "Under", "odd": "1.70", "handicap": "4.5", "main": True, "suspended": False}]
    sc.cycle()
    st = sc.snapshot()
    assert st["n_live"] == 1
    det = sc.fixture_detail(1001)
    assert det["analysable"] and det["model"]["goal_model"] == "goals_xg"
    assert det["form"]["home"]["matches"] == 10
    ev = {e["key"]: e for e in det["evaluations"]}
    over = ev["total_goals:over@4.5"]
    under = ev["total_goals:under@4.5"]
    assert over["p_market_fair"] is not None and abs(over["p_market_fair"] + under["p_market_fair"] - 1) < 1e-9
    assert any("inferiore alla soglia" in r for r in under["fail_reasons"])  # 1.70 < 1.75
    # windows unavailable on the first snapshot -> reported, not invented
    assert det["windows"]["w10"] is None

    # cycle 2: only the Over side quoted at a price well above the model's prudential fair price
    p_cons = over["p_cons"]
    price = round(max(1.80, 1.35 / max(p_cons, 0.05)), 2)
    fake.odds_values = [{"value": "Over", "odd": str(price), "handicap": "4.5", "main": True, "suspended": False}]
    sc.cycle()
    st = sc.snapshot()
    assert st["n_opportunities"] == 1, sc.fixture_detail(1001)["evaluations"]
    opp = st["opportunities"][0]
    assert opp["market"] == "total_goals" and opp["odds"] >= 1.75 and opp["ev_cons"] > 0
    assert opp["reasons"] and opp["risks"]
    assert opp["confidence_label"] in ("alta", "media", "bassa")
    json.dumps(st)  # serialisable for the WebSocket

    # cycle 3: odds drop below 1.75 -> immediately invalidated
    fake.odds_values = [{"value": "Over", "odd": "1.70", "handicap": "4.5", "main": True, "suspended": False}]
    sc.cycle()
    st = sc.snapshot()
    assert st["n_opportunities"] == 0
    assert "inferiore alla soglia" in st["invalidated"][0]["reason"]

    # cycle 4: match leaves the live list -> final result fetched -> settled for backtesting
    fake.live = False
    sc.cycle()
    from app.db import Opportunity, Prediction, session
    with session() as db:
        o = db.query(Opportunity).one()
        assert o.result == "win" and o.profit == pytest.approx(price - 1)
        assert db.query(Prediction).filter(Prediction.result.isnot(None)).count() > 0
    from app.services.backtest import metrics
    with session() as db:
        m = metrics(db)
    assert m["overall"]["n"] == 1 and m["overall"]["wins"] == 1
    assert any(c.startswith("/fixtures?id=1001") for c in fake.calls)


def test_no_key_means_no_data(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 't2.db'}")
    from app.config import get_settings
    get_settings.cache_clear()
    dbmod.reset_engine_for_tests()
    from app.services.scanner import Scanner
    sc = Scanner(Settings(api_football_key=None, database_url=f"sqlite:///{tmp_path / 't2.db'}"), None)
    sc.cycle()
    st = sc.snapshot()
    assert st["n_live"] == 0 and st["opportunities"] == [] and "non configurata" in st["message"]
    dbmod.reset_engine_for_tests()
    get_settings.cache_clear()
