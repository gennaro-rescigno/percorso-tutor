"""Token lifecycle journal: a factual diary of what happens to every pump.fun launch.

Fed trade by trade by the LaunchTracker (same free chain stream, no extra calls). Each event is a FACT observed
on-chain at a precise block time, with the price at that moment, so the research module can measure what tends to
happen after it (event study). Nothing here is a signal or a score.

Events (kind -> value):
  create          launch seen (value: creator's first buy in SOL, filled when it arrives)
  dev_buy         creator buys (SOL)               dev_sell     creator sells (SOL; detail: share of holding)
  block0          buyers other than the creator in the creation slot (count; detail: SOL, supply share)
  whale_buy       single buy >= WHALE_SOL          whale_sell   single sell >= WHALE_SOL
  wash_atomic     same wallet buys and sells inside one transaction (WT1 rule of "Meme Coin Factories")
  reserve         real SOL reserve crosses a level upward for the first time (value: level)
  drawdown        price falls >= 50% / >= 80% from the peak after the curve held >= 5 SOL (value: 50 or 80)
  volume_spike    >= 20 buys from >= 15 wallets in 60 s, after the first 2 minutes (value: buys)
  complete        curve completed: migration to PumpSwap (value: seconds from launch)
  dead            no trade for 30 minutes (value: last price / peak)
  copy            the normalized name was already used by an earlier launch we saw (value: earlier uses)
"""

from __future__ import annotations

import re
import time
from collections import Counter, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

V0_SOL = 30.0
WHALE_SOL = 2.0
RESERVE_LEVELS = (5, 10, 20, 40, 60, 80)
DRAWDOWN_LEVELS = (50, 80)
SPIKE_BUYS, SPIKE_WALLETS, SPIKE_AFTER_S, SPIKE_COOLDOWN_S = 20, 15, 120, 600
DEAD_AFTER_S = 1800
MAX_STATES = 60_000
NAME_MEMORY = 200_000


def real_sol(vsol_lamports: int) -> float:
    """Real SOL in a classic pump.fun curve = virtual SOL - 30 SOL (initial virtual reserve)."""
    return max(0.0, vsol_lamports / 1e9 - V0_SOL)


