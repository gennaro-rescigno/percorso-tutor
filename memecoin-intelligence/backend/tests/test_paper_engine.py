"""End-to-end paper trading flow with fake data sources (no network)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from conftest import good_snapshot
from sqlalchemy import select

from mci.collectors.fx import SolPrice
from mci.config import get_settings
from mci.database import repo
from mci.database.models import Order, Position, SignalRow
from mci.database.session import session_scope
from mci.domain import Candle, utcnow
from mci.execution.costs import CostModel
from mci.execution.paper import PaperExecutor
from mci.paper_trading.engine import TradingEngine
from mci.risk_management.exits import ExitPolicy
from mci.risk_management.profiles import MODERATE
from mci.scanner.service import Scanner, TrackedToken
from mci.scoring.scorer import score_token
from mci.strategies.library import build_strategy
from mci.utils.http import SourceUnavailable


class FakeFx:
    def __init__(self):
        self.last = SolPrice(eur=140.0, usd=150.0, source="test", fetched_at=__import__("time").time())

    async def get(self):
        return self.last


class FakeDex:
    def __init__(self):
        self.price_native = None
        self.down = False

    async def pairs_for_tokens(self, chain, addrs):
        if self.down:
            raise SourceUnavailable("dexscreener", "down")
        if self.price_native is None:
            return []
        return [{"chainId": "solana", "dexId": "pumpswap", "pairAddress": "GoodPool111",
                 "baseToken": {"address": "GoodMint111", "symbol": "GOOD"}, "quoteToken": {"symbol": "SOL"},
                 "priceNative": str(self.price_native), "liquidity": {"usd": 120000, "quote": 400}}]


class Notes:
    def __init__(self):
        self.items: list[tuple[str, dict]] = []

    async def notify(self, kind, payload):
        self.items.append((kind, payload))

    def kinds(self):
        return [k for k, _ in self.items]


def _candles(n=80, start_price=0.001 / 150):
    t0 = int((utcnow() - timedelta(minutes=n)).timestamp()) // 60 * 60
    out, p = [], start_price
    for i in range(n):
        o = p
        p *= 1.002
        out.append(Candle(t0 + 60 * i, o, p * 1.001, o * 0.999, p, 1000 + 50 * i))
    return out


def _engine(notes, executor=None):
    s = get_settings()
    dex = FakeDex()
    sc = Scanner(s, dex, None, None, None, FakeFx())  # type: ignore[arg-type]
    ex = executor or PaperExecutor(CostModel(), jupiter=None, failure_rate=0.0, landing_slippage_pct=0.0)
    policy = ExitPolicy(stop_mode="fixed", fixed_stop_pct=0.2, take_profits=((0.5, 0.5),), trailing_activation_pct=0.4,
                        trailing_pct=0.2, volume_decay_exit=False, no_progress_minutes=0)
    eng = TradingEngine(s, sc, ex, MODERATE, CostModel(), notes, policy, [build_strategy("A")])
    return eng, sc, dex


def _tracked(sc):
    snap = good_snapshot()
    tt = TrackedToken(snap.token_address, snap, utcnow(), "test")
    tt.candles["1m"] = _candles()
    snap.price_native = tt.candles["1m"][-1].close
    tt.score = score_token(snap, tt.candles["1m"])
    tt.trade_score = score_token(snap, tt.candles["1m"], for_trading=True)
    sc.tokens[snap.token_address] = tt
    return tt


@pytest.mark.asyncio
async def test_signal_to_buy_to_stop_loss_and_persistence(db):
    notes = Notes()
    eng, sc, dex = _engine(notes)
    tt = _tracked(sc)
    assert not tt.trade_score.excluded, tt.trade_score.exclusion_reasons
    await eng.on_scan([tt])
    assert "signal" in notes.kinds() and "buy" in notes.kinds(), notes.items
    with session_scope() as s:
        pos = repo.open_positions(s, "paper")
        assert len(pos) == 1
        p = pos[0]
        sig = s.scalar(select(SignalRow))
        assert sig.status == "executed" and sig.snapshot  # data available at signal time is stored
        orders = s.scalars(select(Order)).all()
        assert [o.side for o in orders] == ["buy"] and orders[0].fills
        entry, cost = p.entry_price, p.cost_sol
    assert eng.port.cash == pytest.approx(2.0 - cost)

    # restart: a new engine instance restores the same portfolio from the database
    eng2, sc2, dex2 = _engine(notes)
    assert eng2.port.cash == pytest.approx(eng.port.cash)
    sc2.tokens = sc.tokens

    # price collapses below the stop -> stop loss
    dex2.price_native = entry * 0.7
    await eng2.monitor_positions()
    with session_scope() as s:
        p = s.get(Position, p.id)
        assert p.status == "closed" and p.realized_pnl_sol < 0
        assert "stop" in p.exit_reason.lower()
    assert "close" in notes.kinds() and "stop_hit" in notes.kinds()
    close_payload = dict(notes.items)["close"]
    assert close_payload["net_pnl_sol"] == pytest.approx(close_payload["proceeds_sol"] - cost)


@pytest.mark.asyncio
async def test_take_profit_partial_then_trailing(db):
    notes = Notes()
    eng, sc, dex = _engine(notes)
    tt = _tracked(sc)
    await eng.on_scan([tt])
    with session_scope() as s:
        p = repo.open_positions(s, "paper")[0]
        entry, pid = p.entry_price, p.id
    dex.price_native = entry * 1.6
    await eng.monitor_positions()
    assert "partial" in notes.kinds()
    with session_scope() as s:
        p = s.get(Position, pid)
        assert p.status == "open" and p.qty == pytest.approx(p.qty_initial * 0.5)
    dex.price_native = entry * 2.0  # new high -> trailing level updated on next tick
    await eng.monitor_positions()
    await eng.monitor_positions()
    dex.price_native = entry * 1.5  # below 2.0 * 0.8 = 1.6 -> trailing stop
    await eng.monitor_positions()
    with session_scope() as s:
        p = s.get(Position, pid)
        assert p.status == "closed" and p.realized_pnl_sol > 0


@pytest.mark.asyncio
async def test_paused_and_kill_switch_block_new_entries(db):
    notes = Notes()
    eng, sc, _ = _engine(notes)
    tt = _tracked(sc)
    with session_scope() as s:
        repo.set_state(s, "control_paused", True)
    await eng.on_scan([tt])
    assert "buy" not in notes.kinds()
    with session_scope() as s:
        repo.set_state(s, "control_paused", False)
        repo.set_state(s, "control_kill", "test")
    await eng.on_scan([tt])
    assert "buy" not in notes.kinds()
    with session_scope() as s:
        sig = s.scalar(select(SignalRow).order_by(SignalRow.id.desc()))
        assert sig.status == "rejected" and "kill switch" in sig.rejection_reason


@pytest.mark.asyncio
async def test_failed_order_is_recorded_not_filled(db):
    notes = Notes()
    ex = PaperExecutor(CostModel(), jupiter=None, failure_rate=1.0)
    eng, sc, _ = _engine(notes, executor=ex)
    tt = _tracked(sc)
    await eng.on_scan([tt])
    with session_scope() as s:
        assert not repo.open_positions(s, "paper")
        o = s.scalar(select(Order))
        assert o.status == "failed" and not o.fills
        assert s.scalar(select(SignalRow)).status == "failed"
    assert eng.port.cash < 2.0  # network fee of the failed transaction is charged


@pytest.mark.asyncio
async def test_api_outage_does_not_crash_monitor(db):
    notes = Notes()
    eng, sc, dex = _engine(notes)
    tt = _tracked(sc)
    await eng.on_scan([tt])
    dex.down = True
    await eng.monitor_positions()  # falls back to last known price, no exception
    with session_scope() as s:
        assert len(repo.open_positions(s, "paper")) == 1


def test_signal_outcome_tracking(db):
    notes = Notes()
    eng, sc, _ = _engine(notes)
    tt = _tracked(sc)
    from mci.domain import Signal

    sig = Signal(strategy="A", token_address=tt.address, symbol="GOOD", created_at=utcnow() - timedelta(hours=2),
                 reference_price=tt.snapshot.price_native / 1.1, stop_price=0, score=80, reasons=[], risks=[])
    with session_scope() as s:
        repo.record_signal(s, sig, "paper", tt.snapshot, None)
    assert eng.track_signal_outcomes() == 1
    with session_scope() as s:
        r = s.scalar(select(SignalRow))
        assert r.price_15m and r.price_1h and r.price_4h is None
        assert r.max_gain_24h == pytest.approx(0.1, rel=1e-6)
