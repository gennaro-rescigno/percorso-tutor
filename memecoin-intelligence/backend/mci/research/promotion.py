"""Promotion gate for experiments. It only REPORTS: nothing is ever promoted automatically.

An experiment is "promuovibile" (= worth asking the owner) only when ALL of these hold on its own
out-of-sample trades (opened after the experiment started, with frozen parameters):

1. at least 50 closed trades;
2. at least 14 days of running time;
3. the 95% confidence interval of the mean return per trade is entirely above zero;
4. the mean return beats the Laboratorio baseline over the SAME period, with a bootstrap p-value < 0.05.

Even then the decision stays with the owner (explicit approval), as required.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Any

import numpy as np

from mci.database import repo
from mci.domain import to_utc, utcnow

MIN_TRADES = 50
MIN_DAYS = 14


def _stats(rets: list[float]) -> dict[str, Any]:
    n = len(rets)
    if n == 0:
        return {"trades": 0}
    a = np.array(rets)
    mean = float(a.mean())
    sd = float(a.std(ddof=1)) if n > 1 else None
    half = 1.96 * sd / math.sqrt(n) if sd is not None else None
    return {"trades": n, "win_rate": round(float((a > 0).mean()), 3), "mean_return": round(mean, 4),
            "median_return": round(float(np.median(a)), 4), "sd": round(sd, 4) if sd is not None else None,
            "ci95": [round(mean - half, 4), round(mean + half, 4)] if half is not None else None,
            "best": round(float(a.max()), 4), "worst": round(float(a.min()), 4)}


def _bootstrap_p(x: list[float], y: list[float], iters: int = 2000, seed: int = 11) -> float | None:
    """One-sided p-value that mean(x) > mean(y) (resampling under the pooled null)."""
    if len(x) < 5 or len(y) < 5:
        return None
    rng = np.random.default_rng(seed)
    xa, ya = np.array(x), np.array(y)
    obs = xa.mean() - ya.mean()
    pooled = np.concatenate([xa - xa.mean(), ya - ya.mean()]) + np.concatenate([xa, ya]).mean()
    cnt = 0
    for _ in range(iters):
        bx = rng.choice(pooled, len(xa))
        by = rng.choice(pooled, len(ya))
        if bx.mean() - by.mean() >= obs:
            cnt += 1
    return (cnt + 1) / (iters + 1)


def _returns(s, mode: str, since: datetime | None) -> list[float]:
    out = []
    for p in repo.closed_positions(s, mode):
        if since and to_utc(p.opened_at) < since:
            continue
        if p.cost_sol:
            out.append((p.realized_pnl_sol or 0.0) / p.cost_sol)
    return out


def experiment_report(s, mode: str, baseline: str = "lab") -> dict[str, Any]:
    from mci.paper_trading.lab import state_prefix

    started = repo.get_state(s, f"{state_prefix(mode)}_started_at")
    since = to_utc(datetime.fromisoformat(started)) if started else None
    exp = _returns(s, mode, since)
    base = _returns(s, baseline, since)
    es, bs = _stats(exp), _stats(base)
    days = (utcnow() - since).total_seconds() / 86400 if since else 0.0
    p = _bootstrap_p(exp, base)
    checks = [
        {"check": f"almeno {MIN_TRADES} operazioni chiuse", "ok": es["trades"] >= MIN_TRADES,
         "value": es["trades"]},
        {"check": f"almeno {MIN_DAYS} giorni di test", "ok": days >= MIN_DAYS, "value": round(days, 1)},
        {"check": "intervallo di confidenza 95% del rendimento medio sopra zero",
         "ok": bool(es.get("ci95") and es["ci95"][0] > 0), "value": es.get("ci95")},
        {"check": "meglio del Laboratorio nello stesso periodo (p < 0,05)",
         "ok": bool(p is not None and p < 0.05 and es.get("mean_return", -1) > bs.get("mean_return", 0)),
         "value": None if p is None else round(p, 4)},
    ]
    ok = all(c["ok"] for c in checks)
    return {
        "mode": mode, "baseline": baseline, "started_at": started, "days": round(days, 2),
        "experiment": es, "baseline_stats": bs, "p_value_vs_baseline": p, "checks": checks,
        "status": ("PROMUOVIBILE: serve la tua approvazione esplicita (il bot non promuove mai da solo)" if ok
                   else "NON PROMUOVIBILE: " + "; ".join(c["check"] for c in checks if not c["ok"])),
        "promotable": ok,
        "generated_at": utcnow().isoformat(),
    }
