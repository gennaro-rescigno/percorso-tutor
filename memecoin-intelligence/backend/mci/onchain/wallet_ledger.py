"""Wallet ledger: the realized result of every wallet trading pump.fun curves, measured from the free stream.

Why: the money in memecoins goes to a small minority (top 1% of buyers take 56% of the gains, Bitquery 2026).
Some of them are insiders or bots we cannot follow, but some buy minutes before the crowd (for example before
an influencer call) and hold long enough to be followed a few seconds later. This ledger finds out who they
are, using only on-chain facts, so the copy experiment can test following them OUT OF SAMPLE.

Accounting (SOL, with the 1.25% pump.fun fee on each side):
  * a position opens with a wallet's first buy of a token and closes when its net tokens return to (almost) zero;
  * a position still open when the token dies (30 minutes without trades) is marked at the last price: losers kept
    in the wallet are losses, not invisible (no survivorship bias); a position open when the curve completes is
    marked at the last curve price minus 30% (the pool exit we cannot see);
  * tokens sold beyond what the wallet bought on the curve came from a transfer (insiders, team wallets): those
    sales are counted apart and flag the wallet; they never count as trading profit;
  * the creator's own trades are excluded (the creator is never a model to copy);
  * curves quoted in another token are ignored (amounts are not SOL).
Daily buckets per wallet are kept for 4 days in memory and persisted for wallets with at least 2 closed positions.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

FEE = 0.0125
DUST_SOL = 0.01  # positions below this cost are ignored (dust / spam bots)
CLOSE_FRACTION = 0.01  # a position is closed when under 1% of the bought tokens remain
DEAD_AFTER_S = 1800
MIGRATION_HAIRCUT = 0.30
KEEP_DAYS = 4
QUICK_HOLD_S = 60
EARLY_ENTRY_S = 20
FIELDS = ("n", "win", "pnl", "cost", "sum_ret", "sum_ret2", "quick", "early", "transfer_sells", "marked", "mayhem")


@dataclass(slots=True)
class _Pos:
    opened_ts: float
    entry_age: float
    bought: int = 0
    held: int = 0
    cost: float = 0.0
    proceeds: float = 0.0
    n_buys: int = 0
    n_sells: int = 0


@dataclass(slots=True)
class _Mint:
    created_ts: float
    creator: str | None
    mayhem: bool
    last_ts: float = 0.0
    last_price: float = 0.0
    open: set = field(default_factory=set)


def day_of(ts: float) -> int:
    return int(ts // 86400)


class WalletLedger:
    def __init__(self) -> None:
        self.mints: dict[str, _Mint] = {}
        self.pos: dict[tuple[str, str], _Pos] = {}
        self.days: dict[str, dict[int, list[float]]] = defaultdict(dict)  # wallet -> day -> FIELDS values
        self.dirty: set[tuple[str, int]] = set()
        self.closed_recent: list[dict[str, Any]] = []  # for tests / debugging (bounded)
        self.stats = {"positions_closed": 0, "marked_dead": 0, "marked_migrated": 0, "transfer_sells": 0}
        self._last_prune = 0.0

    # ------------------------------------------------------------------ tracker callbacks
    def on_create(self, st: Any) -> None:
        if st.mint not in self.mints:
            self.mints[st.mint] = _Mint(st.created_ts, st.creator, bool(st.mayhem))

    def on_trade(self, mint: str, t: Any) -> None:
        m = self.mints.get(mint)
        if m is None or not getattr(t, "native", True):
            return
        ts = float(t.ts)
        m.last_ts = ts
        p = t.price
        if p:
            m.last_price = p
        if m.creator and t.wallet == m.creator:
            return
        key = (t.wallet, mint)
        sol = t.sol / 1e9
        pos = self.pos.get(key)
        if t.is_buy:
            if pos is None:
                pos = self.pos[key] = _Pos(ts, ts - m.created_ts)
                m.open.add(t.wallet)
            pos.bought += t.tokens
            pos.held += t.tokens
            pos.cost += sol * (1 + FEE)
            pos.n_buys += 1
            return
        if pos is None:  # selling tokens never bought on the curve: received by transfer
            self._transfer_sell(t.wallet, ts)
            return
        sold = min(t.tokens, pos.held)
        if t.tokens > pos.held and t.tokens - pos.held > pos.bought * CLOSE_FRACTION:
            self._transfer_sell(t.wallet, ts)
        share = sold / t.tokens if t.tokens else 0.0
        pos.proceeds += sol * share * (1 - FEE)
        pos.held -= sold
        pos.n_sells += 1
        if pos.held <= pos.bought * CLOSE_FRACTION:
            self._close(t.wallet, mint, ts, marked=None)

    def on_complete(self, mint: str) -> None:
        m = self.mints.get(mint)
        if m is None:
            return
        for w in list(m.open):
            pos = self.pos.get((w, mint))
            if pos is not None:
                pos.proceeds += pos.held / 1e6 * m.last_price * (1 - MIGRATION_HAIRCUT) * (1 - FEE)
                self._close(w, mint, m.last_ts or time.time(), marked="migrated")

    def tick(self, now: float | None = None) -> None:
        """Dead tokens: mark the positions still open at the last price, then forget the token."""
        now = now or time.time()
        for mint, m in list(self.mints.items()):
            if m.last_ts and now - m.last_ts >= DEAD_AFTER_S:
                for w in list(m.open):
                    pos = self.pos.get((w, mint))
                    if pos is not None:
                        pos.proceeds += pos.held / 1e6 * m.last_price * (1 - FEE)
                        self._close(w, mint, m.last_ts + DEAD_AFTER_S, marked="dead")
                del self.mints[mint]
            elif not m.last_ts and now - m.created_ts > 6 * 3600:
                del self.mints[mint]
        cutoff = day_of(now) - KEEP_DAYS + 1
        if now - self._last_prune >= 600:  # prune old buckets every 10 minutes
            self._last_prune = now
            for w in list(self.days):
                b = self.days[w]
                for d in [d for d in b if d < cutoff]:
                    del b[d]
                if not b:
                    del self.days[w]

    # ------------------------------------------------------------------ accounting
    def _bucket(self, wallet: str, ts: float) -> list[float]:
        d = day_of(ts)
        b = self.days[wallet].get(d)
        if b is None:
            b = self.days[wallet][d] = [0.0] * len(FIELDS)
        self.dirty.add((wallet, d))
        return b

    def _transfer_sell(self, wallet: str, ts: float) -> None:
        self.stats["transfer_sells"] += 1
        self._bucket(wallet, ts)[FIELDS.index("transfer_sells")] += 1

    def _close(self, wallet: str, mint: str, ts: float, marked: str | None) -> None:
        pos = self.pos.pop((wallet, mint), None)
        m = self.mints.get(mint)
        if m is not None:
            m.open.discard(wallet)
        if pos is None or pos.cost < DUST_SOL:
            return
        pnl = pos.proceeds - pos.cost
        ret = pnl / pos.cost
        b = self._bucket(wallet, ts)
        vals = {"n": 1, "win": 1 if pnl > 0 else 0, "pnl": pnl, "cost": pos.cost, "sum_ret": ret, "sum_ret2": ret * ret,
                "quick": 1 if ts - pos.opened_ts < QUICK_HOLD_S else 0, "early": 1 if pos.entry_age < EARLY_ENTRY_S else 0,
                "marked": 1 if marked else 0, "mayhem": 1 if (m and m.mayhem) else 0}
        for k, v in vals.items():
            b[FIELDS.index(k)] += v
        self.stats["positions_closed"] += 1
        if marked == "dead":
            self.stats["marked_dead"] += 1
        elif marked == "migrated":
            self.stats["marked_migrated"] += 1
        if len(self.closed_recent) < 2000:
            self.closed_recent.append({"wallet": wallet, "mint": mint, "pnl": pnl, "ret": ret, "marked": marked,
                                       "hold_s": ts - pos.opened_ts, "entry_age_s": pos.entry_age})

    # ------------------------------------------------------------------ queries
    def window(self, wallet: str, days: list[int]) -> dict[str, float]:
        out = dict.fromkeys(FIELDS, 0.0)
        for d in days:
            b = self.days.get(wallet, {}).get(d)
            if b:
                for i, k in enumerate(FIELDS):
                    out[k] += b[i]
        return out

    def summary(self, now: float | None = None, lookback_days: int = 3) -> dict[str, dict[str, float]]:
        """Per-wallet totals over the last ``lookback_days`` FULL or partial days up to now (past data only)."""
        now = now or time.time()
        today = day_of(now)
        days = list(range(today - lookback_days + 1, today + 1))
        return {w: self.window(w, days) for w in self.days}

    def drain_dirty(self, min_closed: int = 2) -> list[dict[str, Any]]:
        rows = []
        for w, d in self.dirty:
            b = self.days.get(w, {}).get(d)
            if b and b[0] >= min_closed:
                rows.append({"wallet": w, "day": d, **{k: b[i] for i, k in enumerate(FIELDS)}})
        self.dirty = set()
        return rows

    def load(self, rows: list[dict[str, Any]]) -> None:
        for r in rows:
            self.days[r["wallet"]][int(r["day"])] = [float(r.get(k) or 0) for k in FIELDS]

    def health(self) -> dict[str, Any]:
        return {**self.stats, "wallets": len(self.days), "open_positions": len(self.pos), "mints": len(self.mints)}
