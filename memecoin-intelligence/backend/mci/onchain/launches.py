"""Launch tracker: per-token state built from the free pump.fun event stream.

For every launch it keeps the early trades (first 15 minutes, capped), one-minute candles in SOL for the first
hours, the last curve state (price, progress) and the totals. It knows when the stream was down, so features
computed over a window with a gap are flagged incomplete instead of reading "no trades" as "no activity".

Everything here uses on-chain timestamps (block time of the TradeEvent/CreateEvent): features at a horizon only
use trades with ``ts <= created + horizon`` (point in time, no look-ahead).
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from mci.chain.pump import NATIVE_QUOTES, CompleteEvent, CreateEvent, TradeEvent, price_sol
from mci.domain import Candle

PUMP_TOTAL_SUPPLY_RAW = 10**15  # 1,000,000,000 tokens with 6 decimals
PUMP_INITIAL_REAL_TOKENS_RAW = 793_100_000 * 10**6  # sellable on the curve (official default parameters)
HORIZONS = {"t+1m": 60, "t+5m": 300, "t+15m": 900}


@dataclass(slots=True)
class TradeLite:
    ts: int
    slot: int | None
    wallet: str
    is_buy: bool
    sol: int  # lamports
    tokens: int  # raw (6 decimals)
    vsol: int
    vtok: int
    rtok: int
    agent: bool
    sig: str | None
    native: bool = True  # False: the curve is quoted in another token (USDC, stocks...): reserves are not SOL

    @property
    def price(self) -> float | None:
        return price_sol(self.vsol, self.vtok) if self.native else None


@dataclass
class LaunchState:
    mint: str
    created_ts: float
    source: str  # stream | pumpportal | trade (created before we started)
    slot: int | None = None
    signature: str | None = None
    creator: str | None = None
    name: str | None = None
    symbol: str | None = None
    uri: str | None = None
    mayhem: bool | None = None
    token_program: str | None = None
    quote_mint: str | None = None
    total_supply: int = PUMP_TOTAL_SUPPLY_RAW
    initial_real_tokens: int | None = None
    launch_price: float | None = None
    trades: list[TradeLite] = field(default_factory=list)
    early_truncated: bool = False
    n_trades: int = 0
    n_buys: int = 0
    buy_sol: int = 0
    sell_sol: int = 0
    wallets: set[str] = field(default_factory=set)
    last: TradeLite | None = None
    peak_price: float | None = None
    bars: dict[int, list[float]] = field(default_factory=dict)  # minute -> [o, h, l, c, vol_lamports, n]
    complete_ts: float | None = None
    persisted_trades: int = 0
    persisted_bars_upto: int = 0
    horizons_done: set[str] = field(default_factory=set)
    dirty: bool = True
    last_activity: float = field(default_factory=time.time)

    @property
    def price(self) -> float | None:
        if self.last is None:
            return None
        return self.last.price

    def stats(self) -> dict[str, Any]:
        return {
            "trades": self.n_trades, "buys": self.n_buys, "buy_sol": self.buy_sol / 1e9, "sell_sol": self.sell_sol / 1e9,
            "wallets": len(self.wallets), "last_price": self.price, "peak_price": self.peak_price,
            "launch_price": self.launch_price, "last_trade_ts": self.last.ts if self.last else None,
            "progress_pct": progress_pct(self), "complete": self.complete_ts is not None,
        }


def progress_pct(st: LaunchState) -> float | None:
    init = st.initial_real_tokens or PUMP_INITIAL_REAL_TOKENS_RAW
    if st.last is None or not st.last.rtok:
        return None
    return max(0.0, min(100.0, (init - st.last.rtok) / init * 100))


def interval_coverage(start: float, end: float, gaps: list[tuple[float, float]]) -> float:
    """Share of [start, end] NOT covered by the (possibly overlapping) gap intervals."""
    if end <= start:
        return 1.0 if not any(a <= start <= b for a, b in gaps) else 0.0
    clipped = sorted((max(a, start), min(b, end)) for a, b in gaps if b > start and a < end)
    missing, cur_a, cur_b = 0.0, None, None
    for a, b in clipped:
        if cur_b is None or a > cur_b:
            if cur_b is not None:
                missing += cur_b - cur_a
            cur_a, cur_b = a, b
        else:
            cur_b = max(cur_b, b)
    if cur_b is not None:
        missing += cur_b - cur_a
    return max(0.0, 1.0 - missing / (end - start))


def _dt(ts: float) -> datetime:
    return datetime.fromtimestamp(ts, tz=timezone.utc)


class LaunchTracker:
    def __init__(self, early_window_s: int = 900, early_max: int = 400, keep_hours: float = 5.0,
                 max_launches: int = 40_000, bar_minutes: int = 300):
        self.early_window_s = early_window_s
        self.early_max = early_max
        self.keep_s = keep_hours * 3600
        self.max_launches = max_launches
        self.bar_minutes = bar_minutes
        self.launches: dict[str, LaunchState] = {}
        self.watch: set[str] = set()
        self._created: deque = deque()  # creation times (epoch) of the last 24 h, for the launch counter
        self._new_launches: list[LaunchState] = []
        self._upgraded: list[LaunchState] = []  # PumpPortal launches later confirmed by the chain CreateEvent
        self.gaps: deque = deque(maxlen=500)  # (start, end) epoch intervals without stream data
        self._gap_open: float | None = time.time()  # nothing received yet = gap
        self.stats: dict[str, int] = {"creates": 0, "trades": 0, "untracked_trades": 0, "completes": 0,
                                      "pumpportal_creates": 0, "evicted": 0}
        self.journal: Any = None  # optional mci.onchain.journal.Journal (lifecycle diary of every launch)

    # ------------------------------------------------------------------ stream health
    def stream_up(self) -> None:
        if self._gap_open is not None:
            self.gaps.append((self._gap_open, time.time()))
            self._gap_open = None

    def stream_down(self) -> None:
        if self._gap_open is None:
            self._gap_open = time.time()

    def covered(self, start: float, end: float) -> bool:
        """True when the stream was connected for the whole [start, end] interval."""
        return self.coverage(start, end) >= 1.0

    def coverage(self, start: float, end: float, now: float | None = None) -> float:
        """Share of [start, end] during which at least one stream connection was up (1.0 = no data missing)."""
        gaps = list(self.gaps)
        if self._gap_open is not None:
            gaps.append((self._gap_open, now or time.time()))
        return interval_coverage(start, end, gaps)

    # ------------------------------------------------------------------ events
    def on_events(self, events: list[Any]) -> None:
        for ev in events:
            if isinstance(ev, TradeEvent):
                self._trade(ev)
            elif isinstance(ev, CreateEvent):
                self._create_from_event(ev)
            elif isinstance(ev, CompleteEvent):
                st = self.launches.get(ev.mint)
                self.stats["completes"] += 1
                if st:
                    st.complete_ts = float(ev.timestamp or time.time())
                    st.dirty = True
                    if self.journal is not None:
                        self.journal.on_complete(ev.mint, st.complete_ts, st.price)

    def _register(self, st: LaunchState) -> None:
        self.launches[st.mint] = st
        self._new_launches.append(st)
        self._created.append(st.created_ts)

    def _create_from_event(self, ev: CreateEvent) -> None:
        self.stats["creates"] += 1
        st = self.launches.get(ev.mint)
        if st is not None and st.source == "stream":
            return
        new = LaunchState(
            mint=ev.mint, created_ts=float(ev.timestamp or time.time()), source="stream", slot=ev.slot,
            signature=ev.signature, creator=ev.creator or ev.user, name=ev.name[:128], symbol=ev.symbol[:64],
            uri=ev.uri[:300], mayhem=ev.is_mayhem_mode, token_program=ev.token_program, quote_mint=ev.quote_mint,
            total_supply=ev.token_total_supply or PUMP_TOTAL_SUPPLY_RAW, initial_real_tokens=ev.real_token_reserves,
            launch_price=(price_sol(ev.virtual_sol_reserves or 0, ev.virtual_token_reserves or 0)
                          if not ev.quote_mint or ev.quote_mint in NATIVE_QUOTES else None),
        )
        if st is not None:  # seen first from PumpPortal: keep the trades already collected
            new.trades, new.n_trades, new.n_buys = st.trades, st.n_trades, st.n_buys
            new.buy_sol, new.sell_sol, new.wallets, new.last = st.buy_sol, st.sell_sol, st.wallets, st.last
            new.bars, new.peak_price, new.persisted_trades = st.bars, st.peak_price, st.persisted_trades
            new.horizons_done, new.early_truncated = st.horizons_done, st.early_truncated
            new.persisted_bars_upto = st.persisted_bars_upto
            self.launches[ev.mint] = new
            self._upgraded.append(new)  # its database row must get the on-chain time, slot and creator
            if self.journal is not None:
                self.journal.on_create(new)
            return
        self._register(new)
        if self.journal is not None:
            self.journal.on_create(new)

    def on_pumpportal(self, ev: dict[str, Any]) -> None:
        """PumpPortal create events: launch counter and creator when the chain stream is down or slower."""
        if ev.get("txType") != "create" or not ev.get("mint") or (ev.get("pool") not in (None, "pump")):
            return
        self.stats["pumpportal_creates"] += 1
        if ev["mint"] in self.launches:
            return
        vsol, vtok = ev.get("vSolInBondingCurve"), ev.get("vTokensInBondingCurve")
        self._register(LaunchState(
            mint=ev["mint"], created_ts=time.time(), source="pumpportal", signature=ev.get("signature"),
            creator=ev.get("traderPublicKey"), name=(ev.get("name") or "")[:128] or None,
            symbol=(ev.get("symbol") or "")[:64] or None, uri=(ev.get("uri") or "")[:300] or None,
            mayhem=ev.get("is_mayhem_mode"),
            launch_price=(float(vsol) / float(vtok)) if vsol and vtok else None,
        ))

    def watch_mint(self, mint: str) -> None:
        """Aggregate trades (candles, price) of a tracked token created before the stream saw its launch."""
        self.watch.add(mint)

    def _trade(self, ev: TradeEvent) -> None:
        st = self.launches.get(ev.mint)
        if st is None:
            if ev.mint not in self.watch:
                self.stats["untracked_trades"] += 1
                return
            st = LaunchState(mint=ev.mint, created_ts=0.0, source="trade")
            self.launches[ev.mint] = st
        self.stats["trades"] += 1
        t = TradeLite(int(ev.timestamp), ev.slot, ev.user, ev.is_buy, ev.sol_amount, ev.token_amount,
                      ev.virtual_sol_reserves, ev.virtual_token_reserves, ev.real_token_reserves, ev.agent,
                      ev.signature, not ev.quote_mint or ev.quote_mint in NATIVE_QUOTES)
        st.n_trades += 1
        if t.is_buy:
            st.n_buys += 1
            st.buy_sol += t.sol
        else:
            st.sell_sol += t.sol
        if len(st.wallets) < 5000:
            st.wallets.add(t.wallet)
        if st.source != "trade" and t.ts <= st.created_ts + self.early_window_s:
            if len(st.trades) < self.early_max:
                st.trades.append(t)
            else:
                st.early_truncated = True
        st.last = t
        if self.journal is not None and st.source == "stream":
            self.journal.on_trade(ev.mint, t)
        p = t.price
        if p:
            st.peak_price = max(st.peak_price or p, p)
            m = t.ts // 60 * 60
            bar = st.bars.get(m)
            if bar is None:
                st.bars[m] = [p, p, p, p, float(t.sol), 1]
                if len(st.bars) > self.bar_minutes:
                    del st.bars[min(st.bars)]
            else:
                bar[1] = max(bar[1], p)
                bar[2] = min(bar[2], p)
                bar[3] = p
                bar[4] += t.sol
                bar[5] += 1
        st.dirty = True
        st.last_activity = time.time()

    # ------------------------------------------------------------------ queries
    def get(self, mint: str) -> LaunchState | None:
        return self.launches.get(mint)

    def price(self, mint: str) -> tuple[float, int] | None:
        st = self.launches.get(mint)
        if st is None or st.last is None or st.price is None:
            return None
        return st.price, st.last.ts

    def candles(self, mint: str, sol_usd: float | None = None, complete_only: bool = False) -> list[Candle]:
        """One-minute candles in SOL per token; volume in USD when the SOL price is known (as GeckoTerminal)."""
        st = self.launches.get(mint)
        if st is None:
            return []
        now_m = int(time.time()) // 60 * 60
        out = []
        for m in sorted(st.bars):
            if complete_only and m >= now_m:
                continue
            o, h, low, c, vol, _n = st.bars[m]
            v = vol / 1e9 * (sol_usd or 0.0) if sol_usd else vol / 1e9
            out.append(Candle(m, o, h, low, c, v))
        return out

    def launches_last(self, seconds: float) -> int:
        cutoff = time.time() - seconds
        while self._created and self._created[0] < time.time() - 86400:
            self._created.popleft()
        return sum(1 for t in self._created if t >= cutoff)

    def due_horizons(self, now: float | None = None, lag_s: float = 10.0) -> list[tuple[LaunchState, str, float]]:
        """(launch, horizon, at_ts) whose point-in-time snapshot can now be taken."""
        now = now or time.time()
        out = []
        for st in self.launches.values():
            if st.source == "trade":
                continue
            for name, secs in HORIZONS.items():
                if name in st.horizons_done:
                    continue
                at = st.created_ts + secs
                if now >= at + lag_s:
                    st.horizons_done.add(name)
                    if now - at > 600:  # restarted much later: the moment has passed, never back-fill it
                        continue
                    out.append((st, name, at))
        return out

    # ------------------------------------------------------------------ persistence
    def drain(self, now: float | None = None) -> dict[str, list[dict[str, Any]]]:
        """Rows to persist since the last call: new launches, launch stats, early trades, closed 1m bars."""
        now = now or time.time()
        def row(st: LaunchState) -> dict[str, Any]:
            return {"mint": st.mint, "created_at": _dt(st.created_ts), "slot": st.slot, "signature": st.signature,
                    "creator": st.creator, "name": st.name, "symbol": st.symbol, "uri": st.uri, "mayhem": st.mayhem,
                    "token_program": st.token_program, "quote_mint": st.quote_mint, "source": st.source}

        # always the CURRENT state (a PumpPortal launch may already have been confirmed by the chain stream)
        new = [row(self.launches.get(st.mint) or st) for st in self._new_launches]
        new_mints = {r["mint"] for r in new}
        updates = [row(st) for st in self._upgraded if st.mint not in new_mints]
        self._new_launches, self._upgraded = [], []
        stats, trades, bars = [], [], []
        cur_minute = int(now) // 60 * 60
        for st in self.launches.values():
            if not st.dirty:
                continue
            st.dirty = False
            if st.source != "trade":
                stats.append({"mint": st.mint, "stats": st.stats(),
                              "complete_at": _dt(st.complete_ts) if st.complete_ts else None})
                for t in st.trades[st.persisted_trades:]:
                    trades.append({"mint": st.mint, "ts": _dt(t.ts), "slot": t.slot, "signature": t.sig,
                                   "wallet": t.wallet, "is_buy": t.is_buy, "sol_lamports": t.sol,
                                   "token_amount": t.tokens, "v_sol": t.vsol, "v_tokens": t.vtok,
                                   "mayhem": t.agent or bool(st.mayhem)})
                st.persisted_trades = len(st.trades)
            for m in sorted(st.bars):
                if st.persisted_bars_upto < m < cur_minute:
                    o, h, low, c, vol, n = st.bars[m]
                    bars.append({"mint": st.mint, "ts": m, "open": o, "high": h, "low": low, "close": c,
                                 "volume": vol / 1e9, "n": n})
                    st.persisted_bars_upto = m
            if any(m >= cur_minute for m in st.bars):
                st.dirty = True  # current minute still open: persist it next time
        events = []
        if self.journal is not None:
            self.journal.tick(now)
            events = self.journal.drain()
        return {"launches": new, "launch_updates": updates, "stats": stats, "trades": trades, "bars": bars,
                "events": events}

    def evict(self, now: float | None = None) -> int:
        """Forget launches older than ``keep_hours`` with no recent activity (they stay in the database)."""
        now = now or time.time()
        drop = [m for m, st in self.launches.items()
                if m not in self.watch and now - st.last_activity > 1800
                and (st.source == "trade" or now - st.created_ts > self.keep_s)]
        if len(self.launches) - len(drop) > self.max_launches:
            rest = sorted((st.last_activity, m) for m, st in self.launches.items() if m not in drop and m not in self.watch)
            drop += [m for _, m in rest[: len(self.launches) - len(drop) - self.max_launches]]
        for m in drop:
            self.launches.pop(m, None)
        self.stats["evicted"] += len(drop)
        return len(drop)

    def health(self) -> dict[str, Any]:
        return {
            **self.stats,
            "in_memory": len(self.launches),
            "watched": len(self.watch),
            "launches_1h": self.launches_last(3600),
            "launches_24h": self.launches_last(86400),
            "stream_gap_open": self._gap_open is not None,
            "gaps_24h": sum(1 for a, b in self.gaps if b > time.time() - 86400),
        }
