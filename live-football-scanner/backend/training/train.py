"""Fit the in-play hazard models and validate them out-of-sample.

Splits (no match is used both for fitting and for validation):
  * train         : Premier League, La Liga, Serie A, Ligue 1 2015/16, matches before 2016-03-01
  * val_temporal  : same leagues, matches from 2016-03-01 (later in time than every training match)
  * val_cross     : other competitions & seasons (World Cups 2018/2022, Euro 2020/2024, Copa America 2024,
                    AFCON 2023, Indian Super League 2021/22, Bundesliga team-seasons 2015/16 & 2023/24)

Usage:  python -m training.train
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time

import numpy as np

from app.engine.features import CORNER_FEATURES, GOAL_FEATURES
from app.engine.forecast import forecast
from app.engine.markets import Selection, outcome_probs
from app.engine.model import DEFAULT_MODEL_PATH, GLM, ModelBundle
from training.glm_fit import fit_poisson
from training.dataset import (build, compute_priors, compute_refs, goals_mu, load_matches,
                              split_of, stoppage_distribution)

PRIOR_K = 4.0
OLD = {"Premier League 2015/16", "La Liga 2015/16", "Serie A 2015/16", "Ligue 1 2015/16"}
MODERN = {"FIFA World Cup 2022", "UEFA Euro 2024", "Copa America 2024", "African Cup of Nations 2023",
          "Bundesliga 2023/24 (selected team)", "Indian Super League 2021/22", "UEFA Euro 2020"}


def fit_glm(name: str, features: list[str], data: dict, target: str) -> GLM:
    idx = [data["name_idx"][f] for f in features]
    X = np.ascontiguousarray(data["X"][:, idx])
    y = data[target]
    t0 = time.time()
    res = fit_poisson(X, y, data["offset"], data["groups"])
    del X
    print(f"  {name}: {res.n:,} rows, {len(idx)} params, deviance {res.deviance:,.1f}, AIC {res.aic:,.1f}, "
          f"pearson-disp {res.pearson_dispersion:.3f}, {res.iterations} it ({time.time() - t0:.1f}s)", flush=True)
    return GLM(name=name, features=features, coef=res.coef, cov=res.cov, dispersion=0.0,
               meta={"n_rows": int(res.n), "n_matches": int(len(np.unique(data["groups"]))),
                     "aic": res.aic, "deviance": res.deviance, "pearson_dispersion": res.pearson_dispersion,
                     "coef_table": [{"feature": f, "coef": float(c), "se": float(s), "z": float(c / s) if s > 0 else 0.0}
                                    for f, c, s in zip(features, res.coef, res.se)]})


def corner_dispersion(glm: GLM, data: dict) -> float:
    """Method-of-moments NB alpha for *remaining total corners* at the origin level."""
    idx = [data["name_idx"][f] for f in glm.features]
    eta = data["X"][:, idx].astype(np.float64) @ glm.coef + data["offset"]
    lam = np.exp(eta)
    oid = data["oid"]
    m = np.bincount(oid, weights=lam)
    r = np.bincount(oid, weights=data["y_corner"].astype(float))
    keep = m > 0
    m, r = m[keep], r[keep]
    alpha = float(np.sum((r - m) ** 2 - m) / np.sum(m ** 2))
    return max(alpha, 0.0)


# --------------------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------------------

def _logloss(p: np.ndarray, y: np.ndarray) -> float:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def _brier(p: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean((p - y) ** 2))


def _calibration(p: np.ndarray, y: np.ndarray, bins: int = 10) -> tuple[list[dict], float]:
    edges = np.linspace(0, 1, bins + 1)
    out = []
    ece = 0.0
    for i in range(bins):
        msk = (p >= edges[i]) & ((p < edges[i + 1]) if i < bins - 1 else (p <= 1))
        n = int(msk.sum())
        if n == 0:
            continue
        mp, of = float(p[msk].mean()), float(y[msk].mean())
        se = float(np.sqrt(max(of * (1 - of), 1e-4) / n))
        out.append({"bin": i, "p_mean": mp, "obs": of, "n": n, "se": se})
        ece += n * abs(mp - of)
    return out, float(ece / max(len(p), 1))


def baseline_probs(rec, mu_h: float, mu_a: float, stoppage) -> dict:
    """B0: independent Poisson with constant rate x remaining time (no score/stat information)."""
    from scipy import stats as st
    exp_st1 = sum(i * p for i, p in enumerate(stoppage["h1"]))
    exp_st2 = sum(i * p for i, p in enumerate(stoppage["h2"]))
    if rec.period == 1:
        rem = (45 + exp_st1 - rec.clock) + (45 + exp_st2)
        rem_ht = 45 + exp_st1 - rec.clock
    else:
        rem = 90 + exp_st2 - rec.clock
        rem_ht = 0.0
    rem = max(rem, 0.5)  # origin already inside stoppage time
    lh, la = mu_h * rem / 93.0, mu_a * rem / 93.0
    k = np.arange(15)
    ph = st.poisson.pmf(k, lh)
    pa = st.poisson.pmf(k, la)
    J = np.outer(ph, pa)
    gh, ga = rec.state.home.goals, rec.state.away.goals
    H = gh + k[:, None]
    A = ga + k[None, :]
    tot = H + A
    rate10 = (mu_h + mu_a) / 93.0 * 10
    rate_ht = (mu_h + mu_a) / 93.0 * rem_ht
    rate_2h = (mu_h + mu_a) / 93.0 * ((45 + exp_st2) if rec.period == 1 else rem)
    return {
        "any_more": 1 - J[0, 0],
        "over25": float(J[tot > 2.5].sum()),
        "home_win": float(J[H > A].sum()), "draw": float(J[H == A].sum()), "away_win": float(J[H < A].sum()),
        "btts": float(J[(H > 0) & (A > 0)].sum()),
        "next_home": (1 - np.exp(-(lh + la))) * lh / (lh + la), "next_away": (1 - np.exp(-(lh + la))) * la / (lh + la),
        "next_none": float(np.exp(-(lh + la))),
        "goal10": 1 - np.exp(-rate10), "goal_ht": 1 - np.exp(-rate_ht), "goal_2h": 1 - np.exp(-rate_2h),
        "home_scores": float(1 - st.poisson.pmf(0, lh)),
    }


def model_probs(bundle: ModelBundle, rec, model_name: str) -> dict:
    fc = forecast(bundle, rec.state, goal_model=model_name, n_draws=1, with_corners=True)
    tot_now = rec.state.home.goals + rec.state.away.goals

    def pw(sel):
        o = outcome_probs(fc, sel, rec.period)
        return None if o is None else float(o.win[0])
    out = {
        "any_more": pw(Selection("total_goals", "over", tot_now + 0.5)),
        "over25": pw(Selection("total_goals", "over", 2.5)),
        "home_win": pw(Selection("1x2", "home")), "draw": pw(Selection("1x2", "draw")),
        "away_win": pw(Selection("1x2", "away")),
        "btts": pw(Selection("btts", "yes")),
        "next_home": float(fc.p_next_home[0]), "next_away": float(fc.p_next_away[0]),
        "next_none": float(fc.p_next_none[0]),
        "goal10": float(fc.p_goal_next10[0]),
        "goal_ht": pw(Selection("ht_total_goals", "over", tot_now + 0.5)) if rec.period == 1 else 0.0,
        "goal_2h": float(fc.p_goal_2h[0]),
        "home_scores": pw(Selection("team_goals_home", "over", rec.state.home.goals + 0.5)),
    }
    if fc.corners_home is not None:
        now = sum(fc.corners_now)
        out["corners_mean_rem"] = float(fc.corners_home[0] + fc.corners_away[0])
        for d in (2.5, 4.5):
            out[f"corners_over_now+{d}"] = pw(Selection("total_corners", "over", now + d))
    return out


def actuals(rec) -> dict:
    fh, fa = rec.final
    gh, ga = rec.state.home.goals, rec.state.away.goals
    return {
        "any_more": int(fh + fa > gh + ga), "over25": int(fh + fa > 2.5),
        "home_win": int(fh > fa), "draw": int(fh == fa), "away_win": int(fh < fa),
        "btts": int(fh > 0 and fa > 0),
        "next_home": int(rec.next_goal == 0), "next_away": int(rec.next_goal == 1),
        "next_none": int(rec.next_goal == 2),
        "goal10": rec.goal_next10, "goal_ht": int(sum(rec.ht) > gh + ga) if rec.period == 1 else 0,
        "goal_2h": int(rec.goals_2h > ((gh + ga - sum(rec.ht)) if rec.period == 2 else 0)),
        "home_scores": int(fh > gh),
        "corners_rem": sum(rec.corners_final) - (rec.state.home.corners + rec.state.away.corners),
    }


# metric name -> (family, applicability)
BINARY_TARGETS = {
    "any_more": ("totals", lambda r: True),
    "over25": ("totals", lambda r: r.state.home.goals + r.state.away.goals <= 2),
    "btts": ("btts", lambda r: not (r.state.home.goals > 0 and r.state.away.goals > 0)),
    "home_scores": ("team_totals", lambda r: True),
    "goal10": ("goal_next_10", lambda r: True),
    "goal_ht": ("ht_totals", lambda r: r.period == 1),
    "goal_2h": ("goal_2h", lambda r: r.period == 1 or (r.state.home.goals + r.state.away.goals == sum(r.ht))),
}


def evaluate(bundle: ModelBundle, records: list, mu_h: float, mu_a: float, stoppage_eval: dict,
             models: list[str]) -> dict:
    """Out-of-sample metrics for each model + baseline, per market family and per minute band."""
    preds = {m: [] for m in ["baseline"] + models}
    acts = []
    eval_bundle = ModelBundle(bundle.version, bundle.glms, bundle.refs, bundle.mu_goals,
                              bundle.prior_pseudo_matches, stoppage_eval)
    t0 = time.time()
    for i, rec in enumerate(records):
        acts.append(actuals(rec))
        preds["baseline"].append(baseline_probs(rec, mu_h, mu_a, stoppage_eval))
        for m in models:
            preds[m].append(model_probs(eval_bundle, rec, m))
        if (i + 1) % 2000 == 0:
            print(f"    {i + 1}/{len(records)} origins ({time.time() - t0:.0f}s)", flush=True)
    report: dict = {"n_origins": len(records), "n_matches": len({r.match_id for r in records}), "binary": {},
                    "multiclass": {}, "calibration": {}, "by_minute": {}, "corners": {}}
    minute = np.array([r.clock if r.period == 2 else r.clock for r in records])
    for tgt, (fam, ok) in BINARY_TARGETS.items():
        msk = np.array([ok(r) for r in records])
        y = np.array([a[tgt] for a in acts], dtype=float)[msk]
        entry = {"family": fam, "n": int(msk.sum()), "base_rate": float(y.mean())}
        for m in preds:
            p = np.array([pp[tgt] for pp in preds[m]], dtype=float)[msk]
            entry[m] = {"logloss": _logloss(p, y), "brier": _brier(p, y)}
            cal, ece = _calibration(p, y)
            entry[m]["ece"] = ece
            if m != "baseline":
                report["calibration"].setdefault(m, {})[tgt] = cal
        report["binary"][tgt] = entry
    # 1X2 and next goal (multiclass log loss)
    for name, keys in (("1x2", ("home_win", "draw", "away_win")), ("next_goal", ("next_home", "next_away", "next_none"))):
        Y = np.array([[a[k] for k in keys] for a in acts], dtype=float)
        entry = {"n": len(acts)}
        for m in preds:
            Pm = np.array([[pp[k] for k in keys] for pp in preds[m]], dtype=float)
            Pm = np.clip(Pm, 1e-6, 1)
            Pm = Pm / Pm.sum(1, keepdims=True)
            ll = float(-np.mean(np.sum(Y * np.log(Pm), 1)))
            # ranked probability score
            cumP, cumY = np.cumsum(Pm, 1)[:, :-1], np.cumsum(Y, 1)[:, :-1]
            rps = float(np.mean(np.sum((cumP - cumY) ** 2, 1) / (len(keys) - 1)))
            entry[m] = {"logloss": ll, "rps": rps}
            if m != "baseline":
                cal_all = []
                for j, k in enumerate(keys):
                    cal, ece = _calibration(Pm[:, j], Y[:, j])
                    cal_all.append(ece)
                    report["calibration"].setdefault(m, {})[k] = cal
                entry[m]["ece"] = float(np.mean(cal_all))
        report["multiclass"][name] = entry
    # by minute band for the main model (any more goals)
    bands = [(0, 30), (30, 46), (46, 70), (70, 80), (80, 100)]
    for lo, hi in bands:
        msk = (minute >= lo) & (minute < hi)
        if msk.sum() == 0:
            continue
        y = np.array([a["any_more"] for a in acts], dtype=float)[msk]
        row = {"n": int(msk.sum()), "base_rate": float(y.mean())}
        for m in preds:
            p = np.array([pp["any_more"] for pp in preds[m]], dtype=float)[msk]
            row[m] = {"logloss": _logloss(p, y), "mean_pred": float(p.mean())}
        report["by_minute"][f"{lo}-{hi}"] = row
    # corners (main model only — the corner model is shared)
    m0 = models[-1]
    has = np.array(["corners_mean_rem" in pp for pp in preds[m0]])
    if has.any():
        mean_rem = np.array([pp.get("corners_mean_rem", np.nan) for pp in preds[m0]])[has]
        act_rem = np.array([a["corners_rem"] for a in acts], dtype=float)[has]
        out = {"n": int(has.sum()), "mean_pred": float(mean_rem.mean()), "mean_obs": float(act_rem.mean()),
               "mae": float(np.mean(np.abs(mean_rem - act_rem)))}
        for d in (2.5, 4.5):
            key = f"corners_over_now+{d}"
            p = np.array([pp[key] for pp in preds[m0]], dtype=float)[has]
            y = (act_rem > d).astype(float)
            cal, ece = _calibration(p, y)
            out[key] = {"logloss": _logloss(p, y), "brier": _brier(p, y), "ece": ece, "base_rate": float(y.mean())}
            report["calibration"].setdefault(m0, {})[key] = cal
        report["corners"] = out
    return report


def family_margins(reports: dict[str, dict], model: str) -> dict[str, float]:
    """Prudential probability margin per market family = worst out-of-sample ECE (min 1.5pp)."""
    fam_ece: dict[str, float] = {}
    for rep in reports.values():
        for tgt, e in rep["binary"].items():
            fam = e["family"]
            fam_ece[fam] = max(fam_ece.get(fam, 0.0), e[model]["ece"])
        for name, e in rep["multiclass"].items():
            fam_ece[name] = max(fam_ece.get(name, 0.0), e[model]["ece"])
        if rep.get("corners"):
            fam_ece["corners"] = max(fam_ece.get("corners", 0.0),
                                     *[rep["corners"][k]["ece"] for k in rep["corners"] if k.startswith("corners_over")])
    out = {k: round(max(v, 0.015), 4) for k, v in fam_ece.items()}
    # derived families
    out.setdefault("ht_1x2", max(out.get("1x2", 0.03), out.get("ht_totals", 0.03)))
    out["correct_score"] = max(out.get("1x2", 0.03), 0.03)
    out["team_totals"] = out.get("team_totals", out.get("totals", 0.03))
    return out


def main() -> int:
    t0 = time.time()
    matches = load_matches()
    mu = goals_mu(matches)
    priors = compute_priors(matches, mu, PRIOR_K)
    refs = compute_refs(matches)
    st_train = stoppage_distribution(matches, OLD)
    st_modern = stoppage_distribution(matches, MODERN)
    counts = {s: sum(1 for m in matches if split_of(m) == s) for s in ("train", "val_temporal", "val_cross")}
    print("matches per split:", counts, flush=True)

    data = build(matches, priors, refs, st_train, {"train"}, {"val_temporal", "val_cross"})
    print(f"training rows: {data['X'].shape}, goals {int(data['y_goal'].sum())}, "
          f"corners {int(data['y_corner'].sum())} ({time.time() - t0:.0f}s)", flush=True)

    glms = {}
    for name, feats in GOAL_FEATURES.items():
        glms[name] = fit_glm(name, feats, data, "y_goal")
    for name, feats in CORNER_FEATURES.items():
        g = fit_glm(name, feats, data, "y_corner")
        g.dispersion = corner_dispersion(g, data)
        print(f"  corner NB alpha (remaining total corners): {g.dispersion:.4f}")
        glms[name] = g

    tr = [m for m in matches if split_of(m) == "train"]
    mu_h = float(np.mean([m["reg_home_goals"] for m in tr]))
    mu_a = float(np.mean([m["reg_away_goals"] for m in tr]))
    version = "inplay-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d")
    bundle = ModelBundle(version=version, glms=glms, refs=refs, mu_goals=mu, prior_pseudo_matches=PRIOR_K,
                         stoppage=st_modern)

    records = data["records"]
    del data
    reports = {}
    for split in ("val_temporal", "val_cross"):
        recs = [r for r in records if r.split == split]
        print(f"validating on {split}: {len(recs)} origins", flush=True)
        # stoppage distribution estimated on training-era data only (no leakage)
        reports[split] = evaluate(bundle, recs, mu_h, mu_a, st_train, ["goals_context", "goals_stats", "goals_xg"])

    margins = family_margins(reports, "goals_stats")
    bundle.validation = {"reports": reports, "family_margins": margins,
                         "splits": counts, "temporal_split_date": "2016-03-01"}
    bundle.meta = {
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "data_source": "StatsBomb Open Data (https://github.com/statsbomb/open-data)",
        "train_competitions": sorted(OLD), "train_before": "2016-03-01",
        "cross_competitions": sorted({m["competition"] for m in matches if m["role"] == "cross"}),
        "mu_home": mu_h, "mu_away": mu_a,
        "stoppage_note": "coefficients fitted on 2015/16; stoppage-time distribution for live use estimated "
                         "from 2020-2024 competitions (longer added time).",
    }
    bundle.save(DEFAULT_MODEL_PATH)
    print(f"saved {DEFAULT_MODEL_PATH} ({time.time() - t0:.0f}s)")
    summary = {s: {t: {m: round(v[m]["logloss"], 4) for m in ("baseline", "goals_context", "goals_stats", "goals_xg")}
                   for t, v in rep["binary"].items()} for s, rep in reports.items()}
    print(json.dumps(summary, indent=1))
    print(json.dumps({s: rep["multiclass"] for s, rep in reports.items()}, indent=1))
    print("margins", margins)
    return 0


if __name__ == "__main__":
    sys.exit(main())
