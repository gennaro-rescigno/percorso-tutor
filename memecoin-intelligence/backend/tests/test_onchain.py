"""Chain stream, launch tracker, curve features, wallet clusters, risk/opportunity indices, feature store,
research statistics, promotion gate, sell simulation and the x_curve experiment."""

from __future__ import annotations

import base64
import json
import time
from datetime import timedelta
from pathlib import Path

import httpx
import numpy as np
import pytest

from mci.chain import pump
from mci.chain.borsh import b58encode
from mci.chain.rpc_pool import RpcPool
from mci.chain.stream import PumpStream
from mci.chain.tokens import analyze_mint
from mci.chain.tx import parse_transaction
from mci.domain import TokenSnapshot, utcnow
from mci.execution.network_costs import effective_priority_fee
from mci.execution.sell_sim import classify_simulation
from mci.onchain.curve_features import curve_features, early_buyers
from mci.onchain.launches import LaunchTracker
from mci.onchain.service import OnchainService, apply_security
from mci.onchain.wallets import cluster_early_buyers
from mci.research.evaluate import auc, evaluate_rows
from mci.scoring.filters import evaluate_filters
from mci.scoring.risk_opportunity import opportunity_index, risk_index

from conftest import good_snapshot

LIVE = Path(__file__).parent / "fixtures" / "live"


def live(name: str):
    return json.loads((LIVE / f"{name}.json").read_text())


def normal_launch(tracker: LaunchTracker | None = None) -> tuple[LaunchTracker, str]:
    d = live("early_txs_normal")
    tr = tracker or LaunchTracker()
    tr.stream_up()
    c = d["create"]
    tr.on_events([pump.CreateEvent(name="T", symbol="T", uri="", mint=c["mint"], bonding_curve=c["bonding_curve"],
                                   user=c["creator"], creator=c["creator"], timestamp=d["txs"][0]["blockTime"],
                                   slot=c["slot"], real_token_reserves=793_100_000 * 10**6)])
    for t in d["txs"]:
        tr.on_events(parse_transaction(t).events)
    return tr, c["mint"]


# ----------------------------------------------------------------------------- stream
def _ws_message(tx: dict) -> str:
    return json.dumps({"jsonrpc": "2.0", "method": "logsNotification", "params": {"result": {
        "context": {"slot": tx["slot"]},
        "value": {"signature": tx["transaction"]["signatures"][0], "err": tx["meta"]["err"],
                  "logs": tx["meta"]["logMessages"]}}, "subscription": 1}})


def test_stream_decodes_real_logs_and_skips_failed():
    got = []
    stream = PumpStream("wss://example", got.extend)
    d = live("early_txs_normal")
    for t in d["txs"]:
        stream.handle_raw(_ws_message(t))
    assert stream.stats["skipped_failed"] == 2  # failed txs never parsed
    assert stream.stats["trades"] == 13 and len(got) == 13
    stream.handle_raw('{"jsonrpc":"2.0","result":7,"id":1}')  # subscription ack
    stream.handle_raw("not json" + '"err":null')
    assert stream.stats["bad_messages"] == 1


def test_stream_handler_errors_do_not_kill_the_stream():
    def boom(_):
        raise RuntimeError("bug")

    stream = PumpStream("wss://example", boom)
    t = live("early_txs_normal")["txs"][0]
    stream.handle_raw(_ws_message(t))
    assert stream.stats["handler_errors"] == 1


