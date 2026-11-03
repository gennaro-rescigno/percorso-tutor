"""Statistical evaluation of the feature store against real outcomes (numpy only, no paid services).

What it reports, always with sample sizes and 95% bootstrap confidence intervals:

* univariate AUC of every numeric feature vs two targets: ``hit_2x_first`` (opportunity) and ``rug_60m`` (risk);
  AUC 0.5 = no information. A feature is called informative only when its CI excludes 0.5;
* the risk and opportunity indices themselves (are they informative at all?);
* a walk-forward logistic regression (train on the past, test on the following period only) with AUC and Brier
  score vs the base rate: an out-of-sample check, never an in-sample fit;
* the shadow rules: outcome rates when the rule fires vs when it does not.

It NEVER changes the strategies or the rules. With too little data the verdict is "dati insufficienti".
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Any

import numpy as np

MIN_ROWS = 300
MIN_POSITIVES = 30
BOOTSTRAP = 100
MAX_ROWS = 30_000  # most recent observations used (memory and CPU bound on a small server)
CI_SAMPLE = 8_000  # bootstrap confidence intervals on a random subsample (point AUC uses every row)
EXCLUDE = {"version", "complete", "source", "price", "age_s", "deployer_observed_days", "stream_coverage", "quote_native"}


def _rankdata(a: np.ndarray) -> np.ndarray:
    """Average ranks with ties (same algorithm as scipy.stats.rankdata), vectorized."""
    sorter = np.argsort(a, kind="mergesort")
    inv = np.empty(sorter.size, dtype=np.intp)
    inv[sorter] = np.arange(sorter.size)
    s = a[sorter]
    obs = np.r_[True, s[1:] != s[:-1]]
    dense = obs.cumsum()[inv]
    count = np.r_[np.nonzero(obs)[0], len(obs)]
    return 0.5 * (count[dense] + count[dense - 1] + 1)


def auc(scores: np.ndarray, y: np.ndarray) -> float | None:
    """Mann-Whitney AUC with tie correction."""
    n_pos = int((y == 1).sum())
    n_neg = len(y) - n_pos
    if n_pos == 0 or n_neg == 0:
        return None
    ranks = _rankdata(np.asarray(scores, dtype=float))
    rp = ranks[y == 1].sum()
    return float((rp - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def auc_ci(scores: np.ndarray, y: np.ndarray, rng: np.random.Generator) -> tuple[float | None, float | None, float | None]:
    a = auc(scores, y)
    if a is None:
        return None, None, None
    n = len(y)
    base = np.arange(n) if n <= CI_SAMPLE else rng.choice(n, CI_SAMPLE, replace=False)
    boots = []
    for _ in range(BOOTSTRAP):
        idx = base[rng.integers(0, len(base), len(base))]
        b = auc(scores[idx], y[idx])
        if b is not None:
            boots.append(b)
    if len(boots) < BOOTSTRAP // 2:
        return a, None, None
    lo, hi = float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))
    if len(base) < n:
        # bootstrap on a subsample: keep its spread (conservative: wider than the full sample's) around the
        # full-sample estimate, so the interval always contains the reported AUC
        sub = auc(scores[base], y[base])
        if sub is not None:
            lo, hi = a - (sub - lo), a + (hi - sub)
    return a, max(lo, 0.0), min(hi, 1.0)


def _fit_logistic(x: np.ndarray, y: np.ndarray, l2: float = 1.0, iters: int = 300, lr: float = 0.1) -> np.ndarray:
    w = np.zeros(x.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-np.clip(x @ w, -30, 30)))
        grad = x.T @ (p - y) / len(y) + l2 * np.r_[0.0, w[1:]] / len(y)
        w -= lr * grad
    return w


def walk_forward(x: np.ndarray, y: np.ndarray, folds: int = 3) -> dict[str, Any]:
    """Expanding-window walk-forward: train on rows [0, k), test on [k, k + step). Rows are in time order."""
    n = len(y)
    step = n // (folds + 2)
    res = []
    for f in range(folds):
        k = step * (f + 2)
        tr, te = slice(0, k), slice(k, min(k + step, n))
        if y[tr].sum() < 10 or y[te].sum() < 3 or (y[te] == 0).sum() < 3:
            continue
        mu, sd = x[tr].mean(0), x[tr].std(0) + 1e-9
        xtr = np.c_[np.ones(k), (x[tr] - mu) / sd]
        xte = np.c_[np.ones(te.stop - k), (x[te] - mu) / sd]
        w = _fit_logistic(xtr, y[tr].astype(float))
        p = 1 / (1 + np.exp(-np.clip(xte @ w, -30, 30)))
        base = y[tr].mean()
        res.append({"train": k, "test": te.stop - k, "auc": auc(p, y[te]),
                    "brier": float(np.mean((p - y[te]) ** 2)), "brier_base": float(np.mean((base - y[te]) ** 2))})
    if not res:
        return {"verdict": "dati insufficienti per il walk-forward"}
    aucs = [r["auc"] for r in res if r["auc"] is not None]
    better = sum(1 for r in res if r["brier"] < r["brier_base"])
    return {"folds": res, "mean_auc": float(np.mean(aucs)) if aucs else None,
            "beats_base_rate_folds": f"{better}/{len(res)}",
            "verdict": ("informativo fuori campione" if aucs and min(aucs) > 0.55 and better == len(res)
                        else "non dimostrato fuori campione")}


def _matrix(rows: list[dict[str, Any]], names: list[str]) -> np.ndarray:
    x = np.full((len(rows), len(names)), np.nan)
    for i, r in enumerate(rows):
        for j, k in enumerate(names):
            v = r["features"].get(k)
            if isinstance(v, bool):
                v = float(v)
            if isinstance(v, (int, float)) and math.isfinite(v):
                x[i, j] = v
    return x


def evaluate_rows(rows: list[dict[str, Any]], seed: int = 7) -> dict[str, Any]:
    """``rows``: [{"observed_at", "features", "risk", "opportunity", "labels"}] sorted by time."""
    rng = np.random.default_rng(seed)
    usable = [r for r in rows if r.get("labels") and not r["labels"].get("incomplete")
              and not r["labels"].get("no_price") and r["features"].get("complete")]
    out: dict[str, Any] = {"rows_total": len(rows), "rows_usable": len(usable),
                           "min_rows": MIN_ROWS, "min_positives": MIN_POSITIVES}
    if not usable:
        out["verdict"] = "dati insufficienti: nessuna osservazione completa ed etichettata"
        return out
    targets = {"hit_2x_first": np.array([1 if r["labels"].get("hit_2x_first") else 0 for r in usable]),
               "rug_60m": np.array([1 if r["labels"].get("rug_60m") else 0 for r in usable])}
    out["base_rates"] = {k: {"positives": int(v.sum()), "rate": round(float(v.mean()), 4)} for k, v in targets.items()}
    enough = len(usable) >= MIN_ROWS and all(v.sum() >= MIN_POSITIVES for v in targets.values())
    names = sorted({k for r in usable for k, v in r["features"].items()
                    if k not in EXCLUDE and isinstance(v, (int, float, bool)) and v is not None})
    x = _matrix(usable, names)
    feats = []
    for j, k in enumerate(names):
        col = x[:, j]
        ok = ~np.isnan(col)
        entry: dict[str, Any] = {"feature": k, "n": int(ok.sum())}
        for tname, y in targets.items():
            if ok.sum() < 50 or y[ok].sum() < 10 or (y[ok] == 0).sum() < 10:
                entry[tname] = None
                continue
            a, lo, hi = auc_ci(col[ok], y[ok], rng)
            entry[tname] = {"auc": round(a, 3) if a is not None else None,
                            "ci": [round(lo, 3), round(hi, 3)] if lo is not None else None,
                            "informative": bool(lo is not None and (lo > 0.5 or hi < 0.5))}
        feats.append(entry)
    out["features"] = feats
    idx = {}
    for name, key, tname in (("indice di rischio", "risk", "rug_60m"), ("indice di opportunità", "opportunity", "hit_2x_first")):
        vals = np.array([(r.get(key) or {}).get("value") if (r.get(key) or {}).get("value") is not None else np.nan
                         for r in usable], dtype=float)
        ok = ~np.isnan(vals)
        y = targets[tname]
        if ok.sum() >= 50 and y[ok].sum() >= 10 and (y[ok] == 0).sum() >= 10:
            a, lo, hi = auc_ci(vals[ok], y[ok], rng)
            idx[name] = {"target": tname, "n": int(ok.sum()), "auc": round(a, 3) if a is not None else None,
                         "ci": [round(lo, 3), round(hi, 3)] if lo is not None else None}
        else:
            idx[name] = {"target": tname, "n": int(ok.sum()), "verdict": "dati insufficienti"}
    out["indices"] = idx
    rules: dict[str, Any] = {}
    for r in usable:
        for code in (r.get("risk") or {}).get("shadow_hits") or []:
            rules.setdefault(code, None)
    for code in rules:
        hit = np.array([code in ((r.get("risk") or {}).get("shadow_hits") or []) for r in usable])
        y = targets["rug_60m"]
        g = targets["hit_2x_first"]
        rules[code] = {"fires": int(hit.sum()), "rug_rate_if_fires": round(float(y[hit].mean()), 3) if hit.any() else None,
                       "rug_rate_otherwise": round(float(y[~hit].mean()), 3) if (~hit).any() else None,
                       "win_rate_if_fires": round(float(g[hit].mean()), 3) if hit.any() else None,
                       "win_rate_otherwise": round(float(g[~hit].mean()), 3) if (~hit).any() else None}
    out["shadow_rules"] = rules
    if enough:
        xf = np.where(np.isnan(x), np.nanmedian(np.where(np.isnan(x), np.nan, x), axis=0), x)
        xf = np.nan_to_num(xf)
        out["walk_forward"] = {t: walk_forward(xf, y) for t, y in targets.items()}
        out["verdict"] = "campione sufficiente: leggere le AUC con i loro intervalli di confidenza"
    else:
        out["walk_forward"] = None
        out["verdict"] = (f"dati insufficienti per conclusioni robuste: servono almeno {MIN_ROWS} osservazioni e "
                          f"{MIN_POSITIVES} casi positivi per ciascun esito")
    return out


def run_research(horizon: str = "t+5m", days: int = 7) -> dict[str, Any]:
    from sqlalchemy import select

    from mci.database.models import FeatureSnapshot
    from mci.database.session import session_scope
    from mci.domain import utcnow

    since: datetime = utcnow() - timedelta(days=days)
    with session_scope() as s:
        rows = [{"observed_at": r.observed_at, "features": r.features or {}, "risk": r.risk, "opportunity": r.opportunity,
                 "labels": r.labels}
                for r in s.scalars(select(FeatureSnapshot).where(FeatureSnapshot.horizon == horizon,
                                                                  FeatureSnapshot.observed_at >= since,
                                                                  FeatureSnapshot.labels.is_not(None))
                                   .order_by(FeatureSnapshot.observed_at.desc()).limit(MAX_ROWS)).all()]
    rows.reverse()  # time order for the walk-forward
    rep = evaluate_rows(rows)
    rep["horizon"] = horizon
    rep["generated_at"] = utcnow().isoformat()
    return rep
