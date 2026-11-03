"""Study 'loop_model': can a model learn WHEN to enter a pump.fun curve for a 5-10 minute trade?

Data: loopholetape/pumpfun-launches (CC BY 4.0), config `features` (the per-minute state of each launch) and
subset `launches` (2026-09-27 .. 10-27), same universe and price as loop_curve / loop_short.

PRE-REGISTERED (written before looking at any result):
  * decision points: every sampled minute between 1 and 5 minutes of age of every classic launch;
  * features known at that moment only: age, real SOL reserve and its change since the previous minute, distance
    from the highest reserve so far, buys so far and their change, buys and reserve per minute, creator share,
    insider share, block-0 bundle wallets, creator history (launches, rug and graduation rates), the observed flags
    (creator sold, bundle dumped, curve drained, serial rugger, warm launch), creator's first buy, how many earlier
    launches used the same name, hour of the day (UTC). The API's own served probabilities are NOT used;
  * targets: net return of a 0.1 SOL trade held 5 and 10 minutes (exit at the first sampled row at least that much
    later; a graduation in between exits at the graduation price minus 30%), with the costs of loop_curve
    (3% latency, 1.25% fee per side, 1% priority fees);
  * model: gradient-boosted trees (scikit-learn HistGradientBoostingRegressor, fixed settings), target clipped to
    [-100%, +200%]; walk-forward: trained only on days before the tested ones (first 7 days only for training),
    retrained every 3 days;
  * selections, one trade per token per day (its first selected minute): P0 every token (reference),
    P1 predicted net return > 0, P2 prediction in the top 5% of the training predictions, P3 top 1%;
  * statistics: bootstrap 95% interval of the mean, Benjamini-Hochberg over all tests, verdict "positive and stable"
    only with q < 0.05 and both halves of the tested days positive.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from common import Report
from loop_curve import GRAD_RS, bh, boot_mean, load_features, load_launches, net_return, norm_name, universe
from loop_short import prepare

HOLDS = (300, 600)
FEATS = ["age_s", "f_rs", "d_rs", "r_rs", "dd", "prior_max", "f_n_buys", "d_buys", "buys_per_min", "rs_per_min",
         "f_dev_share", "f_insider_share", "f_bundle_wallets", "f_rep_n", "f_rep_rug", "f_rep_grad",
         "flag_creator_sold", "flag_bundle_dumped", "flag_curve_drained", "flag_serial_rugger_creator",
         "flag_warm_launch", "dev_buy_sol", "copy_rank", "hour"]
TRAIN_DAYS, STEP_DAYS = 7, 3


def build() -> pd.DataFrame:
    f = prepare(universe(load_features()))
    la = pd.concat([load_launches("launches_legacy"), load_launches("launches")], ignore_index=True)
    la = la.sort_values("t0").drop_duplicates("mint")
    la["nn"] = norm_name(la["name"])
    la["copy_rank"] = la.groupby("nn").cumcount()
    la.loc[la.nn == "", "copy_rank"] = np.nan
    f = f.merge(la[["mint", "dev_buy_sol", "copy_rank"]], on="mint", how="left")
    f["d_rs"] = f.f_rs - f.prev_rs
    f["r_rs"] = np.where(f.prev_rs > 0, f.f_rs / f.prev_rs - 1, np.nan)
    f["dd"] = np.where(f.prior_max > 0, 1 - f.f_rs / f.prior_max, np.nan)
    f["d_buys"] = f.f_n_buys - f.prev_buys
    minutes = (f.age_s / 60).clip(lower=0.5)
    f["buys_per_min"] = f.f_n_buys / minutes
    f["rs_per_min"] = f.f_rs / minutes
    f["hour"] = pd.to_datetime(f.t, unit="s", utc=True).dt.hour
    for c in ("flag_creator_sold", "flag_bundle_dumped", "flag_curve_drained", "flag_serial_rugger_creator",
              "flag_warm_launch"):
        f[c] = f[c].fillna(False).astype(float)
    f["day"] = (f.t // 86400).astype(int)
    for hold in HOLDS:
        f[f"y{hold}"] = targets(f, hold)
    return f


def targets(f: pd.DataFrame, hold: int) -> np.ndarray:
    left = f[["mint", "age_s", "f_rs", "graduated", "migrate_dt_s"]].copy()
    left["target"] = left.age_s + hold
    left["i"] = np.arange(len(left))
    right = f[["mint", "age_s", "f_rs"]].rename(columns={"age_s": "x_age", "f_rs": "x_rs"}).sort_values("x_age")
    m = pd.merge_asof(left.sort_values("target"), right, left_on="target", right_on="x_age", by="mint",
                      direction="forward").sort_values("i")
    grad = ((m.graduated.fillna(0) == 1) & (m.migrate_dt_s.fillna(np.inf) <= m.target)).to_numpy()
    out = np.where(grad, net_return(m.f_rs, GRAD_RS, 0.30),
                   np.where(m.x_rs.notna(), net_return(m.f_rs, m.x_rs.fillna(0)), np.nan))
    return out


def walk_forward(f: pd.DataFrame, hold: int) -> tuple[pd.DataFrame, dict]:
    from sklearn.ensemble import HistGradientBoostingRegressor

    d = f[(f.age_s >= 60) & (f.age_s < 300) & f[f"y{hold}"].notna()].copy()
    days = sorted(d.day.unique())
    preds, diag = [], {"spearman": []}
    for k in range(TRAIN_DAYS, len(days), STEP_DAYS):
        test_days = days[k:k + STEP_DAYS]
        tr = d[d.day < test_days[0]]
        te = d[d.day.isin(test_days)].copy()
        if tr.empty or te.empty:
            continue
        y = tr[f"y{hold}"].clip(-1, 2)
        model = HistGradientBoostingRegressor(max_iter=200, learning_rate=0.05, max_leaf_nodes=31,
                                              min_samples_leaf=200, l2_regularization=1.0, random_state=0)
        model.fit(tr[FEATS], y)
        p_tr = model.predict(tr[FEATS])
        te["pred"] = model.predict(te[FEATS])
        te["q95"], te["q99"] = np.quantile(p_tr, 0.95), np.quantile(p_tr, 0.99)
        diag["spearman"].append(pd.Series(te.pred).rank().corr(pd.Series(te[f"y{hold}"]).rank()))
        preds.append(te)
    return (pd.concat(preds) if preds else pd.DataFrame()), diag


SELECTIONS = {
    "P0 ogni token (riferimento)": lambda t: pd.Series(True, index=t.index),
    "P1 rendimento previsto > 0": lambda t: t.pred > 0,
    "P2 previsione nel 5% più alto": lambda t: t.pred >= t.q95,
    "P3 previsione nell'1% più alto": lambda t: t.pred >= t.q99,
}


def main() -> None:
    r = Report("loop_model")
    r("# Studio storico: un modello impara quando entrare per 5-10 minuti? (loopholetape, set-ott 2026)")
    r("\nPre-registrazione (testo originale):\n\n```\n" + __doc__.split("PRE-REGISTERED")[1].strip() + "\n```")
    f = build()
    r(f"Momenti di decisione (1-5 minuti di vita): {((f.age_s >= 60) & (f.age_s < 300)).sum():,} "
      f"di {f.mint.nunique():,} token.")
    rows = []
    for hold in HOLDS:
        te, diag = walk_forward(f, hold)
        if te.empty:
            continue
        sp = np.nanmean(diag["spearman"]) if diag["spearman"] else float("nan")
        r(f"- tenuta {hold // 60} min: correlazione di rango media tra previsione e risultato fuori campione = {sp:.3f} "
          f"({len(diag['spearman'])} blocchi di test)")
        tdays = sorted(te.day.unique())
        mid = tdays[len(tdays) // 2] if tdays else 0
        for name, sel in SELECTIONS.items():
            pick = te[sel(te)].sort_values("t").drop_duplicates(["mint", "day"])
            if len(pick) < 30:
                rows.append({"selezione": name, "tenuta_min": hold // 60, "n": len(pick), "p": float("nan")})
                continue
            x = pick[f"y{hold}"].to_numpy()
            lo, hi, p = boot_mean(x)
            early = (pick.day < mid).to_numpy()
            rows.append({"selezione": name, "tenuta_min": hold // 60, "n": len(x), "media_%": 100 * x.mean(),
                         "IC95_basso_%": 100 * lo, "IC95_alto_%": 100 * hi, "p": p, "mediana_%": 100 * np.median(x),
                         "vincenti_%": 100 * (x > 0).mean(), "previsto_medio_%": 100 * pick.pred.mean(),
                         "1a_metà_%": 100 * x[early].mean() if early.any() else np.nan,
                         "2a_metà_%": 100 * x[~early].mean() if (~early).any() else np.nan})
    tab = pd.DataFrame(rows)
    if not tab.empty:
        tab["q_BH"] = bh([v if v == v else 1.0 for v in tab.p.fillna(1.0)])
        ok = (tab.q_BH < 0.05) & (tab["1a_metà_%"] > 0) & (tab["2a_metà_%"] > 0) & (tab["media_%"] > 0)
        tab["verdetto"] = np.where(tab.n < 30, "troppo pochi casi", np.where(ok, "positiva e stabile", "non dimostrata"))
    r.table(tab)
    r("`previsto_medio_%` = quanto il modello si aspettava in media sulle operazioni scelte: se è molto sopra il "
      "risultato reale, il modello si illude (sovra-adattamento).")
    r.save()


if __name__ == "__main__":
    main()