# ----------------------------------------------------------------------------- tracker + features
def test_curve_features_from_real_early_trades():
    tr, mint = normal_launch()
    st = tr.get(mint)
    f = curve_features(st, st.created_ts + 300, tr)
    assert f["complete"] is True and f["n_trades"] == 13 and f["unique_buyers"] == 7
    assert f["same_slot_buyers"] == 2 and f["sniper_buyers"] == 4  # block-0 and first-3-slot buyers
    assert 0 < f["buy_pressure"] < 0.5 and f["creator_sold"] is False
    assert f["agent_trade_share"] == 0.0 and f["mayhem"] is False
    # point in time: nothing after the horizon is used
    f0 = curve_features(st, st.created_ts - 1, tr)
    assert f0["n_trades"] == 0 and f0["price"] is None
    eb = early_buyers(st, st.created_ts + 300)
    assert eb[0]["wallet"] == "46x7gJqyQhsjQuXcws7ESW8h47kGcbQ1FD2RhFjfAWJN" and len(eb) == 7
    bars = tr.candles(mint)
    assert bars and all(b.low <= b.close <= b.high for b in bars)


def test_stream_gap_makes_features_incomplete():
    tr, mint = normal_launch()
    st = tr.get(mint)
    tr.gaps.append((st.created_ts + 10, st.created_ts + 20))
    assert curve_features(st, st.created_ts + 300, tr)["complete"] is False
    assert curve_features(st, st.created_ts + 5, tr)["complete"] is True  # before the gap


def test_untracked_trades_are_ignored_and_watch_works():
    tr = LaunchTracker()
    d = live("early_txs_normal")
    evs = [e for t in d["txs"] for e in parse_transaction(t).events]
    tr.on_events(evs)
    assert tr.stats["untracked_trades"] == 13 and not tr.launches
    tr.watch_mint(d["create"]["mint"])
    tr.on_events(evs)
    st = tr.get(d["create"]["mint"])
    assert st.source == "trade" and st.n_trades == 13 and not st.trades  # bars + price only, no early features
    assert tr.price(d["create"]["mint"]) is not None


def test_mayhem_agent_trades_are_not_organic():
    tr = LaunchTracker()
    tr.stream_up()
    d = live("early_txs_mayhem")
    for t in d["txs"]:
        tr.on_events(parse_transaction(t).events)
    st = tr.get(d["mint"])
    assert st is not None and st.mayhem is True
    f = curve_features(st, st.created_ts + 900, tr)
    assert f["agent_trade_share"] == 1.0 and f["unique_buyers"] == 0
    snap = TokenSnapshot(chain="solana", token_address=d["mint"], observed_at=utcnow(), bonding_curve=True, mayhem=True)
    assert opportunity_index(snap, f).value is None  # never an opportunity reading on an agent-driven curve
    assert "MAYHEM_CURVE" in risk_index(snap, f).blocking


def test_due_horizons_never_backfill_after_long_downtime():
    tr, mint = normal_launch()
    st = tr.get(mint)
    due = tr.due_horizons(now=st.created_ts + 70)
    assert [(h, at) for _, h, at in due] == [("t+1m", st.created_ts + 60)]
    assert tr.due_horizons(now=st.created_ts + 70) == []
    assert tr.due_horizons(now=st.created_ts + 5000) == []  # t+5m / t+15m moments passed long ago: skipped


def test_pumpportal_create_then_stream_create_merge():
    tr = LaunchTracker()
    tr.on_pumpportal({"txType": "create", "mint": "M1", "traderPublicKey": "C1", "pool": "pump",
                      "vSolInBondingCurve": 30.0, "vTokensInBondingCurve": 1.073e9, "is_mayhem_mode": False})
    tr.on_pumpportal({"txType": "create", "mint": "B1", "pool": "bonk"})  # other launchpad: not pump.fun
    assert set(tr.launches) == {"M1"} and tr.get("M1").source == "pumpportal"
    tr.on_events([pump.CreateEvent(name="N", symbol="S", uri="u", mint="M1", bonding_curve="X", user="C1",
                                   creator="C1", timestamp=int(time.time()), slot=5)])
    assert tr.get("M1").source == "stream" and tr.launches_last(3600) == 1


