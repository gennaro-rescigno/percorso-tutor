"""Rules lab: pre-registered entry rules evaluated on EVERY observed launch, with costs, out of sample.

Why: a virtual portfolio sees a few trades a day; the feature store sees every launch at 1, 5 and 15 minutes and,
four hours later, what really happened. Applying a fixed rule to every snapshot gives hundreds of hypothetical
trades a day, so a rule can be judged in days instead of months — without touching any portfolio.

PRE-REGISTERED on 2026-11-03 (REGISTERED_AT), before looking at any result of these rules:
  * universe: classic launches (not mayhem), complete stream coverage, labelled snapshot with a price;
  * rules R0..R6 below, exits E1..E3 below; costs: entry 3% worse than the snapshot (latency), pump.fun fee 1.25% per
    side, priority fees 1% per round trip; the stop of E1 is filled at -60% (gaps through the stop were the main
    loss of the paper portfolios);
  * only snapshots observed AFTER REGISTERED_AT count for the verdict ("fuori campione"); older ones are shown
    for information only ("in campione": the AUCs of these features were already seen);
  * verdict "promettente" needs >= 300 out-of-sample trades, a 95% bootstrap interval of the mean above zero
    and Benjamini-Hochberg q < 0.05 over all rule x exit pairs. Even then nothing changes by itself: a rule
    can only become a strategy after the user's explicit approval and a separate virtual portfolio.
Known optimism: the stream candles stop at the migration, so a token that graduates is valued at its last curve
price (the post-migration dump is not seen); this is stated in the report.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import numpy as np

REGISTERED_AT = datetime(2026, 11, 3, 18, 0, tzinfo=timezone.utc)
LAT, FEE, PRIO, STOP_FILL = 0.03, 0.0125, 0.01, -60.0
MIN_OOS = 300
BOOT = 1000
MAX_ROWS = 60_000


def _f(x: dict, k: str, default: float | None = None) -> float | None:
    v = x.get(k)
    return default if v is None else float(v)


Rule = tuple[str, str, Callable[[dict], bool]]
RULES: list[Rule] = [
    ("R0", "t+5m", lambda f: True),
    ("R1", "t+5m", lambda f: (_f(f, "n_trades", 0) >= 50) and (_f(f, "drawdown_from_peak_pct", 0) >= 40)),
    ("R2", "t+5m", lambda f: (_f(f, "n_trades", 0) >= 100) and (_f(f, "drawdown_from_peak_pct", 0) >= 50)),
    ("R3", "t+5m", lambda f: (_f(f, "holders_net", 0) >= 30) and (_f(f, "top10_net_pct", 100) <= 40)),
    ("R4", "t+5m", lambda f: (f.get("creator_sold") is False) and (_f(f, "n_trades", 0) >= 30)),
    ("R5", "t+15m", lambda f: _f(f, "buyers_last_60s", 0) >= 5),
    ("R6", "t+5m", lambda f: (_f(f, "n_trades", 0) >= 50) and (_f(f, "drawdown_from_peak_pct", 0) >= 40)
     and (_f(f, "sniper_pct", 100) <= 10)),
]
DESCRIPTIONS = {
    "R0": "tutti i lanci a 5 minuti (riferimento)",
    "R1": "a 5 min: >= 50 operazioni e già sceso >= 40% dal massimo",
    "R2": "a 5 min: >= 100 operazioni e già sceso >= 50% dal massimo",
    "R3": "a 5 min: >= 30 holder e i primi 10 hanno <= 40%",
    "R4": "a 5 min: il creatore non ha venduto e >= 30 operazioni",
    "R5": "a 15 min: >= 5 acquirenti nell'ultimo minuto (ancora vivo)",
    "R6": "come R1 ma sniper <= 10% della supply",
}
EXITS = {
    "E1": "obiettivo +100% / stop -50% (riempito a -60%), altrimenti prezzo dopo 4 ore",
    "E2": "vendita dopo 60 minuti",
    "E3": "vendita dopo 4 ore",
}


def net_pct(gross_pct: float) -> float:
    return ((1 + gross_pct / 100) / (1 + LAT) * (1 - FEE) ** 2 - PRIO - 1) * 100


def trade_return(lab: dict, exit_kind: str) -> float | None:
    if exit_kind == "E1":
        fp = lab.get("first_passage")
        if fp == "2x_first":
            return net_pct(100.0)
        if fp == "half_first":
            return net_pct(STOP_FILL)
        g = lab.get("ret_end_240m")
    elif exit_kind == "E2":
        g = lab.get("ret_end_60m")
    else:
        g = lab.get("ret_end_240m")
    return None if g is None else net_pct(float(g))


def _boot(x: np.ndarray, rng: np.random.Generator) -> tuple[float, float, float]:
    if len(x) < 30:
        return float("nan"), float("nan"), float("nan")
    if len(x) <= 5000:
        means = x[rng.integers(0, len(x), size=(BOOT, len(x)))].mean(axis=1)
    else:
        means = rng.normal(x.mean(), x.std(ddof=1) / np.sqrt(len(x)), BOOT)
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(lo), float(hi), max(float((means <= 0).mean()), 1.0 / BOOT)


def bh(p: list[float]) -> list[float]:
    arr = np.asarray(p, float)
    n = len(arr)
    q = np.full(n, np.nan)
    ok = ~np.isnan(arr)
    idx = np.where(ok)[0]
    if not len(idx):
        return q.tolist()
    order = idx[np.argsort(arr[idx])]
    m = len(order)
    prev = 1.0
    for rank in range(m - 1, -1, -1):
        i = order[rank]
        prev = min(prev, arr[i] * m / (rank + 1))
        q[i] = prev
    return q.tolist()


def evaluate(rows_by_horizon: dict[str, list[tuple[datetime, dict, dict]]], seed: int = 11) -> dict[str, Any]:
    """rows: (observed_at, features, labels) per horizon."""
    rng = np.random.default_rng(seed)
    out, pvals = [], []
    for code, horizon, rule in RULES:
        rows = rows_by_horizon.get(horizon, [])
        sel = [(at, lab) for at, f, lab in rows if rule(f)]
        for ek in EXITS:
            oos = np.array([r for at, lab in sel if at >= REGISTERED_AT and (r := trade_return(lab, ek)) is not None])
            ins = np.array([r for at, lab in sel if at < REGISTERED_AT and (r := trade_return(lab, ek)) is not None])
            lo, hi, p = _boot(oos, rng)
            out.append({"rule": code, "description": DESCRIPTIONS[code], "horizon": horizon, "exit": ek,
                        "n_oos": int(len(oos)), "mean_oos_pct": round(float(oos.mean()), 2) if len(oos) else None,
                        "ci_oos": [round(lo, 2), round(hi, 2)] if len(oos) >= 30 else None,
                        "median_oos_pct": round(float(np.median(oos)), 2) if len(oos) else None,
                        "win_oos": round(float((oos > 0).mean()), 3) if len(oos) else None,
                        "n_in_sample": int(len(ins)),
                        "mean_in_sample_pct": round(float(ins.mean()), 2) if len(ins) else None})
            pvals.append(p if len(oos) >= MIN_OOS else float("nan"))
    for row, q in zip(out, bh(pvals)):
        row["q"] = None if q != q else round(q, 4)
        if row["n_oos"] < MIN_OOS:
            row["verdict"] = f"dati insufficienti ({row['n_oos']}/{MIN_OOS} fuori campione)"
        elif row["q"] is not None and row["q"] < 0.05 and row["ci_oos"] and row["ci_oos"][0] > 0:
            row["verdict"] = "promettente (serve la tua approvazione per provarla in un portafoglio)"
        else:
            row["verdict"] = "non funziona" if (row["mean_oos_pct"] or 0) <= 0 else "non dimostrata"
    return {"registered_at": REGISTERED_AT.isoformat(), "exits": EXITS, "results": out,
            "costs": {"latency": LAT, "fee_per_side": FEE, "priority_round_trip": PRIO, "stop_fill_pct": STOP_FILL},
            "note": "Regole fissate il 3 novembre 2026 prima di vedere i loro risultati; contano solo i lanci osservati "
                    "dopo. Ottimismo noto: per i token che si diplomano il valore è l'ultimo prezzo sulla curva "
                    "(il crollo dopo la migrazione non è visto)."}


def run_rules_lab(days: int = 30) -> dict[str, Any]:
    from sqlalchemy import select

    from mci.database.models import FeatureSnapshot
    from mci.database.session import session_scope
    from mci.domain import utcnow

    since = utcnow() - timedelta(days=days)
    rows: dict[str, list] = {}
    with session_scope() as s:
        for h in {h for _, h, _ in RULES}:
            got = s.execute(select(FeatureSnapshot.observed_at, FeatureSnapshot.features, FeatureSnapshot.labels).where(
                FeatureSnapshot.horizon == h, FeatureSnapshot.observed_at >= since, FeatureSnapshot.labels.is_not(None))
                .order_by(FeatureSnapshot.observed_at.desc()).limit(MAX_ROWS)).all()
            rows[h] = [(at if at.tzinfo else at.replace(tzinfo=timezone.utc), f or {}, lab) for at, f, lab in got
                       if lab and not lab.get("incomplete") and not lab.get("no_price")
                       and (f or {}).get("complete") and not (f or {}).get("mayhem")]
    rep = evaluate(rows)
    rep["generated_at"] = utcnow().isoformat()
    rep["rows"] = {h: len(v) for h, v in rows.items()}
    return rep
