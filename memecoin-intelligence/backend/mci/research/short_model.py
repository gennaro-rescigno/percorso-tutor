"""5-10 minute entry model on OUR data: does the full on-chain picture tell when to enter a curve?

PRE-REGISTERED on 2026-11-03 (before any result):
  * decision points: the feature snapshots at 1, 2, 3, 5, 7 and 10 minutes of every classic launch with complete
    stream coverage and a price (the extra minutes are written only for launches with >= 5 trades);
  * features: every numeric fact of the snapshot computed from the trades up to that moment (activity, buyers,
    flows, sniper and block-0 shares, concentration, flippers, creator behaviour, curve progress and its speed,
    distance from the peak, last-minute buyers, creator history); never anything from after the moment;
  * targets: net return of a 0.1 SOL trade held 5 and 10 minutes (price of the stream candles), after 3% latency,
    1.25% fee per side and 1% priority fees; the model learns P(net return > 0) (logistic regression, numpy,
    standardised features, missing values set to the training mean, l2 = 1);
  * walk-forward by UTC day: trained on all days before, tested on the next day only; at least 3 training days;
  * selections on the test day, one trade per token (its first selected moment): every snapshot (reference),
    top 10% and top 2% of the predicted probability (thresholds taken from the training days);
  * verdict "promettente" only with >= 300 selected trades over >= 5 test days, a 95% bootstrap interval of the
    average above zero and above the reference. It never trades: a promising result needs the user's approval and
    its own virtual portfolio.
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import timedelta
from typing import Any

import numpy as np

LAT, FEE, PRIO = 0.03, 0.0125, 0.01
HORIZONS = ("t+1m", "t+2m", "t+3m", "t+5m", "t+7m", "t+10m")
HOLDS = (5, 10)
EXCLUDE = {"version", "complete", "source", "price", "stream_coverage", "mayhem", "quote_native",
           "deployer_observed_days"}
MIN_TRAIN_DAYS, MIN_TRADES, MIN_TEST_DAYS, BOOT = 3, 300, 5, 1000
MAX_ROWS = 60_000  # bounded memory on the small server (features are JSON)


def net(gross_pct: float) -> float:
    return (1 + gross_pct / 100) / (1 + LAT) * (1 - FEE) ** 2 - PRIO - 1


def feature_names(rows: list[dict]) -> list[str]:
    names: set[str] = set()
    for r in rows[:5000]:
        for k, v in r["features"].items():
            if k not in EXCLUDE and isinstance(v, (int, float, bool)) and not isinstance(v, str):
                names.add(k)
    return sorted(names)


def matrix(rows: list[dict], names: list[str]) -> np.ndarray:
    x = np.full((len(rows), len(names)), np.nan)
    for i, r in enumerate(rows):
        f = r["features"]
        for j, k in enumerate(names):
            v = f.get(k)
            if isinstance(v, bool):
                v = float(v)
            if isinstance(v, (int, float)) and math.isfinite(v):
                x[i, j] = v
    return x


def fit(x: np.ndarray, y: np.ndarray, l2: float = 1.0, iters: int = 300, lr: float = 0.1):
    mu = np.nanmean(x, axis=0)
    mu = np.where(np.isnan(mu), 0.0, mu)
    xf = np.where(np.isnan(x), mu, x)
    sd = xf.std(axis=0) + 1e-9
    z = np.c_[np.ones(len(xf)), (xf - mu) / sd]
    w = np.zeros(z.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-np.clip(z @ w, -30, 30)))
        w -= lr * (z.T @ (p - y) / len(y) + l2 * np.r_[0.0, w[1:]] / len(y))
    return mu, sd, w


def predict(model, x: np.ndarray) -> np.ndarray:
    mu, sd, w = model
    xf = np.where(np.isnan(x), mu, x)
    z = np.c_[np.ones(len(xf)), (xf - mu) / sd]
    return 1 / (1 + np.exp(-np.clip(z @ w, -30, 30)))


def _boot(x: np.ndarray, rng) -> tuple[float, float]:
    if len(x) < 30:
        return float("nan"), float("nan")
    m = x[rng.integers(0, len(x), size=(BOOT, len(x)))].mean(axis=1) if len(x) <= 5000 else \
        rng.normal(x.mean(), x.std(ddof=1) / np.sqrt(len(x)), BOOT)
    lo, hi = np.percentile(m, [2.5, 97.5])
    return float(lo), float(hi)


def evaluate(rows: list[dict], seed: int = 3) -> dict[str, Any]:
    """rows: {"token", "day", "ts", "features", "labels"} for the decision points, any order."""
    rng = np.random.default_rng(seed)
    rows = sorted(rows, key=lambda r: r["ts"])
    names = feature_names(rows)
    days = sorted({r["day"] for r in rows})
    out: dict[str, Any] = {"rows": len(rows), "days": len(days), "features": len(names), "holds": {}}
    for hold in HOLDS:
        key = f"ret_end_{hold}m"
        usable = [r for r in rows if r["labels"].get(key) is not None]
        if not usable:
            out["holds"][hold] = {"verdict": "dati insufficienti: etichette a 5/10 minuti non ancora disponibili"}
            continue
        x = matrix(usable, names)
        ret = np.array([net(float(r["labels"][key])) for r in usable])
        y = (ret > 0).astype(float)
        dd = np.array([r["day"] for r in usable])
        tok = [r["token"] for r in usable]
        picks: dict[str, list] = defaultdict(list)
        tested = []
        for d in days:
            tr, te = dd < d, dd == d
            if len({int(v) for v in dd[tr]}) < MIN_TRAIN_DAYS or te.sum() == 0 or y[tr].sum() < 20:
                continue
            model = fit(x[tr], y[tr])
            p_tr, p_te = predict(model, x[tr]), predict(model, x[te])
            q90, q98 = np.quantile(p_tr, 0.90), np.quantile(p_tr, 0.98)
            idx = np.where(te)[0]
            tested.append(int(d))
            for name, thr in (("riferimento", -1.0), ("top 10%", q90), ("top 2%", q98)):
                seen = set()
                for i, p in zip(idx, p_te):
                    if p >= thr and tok[i] not in seen:
                        seen.add(tok[i])
                        picks[name].append((ret[i], d))
        res = {}
        ref = np.array([v for v, _ in picks.get("riferimento", [])])
        for name, lst in picks.items():
            v = np.array([a for a, _ in lst])
            lo, hi = _boot(v, rng)
            n_days = len({d for _, d in lst})
            r = {"n": len(v), "test_days": n_days, "mean_pct": round(100 * v.mean(), 2),
                 "ci_pct": [round(100 * lo, 2), round(100 * hi, 2)], "median_pct": round(100 * float(np.median(v)), 2),
                 "win_rate": round(float((v > 0).mean()), 3)}
            if name == "riferimento":
                r["verdict"] = "riferimento: tutti i momenti di decisione"
            elif len(v) < MIN_TRADES or n_days < MIN_TEST_DAYS:
                r["verdict"] = f"dati insufficienti ({len(v)}/{MIN_TRADES} operazioni, {n_days}/{MIN_TEST_DAYS} giorni)"
            elif lo > 0 and len(ref) and lo > ref.mean():
                r["verdict"] = "promettente (serve la tua approvazione per un portafoglio virtuale)"
            else:
                r["verdict"] = "non funziona" if v.mean() <= 0 else "non dimostrata"
            res[name] = r
        out["holds"][hold] = {"tested_days": len(tested), "selections": res}
    return out


def run_short_model(days: int = 21) -> dict[str, Any]:
    from sqlalchemy import select

    from mci.database.models import FeatureSnapshot
    from mci.database.session import session_scope
    from mci.domain import utcnow

    since = utcnow() - timedelta(days=days)
    rows = []
    with session_scope() as s:
        for tok, at, f, lab in s.execute(select(FeatureSnapshot.token_address, FeatureSnapshot.observed_at,
                                               FeatureSnapshot.features, FeatureSnapshot.labels).where(
                FeatureSnapshot.horizon.in_(HORIZONS), FeatureSnapshot.observed_at >= since,
                FeatureSnapshot.labels.is_not(None)).order_by(FeatureSnapshot.observed_at.desc()).limit(MAX_ROWS)):
            f = f or {}
            if not lab or lab.get("incomplete") or lab.get("no_price") or not f.get("complete") or f.get("mayhem") \
                    or f.get("quote_native") is False:
                continue
            ts = at.timestamp() if at.tzinfo else at.replace(tzinfo=__import__("datetime").timezone.utc).timestamp()
            rows.append({"token": tok, "day": int(ts // 86400), "ts": ts, "features": f, "labels": lab})
    rep = evaluate(rows)
    rep["generated_at"] = utcnow().isoformat()
    rep["note"] = ("Modello che stima quando un'entrata di 5-10 minuti chiude in guadagno netto. Addestrato solo sui "
                   "giorni passati e giudicato sul giorno dopo; non compra mai nulla.")
    return rep