# ----------------------------------------------------------------------------- persistence + labels
def test_persist_stream_is_idempotent_and_features_are_written(db):
    from sqlalchemy import func, select

    from mci.database.models import CandleRow, FeatureSnapshot, PumpLaunch, PumpTradeRow
    from mci.database.session import session_scope
    from mci.research import feature_store as fs

    tr, mint = normal_launch()
    st = tr.get(mint)
    rows = tr.drain(now=st.created_ts + 3600)
    out = fs.persist_stream(rows)
    assert out["launches"] == 1 and out["trades"] == 13 and out["bars"] >= 1
    rows["launches"] = [dict(r) for r in rows["launches"]]
    again = fs.persist_stream({"launches": rows["launches"], "bars": rows["bars"]})
    assert again["launches"] == 0 and again["bars"] == 0
    n = fs.write_feature_snapshots([(st, "t+5m", st.created_ts + 300)], tr)
    assert n == 1 and fs.write_feature_snapshots([(st, "t+5m", st.created_ts + 300)], tr) == 0
    with session_scope() as s:
        assert s.scalar(select(func.count()).select_from(PumpTradeRow)) == 13
        assert s.scalar(select(func.count()).select_from(PumpLaunch)) == 1
        assert s.scalar(select(func.count()).select_from(CandleRow).where(CandleRow.source == "stream")) >= 1
        row = s.scalars(select(FeatureSnapshot)).one()
        assert row.features["n_trades"] == 13 and row.risk["value"] is None or isinstance(row.risk["value"], float)
    # the outcome window has not elapsed in real time for this sample: labels need now >= observed + 240 min
    assert fs.label_due([], now=utcnow() - timedelta(days=3650)) == 0
    labeled = fs.label_due([], now=utcnow() + timedelta(days=1))
    assert labeled == 1
    with session_scope() as s:
        lab = s.scalars(select(FeatureSnapshot)).one().labels
    assert lab["first_passage"] in ("neither", "2x_first", "half_first") and "ret_max_60m" in lab


def test_compute_labels_first_passage_and_gaps():
    from mci.research.feature_store import compute_labels

    t0 = 1_000_000
    bars = [(t0 + 60, 1.5, 0.9, 1.4), (t0 + 120, 2.1, 1.3, 2.0), (t0 + 180, 2.0, 0.4, 0.45)]
    lab = compute_labels(1.0, t0, bars, None, None, [])
    assert lab["first_passage"] == "2x_first" and lab["hit_2x_first"] and not lab["rug_60m"]
    assert lab["ret_max_60m"] == 110.0 and lab["ret_min_60m"] == -60.0
    short = compute_labels(1.0, t0, bars, None, None, [(t0 + 100, t0 + 200)])  # 100 s of 4 h: still usable
    assert short["incomplete"] is False and short["stream_coverage"] > 0.99
    assert compute_labels(1.0, t0, bars, None, None, [(t0 + 100, t0 + 1200)])["incomplete"] is True
    dead = compute_labels(1.0, t0, [], None, None, [])
    assert dead["ret_end_60m"] == 0.0 and dead["dead_60m"] and dead["first_passage"] == "neither"
    assert compute_labels(None, t0, bars, None, None, [])["no_price"] is True
    # conservative: inside the same bar a fall to -50% counts before a +100% spike
    assert compute_labels(1.0, t0, [(t0 + 60, 2.5, 0.4, 1.0)], None, None, [])["first_passage"] == "half_first"


