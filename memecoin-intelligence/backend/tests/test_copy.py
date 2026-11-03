"""Wallet ledger and copy experiment: realized results per wallet, leader choice, delayed copies."""

from __future__ import annotations

from mci.chain import pump
from mci.onchain.launches import LaunchTracker
from mci.onchain.wallet_ledger import WalletLedger, day_of
from mci.paper_trading.copy_sim import (
    CopySim,
    build_sims,
    buy_tokens,
    eligible,
    refresh,
    select_control,
    select_leaders,
    sell_sol,
)

from test_journal import MINT, V0, T0, Curve, w


def setup(*listeners):
    tr = LaunchTracker()
    tr.listeners = list(listeners)
    return tr


def test_ledger_realized_marked_transfer_and_creator():
    led = WalletLedger()
    tr = setup(led)
    c = Curve(tr)
    t0, s0 = c.created, c.slot
    c.buy("DEV", 1.0, t0, s0)                     # creator: never counted
    c.buy(w(1), 1.0, t0 + 30, s0 + 10)            # the smart wallet buys early-ish
    for i in range(20):
        c.buy(w(20 + i), 0.5, t0 + 60 + i * 5, s0 + 20 + i)
    held = led.pos[(w(1), MINT)].held
    c.sell(w(1), held, t0 + 200, s0 + 60)          # sells everything at a profit after 170 s
    c.buy(w(2), 0.5, t0 + 210, s0 + 61)           # buys late and never sells
    c.sell(w(3), 10**9, t0 + 220, s0 + 62)        # sells tokens it never bought here: transferred in
    rows = led.closed_recent
    win = next(r for r in rows if r["wallet"] == w(1))
    assert win["pnl"] > 0 and win["marked"] is None and win["hold_s"] == 170 and win["entry_age_s"] == 30
    assert not any(r["wallet"] == "DEV" for r in rows)
    led.tick(now=t0 + 220 + 1801)                  # the token dies: open positions marked at the last price
    late = next(r for r in led.closed_recent if r["wallet"] == w(2))
    assert late["marked"] == "dead" and late["pnl"] < 0
    st = led.summary(now=t0 + 3000)
    assert st[w(1)]["n"] == 1 and st[w(1)]["win"] == 1 and st[w(3)]["transfer_sells"] == 1
    assert led.health()["marked_dead"] >= 1 and MINT not in led.mints


def test_ledger_migration_marks_open_positions_with_haircut():
    led = WalletLedger()
    tr = setup(led)
    c = Curve(tr)
    c.buy(w(5), 1.0, c.created + 40, c.slot + 5)
    for i in range(10):
        c.buy(w(30 + i), 2.0, c.created + 50 + i, c.slot + 10 + i)
    tr.on_events([pump.CompleteEvent(user="X", mint=MINT, bonding_curve="BC", timestamp=c.created + 100)])
    r = next(r for r in led.closed_recent if r["wallet"] == w(5))
    assert r["marked"] == "migrated"


def _st(n=10, win=7, pnl=2.0, ret=0.3, quick=1, early=1, transfer=0, mayhem=0, sd=0.2):
    return {"n": n, "win": win, "pnl": pnl, "cost": 1.0, "sum_ret": ret * n, "sum_ret2": (sd * sd + ret * ret) * n,
            "quick": quick, "early": early, "transfer_sells": transfer, "marked": 0, "mayhem": mayhem}


def test_leader_selection_is_strict_and_control_ignores_profit():
    summary = {"good": _st(), "lucky_one_trade": _st(n=2, win=2), "sniper": _st(early=8), "flipper": _st(quick=9),
               "insider": _st(transfer=1), "loser": _st(win=2, pnl=-1.0, ret=-0.2), "small": _st(pnl=0.5),
               "better": _st(ret=0.6, sd=0.1)}
    lead = [w_ for w_, _ in select_leaders(summary)]
    assert lead == ["better", "good"]
    assert not eligible(summary["sniper"]) and not eligible(summary["insider"]) and eligible(summary["loser"])
    ctrl = {w_ for w_, _ in select_control(summary, seed=1)}
    assert "loser" in ctrl and "sniper" not in ctrl and ctrl == {"good", "loser", "small", "better"}


def test_copy_buys_late_and_sells_when_the_leader_sells():
    sim = CopySim("x_copy_3s", 3, "leaders")
    sim.set_wallets([(w(1), _st())], 0)
    tr = setup(sim)
    c = Curve(tr)
    t0, s0 = c.created, c.slot
    c.buy(w(1), 1.0, t0 + 30, s0 + 10)              # leader buys: copy due at t0 + 33
    state_before = (c.vsol, c.vtok)
    c.buy(w(9), 2.0, t0 + 40, s0 + 11)              # next trade after the due time: copy filled BEFORE it
    cp = sim.copies[MINT]
    assert cp.entry_ts == t0 + 33 and abs(cp.tokens - buy_tokens(*state_before, 0.1)) < 1
    for i in range(10):
        c.buy(w(40 + i), 0.5, t0 + 50 + i, s0 + 20 + i)
    c.sell(w(1), 10**12, t0 + 100, s0 + 40)         # leader sells: copy exits 3 s later
    c.buy(w(60), 0.1, t0 + 103, s0 + 41)            # same second as the due time: filled AFTER this trade
    out = sim.drain()
    assert len(out) == 1 and out[0]["exit_reason"] == "il wallet copiato vende"
    assert out[0]["proceeds_sol"] == sell_sol(c.vsol, c.vtok, cp.tokens) - 0.0005
    assert out[0]["ret_pct"] > 0 and out[0]["leader"] == w(1)


