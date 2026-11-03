"""Copy experiment: follow the best wallets of the PAST, a few seconds late, on FUTURE trades only.

PRE-REGISTERED on 2026-11-03 (before any result):
  * leaders are chosen every hour from the wallet ledger's last 3 days (data before the choice only):
    >= 8 positions, >= 50% winners, >= +1 SOL and >= +10% average per position, at most half of the positions
    held under 60 s or entered in the first 20 s (so a copy a few seconds late is feasible), no sale of
    transferred tokens (insiders), at most 600 positions (not an arbitrage bot), at most half on mayhem curves;
    ranked by the t-statistic of the average return, top 50;
  * control group: 50 random wallets with the same activity filters but NO profit filter: if the leaders do not
    beat the control, the selection is luck;
  * a copy buys 0.1 SOL when a followed wallet makes its first buy of a token, `delay` seconds later (3 s and
    10 s variants), at the curve state at that moment (pump.fun constant product, 1.25% fee, 0.0005 SOL
    priority fee per transaction); it sells when the wallet sells (same delay), after 60 minutes at the latest,
    when the token dies (30 minutes without trades) or, if the curve completes, at the last curve price minus 30%;
  * one copy per token and variant at a time; curves quoted in another token are never copied;
  * verdict "promettente" only with >= 200 copies over >= 7 days, a 95% bootstrap interval of the average above
    zero AND above the control group. Nothing is ever traded for real or promoted without the user.
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

FEE = 0.0125
STAKE_SOL = 0.1
PRIO_SOL = 0.0005
MAX_HOLD_S = 3600
DEAD_AFTER_S = 1800
MIGRATION_HAIRCUT = 0.30
TOP_N = 50
LOOKBACK_DAYS = 3


def eligible(st: dict[str, float]) -> bool:
    """Activity filters shared by leaders and control (copyable, not insiders, not arbitrage bots)."""
    n = st.get("n", 0)
    return (n >= 8 and n <= 600 and st.get("quick", 0) / n <= 0.5 and st.get("early", 0) / n <= 0.5
            and st.get("transfer_sells", 0) == 0 and st.get("mayhem", 0) / n <= 0.5)


def t_stat(st: dict[str, float]) -> float:
    n = st["n"]
    mean = st["sum_ret"] / n
    var = max(st["sum_ret2"] / n - mean * mean, 1e-9) * n / max(n - 1, 1)
    return mean / math.sqrt(var / n)


def select_leaders(summary: dict[str, dict[str, float]], top_n: int = TOP_N) -> list[tuple[str, dict]]:
    cand = []
    for w, st in summary.items():
        if not eligible(st):
            continue
        n = st["n"]
        if st["win"] / n >= 0.5 and st["pnl"] >= 1.0 and st["sum_ret"] / n >= 0.10:
            cand.append((t_stat(st), w, st))
    cand.sort(reverse=True)
    return [(w, st) for _, w, st in cand[:top_n]]


def select_control(summary: dict[str, dict[str, float]], seed: int, n: int = TOP_N) -> list[tuple[str, dict]]:
    pool = sorted(w for w, st in summary.items() if eligible(st))
    rnd = random.Random(seed)
    pick = rnd.sample(pool, min(n, len(pool)))
    return [(w, summary[w]) for w in pick]


def buy_tokens(vsol: int, vtok: int, sol: float) -> float:
    """Raw tokens received for ``sol`` SOL on a constant-product curve (fee taken on the SOL side)."""
    lam = sol * (1 - FEE) * 1e9
    return vtok - (vsol * vtok) / (vsol + lam)


def sell_sol(vsol: int, vtok: int, tokens_raw: float) -> float:
    out = vsol - (vsol * vtok) / (vtok + tokens_raw)
    return max(out, 0.0) / 1e9 * (1 - FEE)


@dataclass
class Copy:
    mint: str
    leader: str
    signal_ts: float
    entry_due: float
    entry_ts: float | None = None
    tokens: float = 0.0
    entry_price: float | None = None
    exit_due: float | None = None
    exit_reason: str | None = None


class CopySim:
    def __init__(self, variant: str, delay_s: float, group: str):
        self.variant, self.delay, self.group = variant, float(delay_s), group
        self.wallets: dict[str, dict] = {}
        self.chosen_at: float | None = None
        self.state: dict[str, tuple[int, int, float]] = {}  # mint -> (vsol, vtok, ts) after the last trade
        self.native: dict[str, bool] = {}
        self.copies: dict[str, Copy] = {}
        self.seen: set[tuple[str, str]] = set()
        self.closed: list[dict[str, Any]] = []
        self.stats = {"signals": 0, "filled": 0, "closed": 0, "skipped_busy": 0}

    def set_wallets(self, chosen: list[tuple[str, dict]], at: float) -> None:
        self.wallets = {w: st for w, st in chosen}
        self.chosen_at = at

    # ------------------------------------------------------------------ stream callbacks
    def on_create(self, st: Any) -> None:
        return None

    def on_trade(self, mint: str, t: Any) -> None:
        ts = float(t.ts)
        native = getattr(t, "native", True)
        prev = self.state.get(mint)
        c = self.copies.get(mint)
        if c is not None:
            self._settle(c, ts, prev, after=(t.vsol, t.vtok))
        self.state[mint] = (t.vsol, t.vtok, ts)
        if not native:
            return
        c = self.copies.get(mint)
        if t.wallet in self.wallets:
            if t.is_buy and (t.wallet, mint) not in self.seen:
                self.seen.add((t.wallet, mint))
                self.stats["signals"] += 1
                if c is None:
                    self.copies[mint] = Copy(mint, t.wallet, ts, ts + self.delay)
                else:
                    self.stats["skipped_busy"] += 1
            elif not t.is_buy and c is not None and c.leader == t.wallet and c.entry_ts is not None \
                    and c.exit_due is None:
                c.exit_due, c.exit_reason = ts + self.delay, "il wallet copiato vende"

    def _settle(self, c: Copy, ts: float, prev: tuple | None, after: tuple[int, int]) -> None:
        """Fill a due entry or exit at the curve state at the due time (before this trade, or after it if same second)."""
        if c.entry_ts is None and ts >= c.entry_due:
            vs, vt = (prev[0], prev[1]) if prev and ts > c.entry_due else after
            self._fill(c, c.entry_due, vs, vt)
        if c.entry_ts is not None and c.exit_due is not None and ts >= c.exit_due:
            vs, vt = (prev[0], prev[1]) if prev and ts > c.exit_due else after
            self._exit(c, c.exit_due, sell_sol(vs, vt, c.tokens), c.exit_reason or "uscita")

    def _fill(self, c: Copy, at: float, vsol: int, vtok: int) -> None:
        c.tokens = buy_tokens(vsol, vtok, STAKE_SOL)
        if c.tokens <= 0:
            self.copies.pop(c.mint, None)
            return
        c.entry_ts = at
        c.entry_price = STAKE_SOL / (c.tokens / 1e6)
        self.stats["filled"] += 1

    def on_complete(self, mint: str) -> None:
        c = self.copies.get(mint)
        st = self.state.get(mint)
        if c is None or st is None:
            return
        if c.entry_ts is None:
            self.copies.pop(mint, None)
            return
        self._exit(c, st[2], sell_sol(st[0], st[1], c.tokens) * (1 - MIGRATION_HAIRCUT), "diploma: venduto nel pool (-30%)")

    def tick(self, now: float | None = None) -> None:
        now = now or time.time()
        for mint, c in list(self.copies.items()):
            st = self.state.get(mint)
            if st is None:
                continue
            last_ts = st[2]
            if c.entry_ts is None and now >= c.entry_due + 1 and last_ts <= c.entry_due:
                self._fill(c, c.entry_due, st[0], st[1])  # nobody traded since the signal: same curve state
                c = self.copies.get(mint)
                if c is None:
                    continue
            if c.entry_ts is None:
                continue
            if c.exit_due is not None and now >= c.exit_due + 1 and last_ts <= c.exit_due:
                self._exit(c, c.exit_due, sell_sol(st[0], st[1], c.tokens), c.exit_reason or "uscita")
            elif now - c.entry_ts >= MAX_HOLD_S:
                self._exit(c, now, sell_sol(st[0], st[1], c.tokens), "60 minuti trascorsi")
            elif now - last_ts >= DEAD_AFTER_S:
                self._exit(c, now, sell_sol(st[0], st[1], c.tokens), "token morto (30 min senza scambi)")
        if len(self.state) > 60_000:  # forget the oldest idle curves
            for m, _ in sorted(self.state.items(), key=lambda kv: kv[1][2])[:10_000]:
                if m not in self.copies:
                    self.state.pop(m, None)
        if len(self.seen) > 200_000:
            self.seen = set()

    def _exit(self, c: Copy, at: float, proceeds: float, reason: str) -> None:
        self.copies.pop(c.mint, None)
        cost = STAKE_SOL + PRIO_SOL
        net = proceeds - PRIO_SOL
        self.stats["closed"] += 1
        self.closed.append({
            "variant": self.variant, "mint": c.mint, "leader": c.leader,
            "signal_at": _dt(c.signal_ts), "entry_at": _dt(c.entry_ts or at), "exit_at": _dt(at),
            "entry_price": c.entry_price, "cost_sol": cost, "proceeds_sol": net,
            "ret_pct": round((net / cost - 1) * 100, 3), "exit_reason": reason,
            "leader_stats": {k: round(v, 4) for k, v in (self.wallets.get(c.leader) or {}).items()},
        })

    def close_all(self, reason: str = "riavvio del bot: chiusa al prezzo corrente") -> None:
        """At shutdown: open copies are closed at the current curve state, never silently dropped."""
        now = time.time()
        for mint, c in list(self.copies.items()):
            st = self.state.get(mint)
            if c.entry_ts is None or st is None:
                self.copies.pop(mint, None)
                continue
            self._exit(c, now, sell_sol(st[0], st[1], c.tokens), reason)

    def drain(self) -> list[dict[str, Any]]:
        out, self.closed = self.closed, []
        return out

    def health(self) -> dict[str, Any]:
        return {"variant": self.variant, "delay_s": self.delay, "group": self.group, "wallets": len(self.wallets),
                "chosen_at": _dt(self.chosen_at).isoformat() if self.chosen_at else None,
                "open": sum(1 for c in self.copies.values() if c.entry_ts is not None),
                "pending": sum(1 for c in self.copies.values() if c.entry_ts is None), **self.stats}


def _dt(ts: float) -> datetime:
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def build_sims() -> list[CopySim]:
    return [CopySim("x_copy_3s", 3, "leaders"), CopySim("x_copy_10s", 10, "leaders"),
            CopySim("x_copy_ctrl", 3, "control")]


def refresh(sims: list[CopySim], summary: dict[str, dict[str, float]], now: float | None = None) -> dict[str, Any]:
    now = now or time.time()
    leaders = select_leaders(summary)
    control = select_control(summary, seed=int(now // 21600))
    for s in sims:
        s.set_wallets(leaders if s.group == "leaders" else control, now)
    return {"chosen_at": _dt(now).isoformat(), "eligible": sum(1 for st in summary.values() if eligible(st)),
            "wallets_measured": len(summary),
            "leaders": [{"wallet": w, "n": st["n"], "win_rate": round(st["win"] / st["n"], 3),
                         "pnl_sol": round(st["pnl"], 3), "avg_ret_pct": round(st["sum_ret"] / st["n"] * 100, 1),
                         "t": round(t_stat(st), 2)} for w, st in leaders],
            "control_size": len(control)}