# ----------------------------------------------------------------------------- wallet clusters
def test_clusters_use_only_factual_links():
    buyers = [{"wallet": w, "first_slot": 10 if w in ("A", "B") else 12, "first_ts": 0, "buy_sol": 10**9,
               "net_tokens": 10**13} for w in "ABCDEF"]
    profiles = {
        "A": {"funder": "F1", "first_tx_at": utcnow(), "history_capped": False},
        "B": {"funder": "F1", "first_tx_at": utcnow(), "history_capped": False},
        "C": {"funder": "HUB", "first_tx_at": None, "history_capped": True},
        "D": {"funder": "HUB", "first_tx_at": None, "history_capped": True},
        "E": {"funder": "CREATOR", "first_tx_at": None, "history_capped": False},
        "F": {"funder": "A", "first_tx_at": None, "history_capped": False},
    }
    r = cluster_early_buyers(buyers, profiles, "CREATOR", {"HUB"}, 10**15, creation_slot=10)
    sizes = sorted(c["size"] for c in r["clusters"])
    assert sizes == [3]  # A, B (same funder) + F (funded by A); C/D share only an exchange-like hub
    assert r["creator_linked_wallets"] == 1 and r["block0_wallets"] == 2
    assert r["independent_buyers"] == 2  # C and D
    assert r["coordinated_pct"] == pytest.approx(4.0)  # A, B, F, E: 4 x 1% of supply
    assert r["fresh_wallets"] == 2 and r["coverage"] == 1.0


# ----------------------------------------------------------------------------- indices and rules
def test_indices_are_honest_about_missing_data():
    s = TokenSnapshot(chain="solana", token_address="X", observed_at=utcnow())
    r = risk_index(s)
    assert r.value is None and r.coverage < 0.5 and "NON è una probabilità" in r.note
    o = opportunity_index(s)
    assert o.value is None
    g = good_snapshot()
    r2 = risk_index(g)
    assert r2.value is not None and r2.value < 30 and not r2.blocking


def test_opportunity_never_overrides_blocking_security():
    g = good_snapshot(onchain_findings=[{"code": "PERMANENT_DELEGATE", "severity": "critical",
                                         "message": "delegato permanente", "blocking": True}])
    assert "ONCHAIN_SECURITY" in risk_index(g).blocking
    res = evaluate_filters(g, for_trading=True)
    assert res.excluded and "ONCHAIN_SECURITY" in res.codes
    m = good_snapshot(bonding_curve=True, mayhem=True)
    assert "MAYHEM_CURVE" in evaluate_filters(m).codes
    f = good_snapshot(sell_sim_ok=False, sell_sim_detail="account congelato")
    assert "SELL_SIM_FAILED" in evaluate_filters(f).codes
    assert not evaluate_filters(good_snapshot(sell_sim_ok=None)).excluded  # unverified != failed


def test_shadow_rules_fire_but_do_not_exclude():
    tr, mint = normal_launch()
    st = tr.get(mint)
    f = curve_features(st, st.created_ts + 300, tr)
    f["creator_sold"] = True
    g = good_snapshot()
    r = risk_index(g, f, None, None)
    assert "CREATOR_SOLD" in r.shadow_hits and not evaluate_filters(g).excluded


# ----------------------------------------------------------------------------- own security in the snapshot
def test_apply_security_wins_over_rugcheck_and_reports_disagreement():
    snap = good_snapshot()
    snap.sources["mint_authority"] = "rugcheck"
    sec = analyze_mint("PYUSD", live("mint_pyusd")["result"]["value"])
    diffs = apply_security(snap, sec)
    assert diffs and snap.mint_authority_revoked is False and snap.sources["mint_authority"] == "onchain"
    res = evaluate_filters(snap, for_trading=True)
    assert {"MINT_AUTHORITY_ACTIVE", "FREEZE_AUTHORITY_ACTIVE", "ONCHAIN_SECURITY"} <= set(res.codes)
    # mint/freeze are reported by their own rules, not duplicated in ONCHAIN_SECURITY
    assert all(not x["blocking"] for x in snap.onchain_findings if x["code"].endswith("AUTHORITY_ACTIVE"))


def _rpc_with_accounts(accounts: dict[str, dict]) -> tuple[RpcPool, httpx.AsyncClient]:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        key = body["params"][0]
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": body["id"],
                                         "result": {"value": accounts.get(key)}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return RpcPool(["https://rpc.example"], rps=100, client=client), client