def norm_name(name: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


@dataclass(slots=True)
class _J:
    created_ts: float
    creator: str | None
    mayhem: bool
    creation_slot: int | None
    dev_tokens: int = 0
    dev_bought: bool = False
    block0_done: bool = False
    block0_wallets: set = field(default_factory=set)
    block0_sol: int = 0
    block0_tokens: int = 0
    peak: float = 0.0
    peak_rs: float = 0.0
    reserves: set = field(default_factory=set)
    drawdowns: set = field(default_factory=set)
    buys_60s: deque = field(default_factory=deque)  # (ts, wallet)
    last_spike: float = 0.0
    wash: bool = False
    sig_sides: dict = field(default_factory=dict)  # signature -> {wallet: set(sides)} (last few only)
    last_trade_ts: float = 0.0
    last_price: float = 0.0
    dead: bool = False
    complete: bool = False


class Journal:
    def __init__(self, supply_raw: int = 10**15):
        self.supply_raw = supply_raw
        self.states: dict[str, _J] = {}
        self.names: Counter = Counter()
        self._name_order: deque = deque()
        self.events: list[dict[str, Any]] = []
        self.stats: Counter = Counter()

    # ------------------------------------------------------------------ helpers
    def _emit(self, mint: str, ts: float, kind: str, value: float | None, price: float | None,
              detail: dict[str, Any] | None = None, age_s: float | None = None) -> None:
        self.stats[kind] += 1
        self.events.append({"token_address": mint, "ts": datetime.fromtimestamp(ts, tz=timezone.utc), "kind": kind,
                            "value": None if value is None else round(float(value), 6), "price": price,
                            "age_s": None if age_s is None else round(age_s, 1), "detail": detail or {},
                            "source": "stream"})

    def seed_names(self, names: list[str | None]) -> None:
        """Names of launches already in the database (so 'copy' works right after a restart)."""
        for n in names:
            self._remember(norm_name(n))

    def _remember(self, nn: str) -> None:
        if not nn:
            return
        self.names[nn] += 1
        self._name_order.append(nn)
        while len(self._name_order) > NAME_MEMORY:
            old = self._name_order.popleft()
            self.names[old] -= 1
            if self.names[old] <= 0:
                del self.names[old]

    # ------------------------------------------------------------------ inputs (called by the tracker)
    def on_create(self, st: Any) -> None:
        if st.mint in self.states:
            return
        if len(self.states) >= MAX_STATES:
            self._drop_oldest()
        self.states[st.mint] = _J(st.created_ts, st.creator, bool(st.mayhem), st.slot)
        nn = norm_name(st.name)
        detail = {"name": (st.name or "")[:40], "symbol": (st.symbol or "")[:16], "mayhem": bool(st.mayhem),
                  "uri_kind": uri_kind(st.uri)}
        self._emit(st.mint, st.created_ts, "create", None, st.launch_price, detail, 0.0)
        prior = self.names.get(nn, 0) if nn else 0
        if prior:
            self._emit(st.mint, st.created_ts, "copy", prior, st.launch_price, {"name": (st.name or "")[:40]}, 0.0)
        self._remember(nn)

    def on_trade(self, mint: str, t: Any) -> None:
        j = self.states.get(mint)
        if j is None:
            return
        p = t.price or 0.0
        ts = float(t.ts)
        age = ts - j.created_ts
        sol = t.sol / 1e9
        rs = real_sol(t.vsol)
        j.last_trade_ts, j.last_price = ts, p
        if j.dead:  # trading resumed after a long silence: allow a new 'dead' later
            j.dead = False
        # --- creator
        if j.creator and t.wallet == j.creator:
            if t.is_buy:
                j.dev_tokens += t.tokens
                self._emit(mint, ts, "dev_buy", sol, p, {"first": not j.dev_bought}, age)
                j.dev_bought = True
            else:
                held_before = j.dev_tokens
                j.dev_tokens = max(0, j.dev_tokens - t.tokens)
                share = (t.tokens / held_before) if held_before > 0 else None
                self._emit(mint, ts, "dev_sell", sol, p,
                           {"share_of_holding": None if share is None else round(min(share, 1.0), 3),
                            "sold_all": j.dev_tokens == 0 and held_before > 0}, age)
        # --- block 0 (creation slot) buyers other than the creator
        if not j.block0_done:
            if j.creation_slot is not None and t.slot == j.creation_slot:
                if t.is_buy and t.wallet != j.creator:
                    j.block0_wallets.add(t.wallet)
                    j.block0_sol += t.sol
                    j.block0_tokens += t.tokens
            elif j.creation_slot is not None and t.slot is not None and t.slot > j.creation_slot:
                self._close_block0(mint, j, ts)
        # --- whales and atomic wash trades
        if sol >= WHALE_SOL and not (j.creator and t.wallet == j.creator):
            self._emit(mint, ts, "whale_buy" if t.is_buy else "whale_sell", sol, p, {"wallet": t.wallet[:8]}, age)
        if t.sig and not j.wash:
            sides = j.sig_sides.setdefault(t.sig, {}).setdefault(t.wallet, set())
            sides.add(t.is_buy)
            if len(sides) == 2:
                j.wash = True
                self._emit(mint, ts, "wash_atomic", 1, p, {"wallet": t.wallet[:8]}, age)
            if len(j.sig_sides) > 64:
                j.sig_sides.pop(next(iter(j.sig_sides)))
        if j.mayhem:
            return  # the agent moves mayhem curves: reserves and drawdowns are not organic, keep only facts above
        # --- reserve levels and drawdowns
        for lvl in RESERVE_LEVELS:
            if rs >= lvl and lvl not in j.reserves:
                j.reserves.add(lvl)
                self._emit(mint, ts, "reserve", lvl, p, {"multiple": round(((V0_SOL + rs) / V0_SOL) ** 2, 2)}, age)
        if p > j.peak:
            j.peak, j.peak_rs = p, max(j.peak_rs, rs)
        if j.peak_rs >= 5 and j.peak > 0:
            dd = (1 - p / j.peak) * 100
            for lvl in DRAWDOWN_LEVELS:
                if dd >= lvl and lvl not in j.drawdowns:
                    j.drawdowns.add(lvl)
                    self._emit(mint, ts, "drawdown", lvl, p, {"peak_reserve_sol": round(j.peak_rs, 2)}, age)
        # --- volume spike
        if t.is_buy:
            j.buys_60s.append((ts, t.wallet))
        while j.buys_60s and j.buys_60s[0][0] < ts - 60:
            j.buys_60s.popleft()
        if (age >= SPIKE_AFTER_S and ts - j.last_spike >= SPIKE_COOLDOWN_S and len(j.buys_60s) >= SPIKE_BUYS
                and len({w for _, w in j.buys_60s}) >= SPIKE_WALLETS):
            j.last_spike = ts
            self._emit(mint, ts, "volume_spike", len(j.buys_60s), p,
                       {"wallets": len({w for _, w in j.buys_60s}), "reserve_sol": round(rs, 2)}, age)

    def on_complete(self, mint: str, ts: float, price: float | None) -> None:
        j = self.states.get(mint)
        if j is None or j.complete:
            return
        j.complete = True
        self._emit(mint, ts, "complete", ts - j.created_ts, price, {"mayhem": j.mayhem}, ts - j.created_ts)

    def _close_block0(self, mint: str, j: _J, ts: float) -> None:
        j.block0_done = True
        self._emit(mint, j.created_ts, "block0", len(j.block0_wallets), None,
                   {"sol": round(j.block0_sol / 1e9, 4),
                    "supply_pct": round(j.block0_tokens / self.supply_raw * 100, 2)}, 0.0)
        j.block0_wallets = set()

    # ------------------------------------------------------------------ periodic
    def tick(self, now: float | None = None) -> None:
        """Time-based facts (no trade arrives to trigger them): block 0 closed, 30 minutes of silence."""
        now = now or time.time()
        for mint, j in list(self.states.items()):
            if not j.block0_done and now - j.created_ts > 30:
                self._close_block0(mint, j, now)
            if not j.dead and not j.complete and j.last_trade_ts and now - j.last_trade_ts >= DEAD_AFTER_S:
                j.dead = True
                ratio = (j.last_price / j.peak) if j.peak else None
                self._emit(mint, j.last_trade_ts + DEAD_AFTER_S, "dead", ratio, j.last_price,
                           {"peak_reserve_sol": round(j.peak_rs, 2)}, j.last_trade_ts + DEAD_AFTER_S - j.created_ts)
            if now - j.created_ts > 6 * 3600 and (j.dead or j.complete):
                del self.states[mint]

    def _drop_oldest(self) -> None:
        for mint in sorted(self.states, key=lambda m: self.states[m].created_ts)[: MAX_STATES // 10]:
            del self.states[mint]

    def drain(self) -> list[dict[str, Any]]:
        out, self.events = self.events, []
        return out

    def health(self) -> dict[str, Any]:
        return {"tracked": len(self.states), "events": dict(self.stats)}


def uri_kind(uri: str | None) -> str:
    u = (uri or "").lower()
    if not u:
        return "none"
    if "ipfs" in u:
        return "ipfs"
    if "arweave" in u or "irys" in u:
        return "arweave"
    return "http" if u.startswith("http") else "other"