def test_copy_fills_on_tick_time_stop_completion_and_shutdown():
    sim = CopySim("x_copy_10s", 10, "leaders")
    sim.set_wallets([(w(1), _st()), (w(2), _st())], 0)
    tr = setup(sim)
    c = Curve(tr)
    c.buy(w(1), 1.0, c.created + 30, c.slot + 10)
    sim.tick(now=c.created + 45)                    # no trade since: filled at the unchanged curve state
    assert sim.copies[MINT].entry_ts == c.created + 40
    sim.tick(now=c.created + 40 + 3600)             # 60 minutes later
    assert sim.drain()[0]["exit_reason"] == "60 minuti trascorsi"
    # a second leader, same token later: one copy at a time; then the curve completes
    c.buy(w(2), 1.0, c.created + 4000, c.slot + 30)
    c.buy(w(8), 0.5, c.created + 4020, c.slot + 31)
    tr.on_events([pump.CompleteEvent(user="X", mint=MINT, bonding_curve="BC", timestamp=c.created + 4030)])
    assert sim.drain()[0]["exit_reason"].startswith("diploma")
    c.buy(w(3), 0.5, c.created + 4040, c.slot + 32)
    sim.close_all()
    assert sim.drain() == []                        # nothing open: nothing invented


def test_wallet_days_and_copy_trades_are_persisted_and_reported(db):
    from mci.research import copy_store

    led = WalletLedger()
    led.days["W"][day_of(1_800_000_000)] = [3, 2, 0.5, 1.0, 0.6, 0.2, 0, 0, 0, 0, 0]
    led.dirty.add(("W", day_of(1_800_000_000)))
    assert copy_store.save_wallet_days(led.drain_dirty()) == 1
    assert copy_store.save_wallet_days([{"wallet": "W", "day": day_of(1_800_000_000), **dict.fromkeys(
        ("n", "win", "pnl", "cost", "sum_ret", "sum_ret2", "quick", "early", "transfer_sells", "marked", "mayhem"), 4)}]) == 1
    rows = copy_store.load_wallet_days(days=2, now=1_800_000_000)
    assert len(rows) == 1 and rows[0]["n"] == 4  # upsert, not a duplicate
    sim = CopySim("x_copy_3s", 3, "leaders")
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    sim.closed = [{"variant": "x_copy_3s", "mint": "M", "leader": "L", "signal_at": now, "entry_at": now, "exit_at": now,
                   "entry_price": 1e-7, "cost_sol": 0.1005, "proceeds_sol": 0.12, "ret_pct": 19.4,
                   "exit_reason": "x", "leader_stats": {}}]
    assert copy_store.save_copy_trades(sim.drain()) == 1
    rep = copy_store.copy_report()
    assert rep["variants"]["x_copy_3s"]["verdict"].startswith("dati insufficienti")
    info = refresh(build_sims(), {"a": _st()}, now=1_800_000_000)
    assert info["leaders"][0]["wallet"] == "a" and info["eligible"] == 1


def test_copy_never_acts_before_the_trade_could_have_been_seen():
    sim = CopySim("x_copy_3s", 3, "leaders")
    sim.set_wallets([(w(1), _st())], 0)
    tr = setup(sim)
    c = Curve(tr)
    sim.clock = lambda: c.created + 30 + 4.0  # the stream delivered the leader's buy 4 s after its block time
    c.buy(w(1), 1.0, c.created + 30, c.slot + 10)
    assert sim.copies[MINT].entry_due == c.created + 30 + 4.5  # arrival + landing time, not the planned 3 s
    sim.clock = lambda: c.created + 30 + 1.0  # fast arrival: the planned delay applies
    sim.copies.clear()
    sim.seen.clear()
    c.buy(w(1), 0.2, c.created + 31, c.slot + 11)
    assert sim.copies[MINT].entry_due == c.created + 34
    # a constant drift of the on-chain clock (here 30 s) is not a delay: only the excess above it counts
    sim.lag_floor = lambda: 30.0
    sim.clock = lambda: c.created + 32 + 31.0
    sim.copies.clear()
    sim.seen.clear()
    c.buy(w(1), 0.2, c.created + 32, c.slot + 12)
    assert sim.copies[MINT].entry_due == c.created + 32 + 3