async def test_onchain_service_security_and_curve_state(db):
    from mci.chain.pda import pump_bonding_curve_address

    mint = "7SHruMKRr1DGKNe4FBQDBsYK7pEHwMPQb1chbzW1pump"
    curve = live("curve_account_mayhem")["result"]["value"]
    rpc, client = _rpc_with_accounts({mint: live("mint_new_mayhem")["result"]["value"],
                                      pump_bonding_curve_address(mint): curve})
    svc = OnchainService(rpc, LaunchTracker())
    snap = TokenSnapshot(chain="solana", token_address=mint, observed_at=utcnow(), bonding_curve=True)
    await svc.security(snap)
    assert snap.mint_authority_revoked and snap.freeze_authority_revoked and snap.metadata_mutable is False
    assert snap.onchain_findings == [] and snap.sources["onchain_security"] == "rpc"
    await svc.curve_state(snap)
    assert snap.mayhem is True and snap.bonding_curve is True and 0 < snap.bonding_progress_pct < 5
    assert "MAYHEM_CURVE" in evaluate_filters(snap).codes
    await client.aclose()


# ----------------------------------------------------------------------------- research + promotion
def test_auc_and_research_verdicts():
    y = np.array([0, 0, 1, 1])
    assert auc(np.array([0.1, 0.2, 0.8, 0.9]), y) == 1.0
    assert auc(np.array([1, 1, 1, 1.0]), y) == 0.5
    rng = np.random.default_rng(1)
    rows = []
    for i in range(600):
        good = rng.random() < 0.2
        rug = (not good) and rng.random() < 0.3
        rows.append({"observed_at": i, "features": {"complete": True, "unique_buyers": float(rng.normal(30 if good else 15, 5)),
                                                    "noise": float(rng.normal())},
                     "risk": {"value": float(rng.random() * 100), "shadow_hits": ["CREATOR_SOLD"] if rug else []},
                     "opportunity": {"value": None}, "labels": {"hit_2x_first": good, "rug_60m": rug}})
    rep = evaluate_rows(rows)
    feats = {f["feature"]: f for f in rep["features"]}
    assert feats["unique_buyers"]["hit_2x_first"]["informative"] is True
    assert feats["unique_buyers"]["hit_2x_first"]["auc"] > 0.8
    assert rep["walk_forward"]["hit_2x_first"]["mean_auc"] > 0.8
    assert rep["shadow_rules"]["CREATOR_SOLD"]["rug_rate_if_fires"] == 1.0
    small = evaluate_rows(rows[:40])
    assert small["walk_forward"] is None and "insufficienti" in small["verdict"]
    assert "insufficienti" in evaluate_rows([])["verdict"]


def test_promotion_gate_never_promotes_small_samples(db):
    from mci.database import repo
    from mci.database.session import session_scope
    from mci.research.promotion import experiment_report

    with session_scope() as s:
        repo.set_state(s, "x_safe_started_at", utcnow().isoformat())
        rep = experiment_report(s, "x_safe")
    assert rep["promotable"] is False and rep["status"].startswith("NON PROMUOVIBILE")
    assert any(not c["ok"] for c in rep["checks"])


# ----------------------------------------------------------------------------- execution realism
def test_sell_simulation_is_tri_state():
    assert classify_simulation({"err": None, "logs": []})[0] is True
    assert classify_simulation({"err": {"InstructionError": [3, {"Custom": 17}]},
                                "logs": ["Program log: Error: Account is frozen"]})[0] is False
    assert classify_simulation({"err": "InsufficientFundsForFee", "logs": []})[0] is None
    assert classify_simulation({"err": {"InstructionError": [3, {"Custom": 6024}]}, "logs": []})[0] is None
    assert classify_simulation(None)[0] is None


def test_measured_fees_only_make_simulation_more_conservative():
    assert effective_priority_fee(0.0001, {"priority_p75_sol": 0.00002}) == 0.0001
    assert effective_priority_fee(0.0001, {"priority_p75_sol": 0.0004}) == 0.0004
    assert effective_priority_fee(0.0001, {"priority_p75_sol": 1.0}) == 0.005
    assert effective_priority_fee(0.0001, None) == 0.0001


