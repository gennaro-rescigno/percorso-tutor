"""Study 'loop_short': short-horizon entries on the curve from the minute-by-minute path (loopholetape features).

PRE-REGISTERED (written before looking at any result):
  * universe and price as in loop_curve (classic launches, settled, decoder complete, lag <= 10 s, rows before the
    migration; price from the real SOL reserve with 30 SOL virtual);
  * entry: the first row between 1 and 5 minutes of age that meets the rule (one trade per token);
  * rules: M0 any row (reference); M1 momentum: reserve up >= 30% since the previous row and >= 3 SOL;
    M2 pullback: reserve <= 60% of the earlier maximum, which was >= 5 SOL; M3 deep pullback: <= 40% of an
    earlier maximum >= 10 SOL; M4 flow: >= 20 more buys than at the previous row; M5 pullback + flow: M2 and
    >= 10 more buys;
  * exits at a fixed time after the entry: the first row at least 60 s, 180 s or 600 s later; a token that
    graduated before that moment exits at the graduation price minus 30% (pool haircut); a token with no later
    row and no graduation is dropped and counted (the sampling stops at 15 minutes of age);
  * costs as in loop_curve (3% latency, 1.25% fee per side, 1% priority fees);
  * statistics: bootstrap 95% interval, Benjamini-Hochberg over all tests, verdict needs both halves positive.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from common import Report
from loop_curve import GRAD_RS, SPLIT_T, bh, boot_mean, load_features, net_return, universe

HOLDS = (60, 180, 600)


def prepare(f: pd.DataFrame) -> pd.DataFrame:
    f = f.sort_values(["mint", "t"]).copy()
    g = f.groupby("mint", sort=False)
    f["prev_rs"] = g["f_rs"].shift(1)
    f["prior_max"] = g["f_rs"].cummax().groupby(f["mint"]).shift(1)
    f["prev_buys"] = g["f_n_buys"].shift(1)
    return f


RULES = {
    "M0 qualsiasi riga 1-5 min": lambda d: pd.Series(True, index=d.index),
    "M1 slancio: riserva +30% dalla riga prima e >= 3 SOL": lambda d: (d.f_rs >= 1.3 * d.prev_rs) & (d.f_rs >= 3),
    "M2 ritracciamento: <= 60% di un massimo >= 5 SOL": lambda d: (d.prior_max >= 5) & (d.f_rs <= 0.6 * d.prior_max),
    "M3 ritracciamento forte: <= 40% di un massimo >= 10 SOL": lambda d: (d.prior_max >= 10) & (d.f_rs <= 0.4 * d.prior_max),
    "M4 flusso: >= 20 acquisti in più dalla riga prima": lambda d: (d.f_n_buys - d.prev_buys) >= 20,
    "M5 ritracciamento + flusso (M2 e >= 10 acquisti in più)": lambda d: (d.prior_max >= 5) & (d.f_rs <= 0.6 * d.prior_max)
        & ((d.f_n_buys - d.prev_buys) >= 10),
}


def exits(f: pd.DataFrame, entries: pd.DataFrame, hold: int) -> tuple[np.ndarray, np.ndarray, int]:
    """Net returns of the entries held `hold` seconds (first later row), graduation exit, else dropped."""
    later = f[["mint", "age_s", "f_rs"]].rename(columns={"age_s": "x_age", "f_rs": "x_rs"})
    e = entries[["mint", "age_s", "f_rs", "graduated", "migrate_dt_s", "t"]].copy()
    e["target"] = e["age_s"] + hold
    m = e[["mint", "target"]].merge(later, on="mint", how="left")
    m = m[m.x_age >= m.target].sort_values(["mint", "x_age"]).drop_duplicates("mint")
    e = e.merge(m[["mint", "x_rs"]], on="mint", how="left")
    grad_before = ((e.graduated.fillna(0) == 1) & (e.migrate_dt_s.fillna(np.inf) <= e.target)).to_numpy()
    has_row = e.x_rs.notna().to_numpy()
    ret = np.where(grad_before, net_return(e.f_rs, GRAD_RS, 0.30),
                   np.where(has_row, net_return(e.f_rs, e.x_rs.fillna(0)), np.nan))
    keep = ~np.isnan(ret)
    return ret[keep], e.t.to_numpy()[keep], int((~keep).sum())


def main() -> None:
    r = Report("loop_short")
    r("# Studio storico: entrate a breve termine sulla curva (loopholetape, 27 set - 27 ott 2026)")
    r("\nPre-registrazione (testo originale):\n\n```\n" + __doc__.split("PRE-REGISTERED")[1].strip() + "\n```")
    f = prepare(universe(load_features()))
    win = f[(f.age_s >= 60) & (f.age_s < 300)]
    r(f"Righe candidate (1-5 min): {len(win):,} di {win.mint.nunique():,} token.")
    rows, pvals = [], []
    for name, rule in RULES.items():
        e = win[rule(win).fillna(False).astype(bool)].sort_values("t").drop_duplicates("mint")
        if len(e) < 100:
            continue
        for hold in HOLDS:
            ret, ts, dropped = exits(f, e, hold)
            lo, hi, p = boot_mean(ret)
            early = ts < SPLIT_T
            rows.append({"regola": name, "uscita_s": hold, "n": len(ret), "scartati": dropped,
                         "media_%": 100 * ret.mean(), "IC95_basso_%": 100 * lo, "IC95_alto_%": 100 * hi, "p": p,
                         "mediana_%": 100 * np.median(ret), "vincenti_%": 100 * (ret > 0).mean(),
                         "1a_metà_%": 100 * ret[early].mean() if early.any() else np.nan,
                         "2a_metà_%": 100 * ret[~early].mean() if (~early).any() else np.nan})
            pvals.append(p)
    res = pd.DataFrame(rows)
    res["q_BH"] = bh(pvals)
    res["verdetto"] = np.where((res.q_BH < 0.05) & (res["1a_metà_%"] > 0) & (res["2a_metà_%"] > 0),
                               "positiva e stabile", "non dimostrata")
    r.table(res)
    r("Lordo = senza costi: per capire se il problema sono i costi o la direzione, la stessa tabella senza costi:")
    import loop_curve as lc
    saved = (lc.LAT, lc.FEE, lc.PRIO)
    lc.LAT, lc.FEE, lc.PRIO = 0.0, 0.0, 0.0
    gross = []
    for name, rule in RULES.items():
        e = win[rule(win).fillna(False).astype(bool)].sort_values("t").drop_duplicates("mint")
        if len(e) < 100:
            continue
        for hold in HOLDS:
            ret, _, _ = exits(f, e, hold)
            gross.append({"regola": name, "uscita_s": hold, "n": len(ret), "media_lorda_%": 100 * ret.mean(),
                          "mediana_lorda_%": 100 * np.median(ret)})
    lc.LAT, lc.FEE, lc.PRIO = saved
    r.table(pd.DataFrame(gross))
    r.save()


if __name__ == "__main__":
    main()
