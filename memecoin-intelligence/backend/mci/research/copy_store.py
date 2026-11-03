"""Persistence and report of the wallet ledger and of the copy experiment (see paper_trading/copy_sim.py)."""

from __future__ import annotations

import time
from collections import defaultdict
from datetime import timedelta
from typing import Any

import numpy as np
from sqlalchemy import delete, insert, select

from mci.database.models import CopyTrade, WalletDay
from mci.database.session import session_scope
from mci.domain import utcnow
from mci.onchain.wallet_ledger import FIELDS, day_of

MIN_TRADES, MIN_DAYS, BOOT = 200, 7, 2000


def save_wallet_days(rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    by_day: dict[int, list[dict]] = defaultdict(list)
    for r in rows:
        by_day[int(r["day"])].append(r)
    with session_scope() as s:
        for d, rs in by_day.items():
            wallets = [r["wallet"] for r in rs]
            for i in range(0, len(wallets), 500):
                s.execute(delete(WalletDay).where(WalletDay.day == d, WalletDay.wallet.in_(wallets[i:i + 500])))
        s.execute(insert(WalletDay), [{"wallet": r["wallet"], "day": int(r["day"]), **{k: float(r[k]) for k in FIELDS}}
                                      for r in rows])
    return len(rows)


def load_wallet_days(days: int = 4, now: float | None = None) -> list[dict[str, Any]]:
    since = day_of(now or time.time()) - days + 1
    with session_scope() as s:
        rows = s.scalars(select(WalletDay).where(WalletDay.day >= since)).all()
        return [{"wallet": r.wallet, "day": r.day, **{k: getattr(r, k) for k in FIELDS}} for r in rows]


def save_copy_trades(rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    with session_scope() as s:
        s.execute(insert(CopyTrade), rows)
    return len(rows)


def retention(now=None) -> dict[str, int]:
    now = now or utcnow()
    with session_scope() as s:
        a = s.execute(delete(WalletDay).where(WalletDay.day < day_of(now.timestamp()) - 10)).rowcount
        b = s.execute(delete(CopyTrade).where(CopyTrade.exit_at < now - timedelta(days=90))).rowcount
    return {"wallet_days": a, "copy_trades": b}


def _boot_ci(x: np.ndarray, rng: np.random.Generator) -> tuple[float, float]:
    if len(x) < 30:
        return float("nan"), float("nan")
    idx = rng.integers(0, len(x), size=(BOOT, len(x))) if len(x) <= 5000 else None
    means = x[idx].mean(axis=1) if idx is not None else rng.normal(x.mean(), x.std(ddof=1) / np.sqrt(len(x)), BOOT)
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(lo), float(hi)


def copy_report(days: int = 30, seed: int = 5) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    since = utcnow() - timedelta(days=days)
    with session_scope() as s:
        rows = s.execute(select(CopyTrade.variant, CopyTrade.ret_pct, CopyTrade.exit_at, CopyTrade.exit_reason,
                                CopyTrade.proceeds_sol, CopyTrade.cost_sol)
                         .where(CopyTrade.exit_at >= since)).all()
    by: dict[str, list] = defaultdict(list)
    for v, r, at, reason, pr, co in rows:
        by[v].append((r, at, reason, pr - co))
    out = {}
    ctrl = np.array([r for r, *_ in by.get("x_copy_ctrl", [])], float)
    for v, lst in sorted(by.items()):
        x = np.array([r for r, *_ in lst], float)
        lo, hi = _boot_ci(x, rng)
        days_cov = len({at.date() for _, at, _, _ in lst})
        reasons: dict[str, int] = defaultdict(int)
        for _, _, reason, _ in lst:
            reasons[reason or "?"] += 1
        d = {"n": len(x), "mean_pct": round(float(x.mean()), 2), "ci_pct": [round(lo, 2), round(hi, 2)],
             "median_pct": round(float(np.median(x)), 2), "win_rate": round(float((x > 0).mean()), 3),
             "pnl_sol": round(float(sum(p for *_, p in lst)), 4), "days": days_cov, "exit_reasons": dict(reasons)}
        if v != "x_copy_ctrl" and len(ctrl) >= 30 and len(x) >= 30:
            diffs = [x[rng.integers(0, len(x), len(x))].mean() - ctrl[rng.integers(0, len(ctrl), len(ctrl))].mean()
                     for _ in range(500)]
            d["vs_control_ci_pct"] = [round(float(np.percentile(diffs, 2.5)), 2), round(float(np.percentile(diffs, 97.5)), 2)]
        ok = (len(x) >= MIN_TRADES and days_cov >= MIN_DAYS and lo > 0
              and d.get("vs_control_ci_pct", [0])[0] > 0)
        if v == "x_copy_ctrl":
            d["verdict"] = "gruppo di controllo (wallet a caso con gli stessi filtri di attività)"
        elif len(x) < MIN_TRADES or days_cov < MIN_DAYS:
            d["verdict"] = f"dati insufficienti ({len(x)}/{MIN_TRADES} copie, {days_cov}/{MIN_DAYS} giorni)"
        elif ok:
            d["verdict"] = "promettente: batte zero e il controllo (serve la tua approvazione per andare oltre)"
        else:
            d["verdict"] = "non funziona" if x.mean() <= 0 else "non dimostrata"
        out[v] = d
    return {"generated_at": utcnow().isoformat(), "variants": out, "min_trades": MIN_TRADES, "min_days": MIN_DAYS}