# ----------------------------------------------------------------------------- x_curve experiment
def _synthetic_launch(tr: LaunchTracker, mint: str, now: float) -> None:
    created = int(now - 240)
    tr.stream_up()
    tr.gaps.clear()
    tr._gap_open = None
    tr.on_events([pump.CreateEvent(name="Organic", symbol="ORG", uri="", mint=mint, bonding_curve="BC", user="DEV",
                                   creator="DEV", timestamp=created, slot=1000, virtual_sol_reserves=30 * 10**9,
                                   virtual_token_reserves=1_073_000_000 * 10**6, real_token_reserves=793_100_000 * 10**6,
                                   token_total_supply=10**15, is_mayhem_mode=False)])
    vsol, vtok, rtok = 30 * 10**9, 1_073_000_000 * 10**6, 793_100_000 * 10**6
    for i in range(40):
        sol = 400_000_000
        tok = vtok - (vsol * vtok) // (vsol + sol)
        vsol, vtok, rtok = vsol + sol, vtok - tok, rtok - tok
        wallet = b58encode(bytes([i + 1]) * 32)
        tr.on_events([pump.TradeEvent(mint=mint, sol_amount=sol, token_amount=tok, is_buy=True, user=wallet,
                                      timestamp=created + 10 + i * 5, virtual_sol_reserves=vsol,
                                      virtual_token_reserves=vtok, real_sol_reserves=vsol - 30 * 10**9,
                                      real_token_reserves=rtok, slot=1010 + i, quote_mint="11111111111111111111111111111111")])


async def test_curve_experiment_opens_a_virtual_position(db):
    from mci.config import get_settings
    from mci.database import repo
    from mci.database.session import session_scope
    from mci.execution.costs import CostModel
    from mci.paper_trading.experiments import CurveExperiment

    mint = "ORGANIC1111111111111111111111111111111pump"
    tr = LaunchTracker()
    _synthetic_launch(tr, mint, time.time())
    st = tr.get(mint)
    f = curve_features(st, time.time(), tr)
    assert f["complete"] and f["unique_buyers"] == 40 and f["buy_pressure"] == 1.0

    rpc, client = _rpc_with_accounts({mint: live("mint_new_mayhem")["result"]["value"]})

    class FX:
        last = type("P", (), {"usd": 150.0, "eur": 140.0})()

    class FakeScanner:
        onchain = OnchainService(rpc, tr)
        fx = FX()
        tokens: dict = {}

    exp = CurveExperiment(get_settings(), FakeScanner(), CostModel())
    await exp.on_scan([])
    assert exp.last_candidates == 1
    with session_scope() as s:
        pos = repo.open_positions(s, "x_curve")
        main = repo.open_positions(s, "paper")
        stats = repo.get_state(s, "x_curve_stats")
    assert len(pos) == 1 and pos[0].strategy == "O" and not main
    assert stats["signals"] == 1
    await exp.monitor_positions()  # priced from the stream, no external call
    await client.aclose()


