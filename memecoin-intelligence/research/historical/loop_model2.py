"""Study 'loop_model2': the loop_model result checked for survivorship and for the graduation assumption.

loop_model found the 10-minute selections positive (+22% to +92% per trade). Before believing it, three checks
written BEFORE running them:
  * survivorship: in loop_model a decision without a sampled row 10 minutes later was DROPPED (about two thirds of
    the tokens at 10 minutes); here it is kept and valued at the token's final reserve (`terminal_rs`), which for
    a dead curve is close to its price at that time (conservative: never better than the truth for a dying token);
  * graduation: an exit at the graduation price minus 30% (as before) and minus 50%;
  * a single clean split: trained on the first half of the days, judged only on the second half (no retraining);
  * what the model looks at: permutation importance on the test half.
Everything else (features, model, costs, selections, statistics) as in loop_model.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import loop_model as lm
from common import Report
from loop_curve import GRAD_RS, bh, boot_mean, net_return

HAIRCUTS = (0.30, 0.50)


def targets(f: pd.DataFrame, hold: int, haircut: float) -> tuple[np.ndarray, np.ndarray]:
    left = f[["mint", "age_s", "f_rs", "graduated", "migrate_dt_s", "terminal_rs"]].copy()
    left["target"] = left.age_s + hold
    left["i"] = np.arange(len(left))
    right = f[["mint", "age_s", "f_rs"]].rename(columns={"age_s": "x_age", "f_rs": "x_rs"}).sort_values("x_age")
    m = pd.merge_asof(left.sort_values("target"), right, left_on="target", right_on="x_age", by="mint",
                      direction="forward").sort_values("i")
    grad = ((m.graduated.fillna(0) == 1) & (m.migrate_dt_s.fillna(np.inf) <= m.target)).to_numpy()
    term = np.clip(m.terminal_rs.fillna(0).to_numpy(), 0, GRAD_RS)
    kind = np.where(grad, "diploma", np.where(m.x_rs.notna(), "riga", "finale"))
    out = np.where(grad, net_return(m.f_rs, GRAD_RS, haircut),
                   np.where(m.x_rs.notna(), net_return(m.f_rs, m.x_rs.fillna(0)), net_return(m.f_rs, term)))
    return out, kind


def main() -> None:
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.inspection import permutation_importance

    r = Report("loop_model2")
    r("# Verifica del modello a 10 minuti: sopravvissuti, ipotesi sul diploma, divisione netta (loopholetape)")
    r("\n```\n" + __doc__.split("\n\n", 1)[1].strip() + "\n```")
    f = lm.build()
    d_all = f[(f.age_s >= 60) & (f.age_s < 300)].copy()
    days = sorted(d_all.day.unique())
    half = days[len(days) // 2]
    rows = []
    for hold in (300, 600):
        for h in HAIRCUTS:
            y, kind = targets(f, hold, h)
            f["y"], f["kind"] = y, kind
            d = f[(f.age_s >= 60) & (f.age_s < 300)].copy()
            tr, te = d[d.day < half], d[d.day >= half].copy()
            model = HistGradientBoostingRegressor(max_iter=200, learning_rate=0.05, max_leaf_nodes=31,
                                                  min_samples_leaf=200, l2_regularization=1.0, random_state=0)
            model.fit(tr[lm.FEATS], tr.y.clip(-1, 2))
            p_tr = model.predict(tr[lm.FEATS])
            te["pred"] = model.predict(te[lm.FEATS])
            sels = {"P0 ogni token": te.pred > -np.inf, "P1 previsto > 0": te.pred > 0,
                    "P2 5% più alto": te.pred >= np.quantile(p_tr, 0.95),
                    "P3 1% più alto": te.pred >= np.quantile(p_tr, 0.99)}
            for name, m in sels.items():
                pick = te[m].sort_values("t").drop_duplicates(["mint", "day"])
                if len(pick) < 30:
                    continue
                x = pick.y.to_numpy()
                lo, hi, p = boot_mean(x)
                share = pick.kind.value_counts(normalize=True)
                rows.append({"tenuta_min": hold // 60, "taglio_diploma": h, "selezione": name, "n": len(x),
                             "media_%": 100 * x.mean(), "IC95_basso_%": 100 * lo, "IC95_alto_%": 100 * hi, "p": p,
                             "mediana_%": 100 * np.median(x), "vincenti_%": 100 * (x > 0).mean(),
                             "uscite_diploma_%": 100 * share.get("diploma", 0),
                             "uscite_valore_finale_%": 100 * share.get("finale", 0)})
            if hold == 600 and h == 0.30:
                sample = te.sample(min(len(te), 60_000), random_state=0)
                imp = permutation_importance(model, sample[lm.FEATS], sample.y.clip(-1, 2), n_repeats=3,
                                             random_state=0, n_jobs=1)
                order = np.argsort(-imp.importances_mean)
                r("\n## Cosa guarda il modello (10 minuti, importanza per permutazione sulla seconda metà)")
                r.table(pd.DataFrame({"caratteristica": [lm.FEATS[i] for i in order[:12]],
                                      "importanza": imp.importances_mean[order[:12]]}))
                top = te[te.pred >= np.quantile(p_tr, 0.99)]
                r("Profilo dei momenti scelti (1% più alto) rispetto a tutti (mediane):")
                prof = pd.DataFrame({"caratteristica": lm.FEATS,
                                     "scelti": [top[c].median() for c in lm.FEATS],
                                     "tutti": [te[c].median() for c in lm.FEATS]})
                r.table(prof)
    tab = pd.DataFrame(rows)
    tab["q_BH"] = bh(tab.p.tolist())
    tab["verdetto"] = np.where((tab.q_BH < 0.05) & (tab["IC95_basso_%"] > 0), "positiva", "non dimostrata")
    r("\n## Risultati sulla seconda metà dei giorni (mai vista dal modello)")
    r.table(tab)
    r.save()


if __name__ == "__main__":
    main()
