"""Lifecycle journal: facts detected trade by trade, persisted, and the event study built on them."""

from __future__ import annotations

from datetime import datetime, timezone

from mci.chain import pump
from mci.chain.borsh import b58encode
from mci.onchain.journal import Journal, norm_name, real_sol
from mci.onchain.launches import LaunchTracker

V0, T0, R0 = 30 * 10**9, 1_073_000_000 * 10**6, 793_100_000 * 10**6
MINT = "JOURNAL111111111111111111111111111111pump"


class Curve:
    """Constant-product pump.fun curve to build realistic TradeEvents."""

    def __init__(self, tracker: LaunchTracker, mint: str = MINT, created: int = 1_800_000_000, slot: int = 5000):
        self.tr, self.mint, self.created, self.slot = tracker, mint, created, slot
        self.vsol, self.vtok, self.rtok = V0, T0, R0
        tracker.stream_up()
        tracker.gaps.clear()
        tracker._gap_open = None
        tracker.on_events([pump.CreateEvent(name="Pepe Moon", symbol="PM", uri="https://ipfs.io/x", mint=mint,
                                            bonding_curve="BC", user="DEV", creator="DEV", timestamp=created, slot=slot,
                                            virtual_sol_reserves=V0, virtual_token_reserves=T0,
                                            real_token_reserves=R0, token_total_supply=10**15, is_mayhem_mode=False)])

    def buy(self, wallet: str, sol: float, ts: int, slot: int, sig: str | None = None) -> None:
        lam = int(sol * 1e9)
        tok = self.vtok - (self.vsol * self.vtok) // (self.vsol + lam)
        self.vsol, self.vtok, self.rtok = self.vsol + lam, self.vtok - tok, self.rtok - tok
        self._emit(wallet, True, lam, tok, ts, slot, sig)

    def sell(self, wallet: str, tokens: int, ts: int, slot: int, sig: str | None = None) -> None:
        lam = self.vsol - (self.vsol * self.vtok) // (self.vtok + tokens)
        self.vsol, self.vtok, self.rtok = self.vsol - lam, self.vtok + tokens, self.rtok + tokens
        self._emit(wallet, False, lam, tokens, ts, slot, sig)

    def _emit(self, wallet, is_buy, lam, tok, ts, slot, sig):
        self.tr.on_events([pump.TradeEvent(mint=self.mint, sol_amount=lam, token_amount=tok, is_buy=is_buy, user=wallet,
                                           timestamp=ts, virtual_sol_reserves=self.vsol, virtual_token_reserves=self.vtok,
                                           real_sol_reserves=self.vsol - V0, real_token_reserves=self.rtok, slot=slot,
                                           signature=sig, quote_mint="11111111111111111111111111111111")])


def w(i: int) -> str:
    return b58encode(bytes([i % 250 + 1]) * 32)