async def test_scanner_onchain_enrichment_path(db):
    """The scanner's on-chain step on a curve candidate: own security, stream price/candles, indices."""
    from mci.config import get_settings
    from mci.scanner.service import Scanner, TrackedToken

    mint = b58encode(b"\x07" * 32)
    tr = LaunchTracker()
    _synthetic_launch(tr, mint, time.time())
    rpc, client = _rpc_with_accounts({mint: live("mint_new_mayhem")["result"]["value"]})
    svc = OnchainService(rpc, tr)
    sc = Scanner(get_settings(), None, None, None, None, None, onchain=svc)  # type: ignore[arg-type]
    snap = TokenSnapshot(chain="solana", token_address=mint, observed_at=utcnow(), bonding_curve=True,
                         price_native=1e-9, dex_id="pumpfun")
    tt = TrackedToken(mint, snap, utcnow(), "pumpportal")
    sc._sec_budget = 10
    await sc._enrich_onchain(tt, 150.0, wallet_budget=0)
    s = tt.snapshot
    assert s.sources["onchain_security"] == "rpc" and s.mint_authority_revoked is True
    assert s.sources["price"] == "chain_stream" and s.price_native == tr.price(mint)[0]
    assert tt.candle_source.get("1m") == "stream" and len(tt.candles["1m"]) >= 3
    assert s.onchain["curve"]["unique_buyers"] == 40 and s.onchain["risk"]["value"] is not None
    assert s.onchain["opportunity"]["value"] is not None
    # unknown non-pump token: not watched (the stream only carries pump.fun trades)
    other = TrackedToken("DEXTOKEN", TokenSnapshot(chain="solana", token_address="DEXTOKEN", observed_at=utcnow(),
                                                   bonding_curve=False), utcnow(), "dexscreener")
    await sc._enrich_onchain(other, 150.0, wallet_budget=0)
    assert "DEXTOKEN" not in tr.watch
    # malformed address ending in "pump" (invalid base58): logged and skipped, never raised
    bad = TrackedToken("BAD0Ipump", TokenSnapshot(chain="solana", token_address="BAD0Ipump", observed_at=utcnow(),
                                                  bonding_curve=True), utcnow(), "x")
    await sc._enrich_onchain(bad, 150.0, wallet_budget=0)
    await client.aclose()


async def test_stream_reconnects_after_the_server_drops_it():
    """A real local WebSocket server sends real logs, then drops the connection: the stream must report the
    outage (gap) and reconnect by itself."""
    import asyncio

    import websockets

    tx = live("early_txs_normal")["txs"][0]
    connections = []

    async def handler(ws):
        connections.append(1)
        await ws.recv()  # logsSubscribe request
        await ws.send(_ws_message(tx))
        await asyncio.sleep(0.05)
        await ws.close()  # the public node drops us

    states = []
    got = []
    async with websockets.serve(handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        stream = PumpStream(f"ws://127.0.0.1:{port}", got.extend, on_state=states.append)
        task = asyncio.create_task(stream.run())
        for _ in range(100):
            await asyncio.sleep(0.05)
            if len(connections) >= 2:
                break
        stream.stop()
        await asyncio.wait_for(task, timeout=5)
    assert len(connections) >= 2 and stream.stats["reconnects"] >= 1
    assert states[:2] == [True, False] and len(got) >= 1



def test_interval_coverage_merges_overlapping_gaps():
    from mci.onchain.launches import interval_coverage

    assert interval_coverage(0, 100, []) == 1.0
    assert interval_coverage(0, 100, [(10, 20), (15, 30), (90, 200)]) == pytest.approx(0.7)
    assert interval_coverage(0, 100, [(-50, 5)]) == pytest.approx(0.95)
    tr, mint = normal_launch()
    st = tr.get(mint)
    tr.gaps.append((st.created_ts + 100, st.created_ts + 105))  # 5 s of 300 s = 98.3% coverage
    f = curve_features(st, st.created_ts + 300, tr)
    assert f["complete"] is True and f["stream_coverage"] == pytest.approx(0.9833, abs=1e-3)


def test_redundant_connections_are_deduplicated():
    got = []
    stream = PumpStream("wss://example", got.extend, connections=2)
    t = live("early_txs_normal")["txs"][0]
    stream.handle_raw(_ws_message(t))
    stream.handle_raw(_ws_message(t))  # the same transaction from the second connection
    assert len(got) == 1 and stream.stats["duplicates"] == 1
    states = []
    stream.on_state = states.append
    stream._set_up(0, True)
    stream._set_up(1, True)
    stream._set_up(0, False)  # one connection still up: no gap
    stream._set_up(1, False)
    assert states == [True, False]