def build_story() -> tuple[LaunchTracker, Journal, Curve]:
    tr, j = LaunchTracker(), Journal()
    tr.journal = j
    c = Curve(tr)
    t0, s0 = c.created, c.slot
    c.buy("DEV", 1.0, t0, s0)                      # creator's first buy, same slot as the creation
    c.buy(w(1), 0.5, t0, s0)                        # two other buyers in block 0
    c.buy(w(2), 0.5, t0, s0)
    for i in range(30):                             # organic climb: about 0.3 SOL per buy
        c.buy(w(10 + i), 0.3, t0 + 5 + i * 3, s0 + 5 + i)
    c.buy(w(99), 4.0, t0 + 100, s0 + 40)            # whale buy
    for i in range(25):                             # a burst of buyers after 2 minutes: volume spike
        c.buy(w(120 + i), 0.2, t0 + 150 + i, s0 + 60 + i)
    dev_tokens = j.states[MINT].dev_tokens
    c.sell("DEV", dev_tokens, t0 + 200, s0 + 100)  # the creator sells everything
    c.buy(w(200), 0.1, t0 + 210, s0 + 110, sig="SIGWASH")  # atomic wash: buy and sell in one transaction
    c.sell(w(200), 1000, t0 + 210, s0 + 110, sig="SIGWASH")
    held = c.rtok
    c.sell(w(201), (R0 - held) * 7 // 10, t0 + 260, s0 + 150)  # holders dump: drawdown from the peak
    return tr, j, c


def kinds(events):
    return [e["kind"] for e in events]


def test_journal_records_the_facts_of_a_launch():
    tr, j, c = build_story()
    ev = j.drain()
    k = kinds(ev)
    assert k[0] == "create" and "dev_buy" in k and "block0" in k
    b0 = next(e for e in ev if e["kind"] == "block0")
    assert b0["value"] == 2 and b0["detail"]["sol"] == 1.0
    assert [e["value"] for e in ev if e["kind"] == "reserve"][:3] == [5, 10, 20]
    assert any(e["kind"] == "whale_buy" and e["value"] == 4.0 for e in ev)
    assert any(e["kind"] == "volume_spike" for e in ev)
    ds = next(e for e in ev if e["kind"] == "dev_sell")
    assert ds["detail"]["sold_all"] and ds["detail"]["share_of_holding"] == 1.0
    assert k.count("wash_atomic") == 1
    dd = [e["value"] for e in ev if e["kind"] == "drawdown"]
    assert dd and dd[0] == 50
    assert all(e["ts"].tzinfo is not None and e["source"] == "stream" for e in ev)


def test_journal_complete_dead_and_copy():
    tr, j, c = build_story()
    j.drain()
    tr.on_events([pump.CompleteEvent(user="X", mint=MINT, bonding_curve="BC", timestamp=c.created + 900)])
    assert kinds(j.drain()) == ["complete"]
    # a second launch with the same normalized name is a copy; it dies after 30 minutes without trades
    tr2_mint = "COPY1111111111111111111111111111111111pump"
    c2 = Curve(tr, tr2_mint, created=c.created + 1000, slot=9000)
    c2.buy(w(7), 0.2, c2.created + 5, 9002)
    j.tick(now=c2.created + 5 + 1800 + 1)
    ev = j.drain()
    assert "copy" in kinds(ev) and next(e for e in ev if e["kind"] == "copy")["value"] == 1
    assert "dead" in kinds(ev) and "block0" in kinds(ev)
    assert norm_name("Pepe  Moon!") == "pepemoon" and real_sol(35 * 10**9) == 5.0


def test_mayhem_curves_get_no_reserve_or_drawdown_facts():
    tr, j = LaunchTracker(), Journal()
    tr.journal = j
    tr.stream_up()
    tr.on_events([pump.CreateEvent(name="M", symbol="M", uri="", mint=MINT, bonding_curve="BC", user="DEV",
                                   creator="DEV", timestamp=1_800_000_000, slot=1, virtual_sol_reserves=V0,
                                   virtual_token_reserves=T0, real_token_reserves=R0, is_mayhem_mode=True)])
    tr.on_events([pump.TradeEvent(mint=MINT, sol_amount=10**10, token_amount=10**12, is_buy=True, user=w(3),
                                  timestamp=1_800_000_010, virtual_sol_reserves=V0 + 2 * 10**10,
                                  virtual_token_reserves=T0 // 2, real_sol_reserves=2 * 10**10,
                                  real_token_reserves=R0 // 2, slot=5)])
    k = kinds(j.drain())
    assert "reserve" not in k and "whale_buy" in k


def test_events_are_persisted_and_studied(db):
    from mci.research import feature_store as fs
    from mci.research.events import event_study

    tr, j, c = build_story()
    rows = tr.drain(now=c.created + 3 * 3600)
    out = fs.persist_stream(rows)
    assert out["events"] >= 10 and out["bars"] >= 3
    now = datetime.fromtimestamp(c.created + 3 * 3600, tz=timezone.utc)
    rep = event_study(days=1, gaps=[], now=now)
    assert rep["window_min"] == 60 and rep["skipped"]["mayhem_or_unknown"] == 0
    # one launch only: every group is below the minimum size, so nothing is claimed
    assert rep["events"] == [] and "il creatore vende tutto" in rep["small_groups"]
    assert fs.dataset_counts()["token_events"] == out["events"]
    rep_gap = event_study(days=1, gaps=[(c.created - 10, c.created + 3 * 3600)], now=now)
    assert rep_gap["skipped"]["stream_gap"] >= 10


def test_event_study_groups_with_enough_launches(db):
    from mci.research import feature_store as fs
    from mci.research.events import event_study, forward

    tr, j = LaunchTracker(), Journal()
    tr.journal = j
    base = 1_800_000_000
    for n in range(32):
        mint = f"STUDY{n:02d}" + "1" * 29 + "pump"
        c = Curve(tr, mint, created=base + n * 120, slot=10_000 + n * 100)
        c.buy("DEV", 1.0, c.created, c.slot)
        for i in range(12):
            c.buy(w(10 + i), 0.5, c.created + 10 + i * 10, c.slot + 2 + i)
        c.sell("DEV", j.states[mint].dev_tokens, c.created + 200, c.slot + 40)
        c.buy(w(60), 0.2, c.created + 400, c.slot + 60)  # trading goes on after the creator left
    fs.persist_stream(tr.drain(now=base + 32 * 120 + 7200))
    now = datetime.fromtimestamp(base + 32 * 120 + 7200, tz=timezone.utc)
    rep = event_study(days=1, gaps=[], now=now)
    groups = {g["event"]: g for g in rep["events"]}
    g = groups["il creatore vende tutto"]
    assert g["n"] == 32 and g["p_migrated"] == 0.0 and g["baseline"] == "t+5m"  # sold at 3.3 minutes
    assert g["end_median_pct"] > 0  # the later small buy lifts the price above the dump minute's close
    assert forward(1.0, []) == (0.0, 0.0, 0.0)


def test_rules_lab_counts_only_out_of_sample_and_never_claims_small_samples():
    from datetime import timedelta

    from mci.research.rules_lab import REGISTERED_AT, evaluate, net_pct, trade_return

    assert abs(net_pct(0.0) - ((1 / 1.03) * 0.9875 ** 2 - 0.01 - 1) * 100) < 1e-9
    assert trade_return({"first_passage": "half_first"}, "E1") == net_pct(-60.0)
    assert trade_return({"first_passage": "neither", "ret_end_240m": 10.0}, "E1") == net_pct(10.0)
    assert trade_return({"ret_end_60m": None}, "E2") is None
    good = {"n_trades": 120, "drawdown_from_peak_pct": 60, "sniper_pct": 2, "holders_net": 50, "top10_net_pct": 20,
            "creator_sold": False, "buyers_last_60s": 9}
    win = {"first_passage": "2x_first", "ret_end_60m": 50.0, "ret_end_240m": 80.0}
    before = [(REGISTERED_AT - timedelta(hours=1), good, win)] * 500
    after = [(REGISTERED_AT + timedelta(hours=1), good, win)] * 40
    rep = evaluate({"t+5m": before + after, "t+15m": after})
    r1 = next(r for r in rep["results"] if r["rule"] == "R1" and r["exit"] == "E1")
    assert r1["n_in_sample"] == 500 and r1["n_oos"] == 40 and r1["verdict"].startswith("dati insufficienti")
    many = [(REGISTERED_AT + timedelta(minutes=i), good, win) for i in range(400)]
    rep = evaluate({"t+5m": many, "t+15m": many})
    r1 = next(r for r in rep["results"] if r["rule"] == "R1" and r["exit"] == "E1")
    assert r1["n_oos"] == 400 and r1["verdict"].startswith("promettente") and r1["q"] < 0.05
    lose = {"first_passage": "half_first", "ret_end_60m": -70.0, "ret_end_240m": -90.0}
    rep = evaluate({"t+5m": [(REGISTERED_AT + timedelta(minutes=i), good, lose) for i in range(400)]})
    assert all(r["verdict"] == "non funziona" for r in rep["results"] if r["horizon"] == "t+5m")


def test_curves_quoted_in_another_token_have_no_sol_price_or_reserve_facts():
    tr, j = LaunchTracker(), Journal()
    tr.journal = j
    tr.stream_up()
    usdc = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    tr.on_events([pump.CreateEvent(name="U", symbol="U", uri="", mint=MINT, bonding_curve="BC", user="DEV",
                                   creator="DEV", timestamp=1_800_000_000, slot=1, virtual_sol_reserves=V0,
                                   virtual_token_reserves=T0, real_token_reserves=R0, quote_mint=usdc)])
    tr.on_events([pump.TradeEvent(mint=MINT, sol_amount=5 * 10**9, token_amount=10**12, is_buy=True, user=w(3),
                                  timestamp=1_800_000_010, virtual_sol_reserves=V0 + 5 * 10**10,
                                  virtual_token_reserves=T0 // 2, real_sol_reserves=5 * 10**10,
                                  real_token_reserves=R0 // 2, slot=5, quote_mint=usdc)])
    st = tr.get(MINT)
    assert st.price is None and st.launch_price is None and not st.bars
    ev = j.drain()
    assert kinds(ev) == ["create"] and ev[0]["detail"]["quote"] == usdc[:8]


def test_listed_token_facts_from_consecutive_scanner_snapshots(db):
    from datetime import timedelta

    from sqlalchemy import select

    from conftest import good_snapshot
    from mci.database import repo
    from mci.database.models import TokenEvent
    from mci.database.session import session_scope
    from mci.domain import utcnow
    from mci.research.events import listed_study

    t0 = utcnow() - timedelta(hours=3)
    snaps = [good_snapshot(observed_at=t0, bonding_curve=True, boosts_active=0, holders_count=100),
             good_snapshot(observed_at=t0 + timedelta(minutes=2), price_native=0.001 / 150 * 1.8, boosts_active=2,
                           liquidity_usd=50_000, bonding_curve=False, holders_count=200),
             good_snapshot(observed_at=t0 + timedelta(minutes=10), price_native=0.001 / 150 * 1.2)]
    with session_scope() as s:
        for sn in snaps:
            tok = repo.upsert_token(s, sn, "test")
            repo.add_snapshot(s, tok, sn, None)
    with session_scope() as s:
        k = [e.kind for e in s.scalars(select(TokenEvent).order_by(TokenEvent.id)).all()]
        assert k[0] == "listed"
        assert {"price_jump", "boost_on", "liquidity_drop", "migrated", "holders_jump"} <= set(k)
        assert "price_drop" not in k  # 1.8x -> 1.2x is -33%: below the -40% threshold
        assert all(e.source == "scanner" for e in s.scalars(select(TokenEvent)).all())
        assert listed_study(s, t0 - timedelta(hours=1), utcnow()) == []  # fewer than 30 cases: nothing claimed
