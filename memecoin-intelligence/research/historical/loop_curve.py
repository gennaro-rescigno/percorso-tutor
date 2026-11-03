"""Study 'loop_curve': what happens to pump.fun launches, and is any simple curve entry rule positive after costs?

Data: loopholetape/pumpfun-launches (CC BY 4.0), subset `launches` (2026-09-27 .. 2026-10-27, complete decoder)
and config `features` (the API's per-minute state of each launch joined to its outcome), plus `launches_legacy`
(2026-08-31 .. 2026-09-26) for the stability check of launch-level facts.

PRE-REGISTERED (written before looking at any result; do not tune after reading the output):
  * universe: classic launches only (quoted in SOL, not mayhem), outcome settled, row before migration, not a
    repaired row, recorder lag <= 10 s (or unknown), decoder complete;
  * one trade per mint: the first row (the bot scans once a minute) that meets the rule;
  * price on the curve from the real SOL reserve: virtual SOL = 30 + real, price ~ (30 + real)^2 (constant
    product with 30 SOL virtual, verified on our own chain fixtures);
  * costs: entry price 3% worse than the row (latency), pump.fun fee 1.25% on buy and on sell, 0.001 SOL priority
    fees per round trip on a 0.1 SOL position (1%); a graduation exit sells in the new pool with a haircut H
    (base 30%, sensitivity 10% and 50%);
  * exits: X1 hold until graduation (sell in the pool, haircut H) or until the curve dies (sell at the terminal
    reserve); X2 take profit on the curve at 60 SOL of real reserve (if the curve's peak reached it), otherwise
    as X1 for a dead curve;
  * statistics: mean net return per trade with a 95% bootstrap interval (resampling mints), p-value of mean <= 0,
    Benjamini-Hochberg over all strategy x exit tests; the verdict needs BOTH halves of the period positive;
  * known approximation (stated in the report): X2 uses the peak of the whole path, so a peak reached before the
    entry row would count as hit; measured as the share of entries whose own earlier rows already exceeded 60.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

from common import LOOP, Report, download_prefix

V0 = 30.0          # SOL, virtual reserve of a fresh curve
GRAD_RS = 85.0     # SOL, real reserve at completion
FEE = 0.0125       # pump.fun curve fee per side
LAT = 0.03         # entry price penalty (latency)
PRIO = 0.01        # priority fees per round trip as a share of a 0.1 SOL position
TP_RS = 60.0       # X2 take-profit reserve
HAIRCUTS = (0.10, 0.30, 0.50)
BOOT = 2000
RNG = np.random.default_rng(20261103)
SPLIT_T = pd.Timestamp("2026-10-12", tz="UTC").timestamp()

FEATURE_COLS = [
    "mint", "t", "age_s", "flag_creator_sold", "flag_bundle_dumped", "flag_curve_drained",
    "flag_serial_rugger_creator", "flag_warm_launch", "f_dev_share", "f_insider_share", "f_bundle_wallets",
    "f_rep_n", "f_rep_rug", "f_rep_grad", "f_rs", "f_n_buys", "capture_lag_s", "repaired", "outcome_status",
    "launch_t0", "launch_mayhem", "launch_quote_asset", "launch_decoder_complete", "graduated", "rugged",
    "peak_rs", "terminal_rs", "migrated_before_row",
]


# ----------------------------------------------------------------------------------------------- returns
def price_ratio(rs_in, rs_out):
    return ((V0 + np.asarray(rs_out, float)) / (V0 + np.asarray(rs_in, float))) ** 2


def net_return(rs_in, rs_out, haircut=0.0):
    gross = price_ratio(rs_in, rs_out) * (1.0 - np.asarray(haircut, float))
    return gross / (1.0 + LAT) * (1.0 - FEE) ** 2 - PRIO - 1.0


def exit_returns(df: pd.DataFrame, exit_kind: str, haircut: float) -> np.ndarray:
    rs_in = df["f_rs"].to_numpy(float)
    term = np.clip(df["terminal_rs"].fillna(0).to_numpy(float), 0, GRAD_RS)
    peak = np.clip(df["peak_rs"].fillna(0).to_numpy(float), 0, GRAD_RS)
    grad = df["graduated"].fillna(0).to_numpy(int) == 1
    dead = net_return(rs_in, term)
    at_grad = net_return(rs_in, GRAD_RS, haircut)
    if exit_kind == "X1":
        return np.where(grad, at_grad, dead)
    tp_hit = (peak >= TP_RS) & (rs_in < TP_RS)
    return np.where(tp_hit, net_return(rs_in, TP_RS), np.where(grad, at_grad, dead))


# ----------------------------------------------------------------------------------------------- stats
def boot_mean(x: np.ndarray, reps: int = BOOT) -> tuple[float, float, float]:
    """95% interval of the mean and the one-sided p-value of mean <= 0 (resampling trades = mints)."""
    if len(x) < 30:
        return float("nan"), float("nan"), float("nan")
    idx = RNG.integers(0, len(x), size=(reps, len(x))) if len(x) <= 20000 else None
    if idx is not None:
        means = x[idx].mean(axis=1)
    else:  # large samples: normal approximation is accurate and cheap
        se = x.std(ddof=1) / np.sqrt(len(x))
        means = RNG.normal(x.mean(), se, reps)
    lo, hi = np.percentile(means, [2.5, 97.5])
    p = float((means <= 0).mean())
    return float(lo), float(hi), max(p, 1.0 / reps)


def bh(pvals: list[float]) -> list[float]:
    p = np.asarray(pvals, float)
    n = len(p)
    order = np.argsort(p)
    q = np.empty(n)
    prev = 1.0
    for rank, i in enumerate(order[::-1]):
        k = n - rank
        prev = min(prev, p[i] * n / k)
        q[i] = prev
    return q.tolist()


def summarize(ret: np.ndarray, grad: np.ndarray) -> dict:
    lo, hi, p = boot_mean(ret)
    return {"n": len(ret), "media_%": 100 * ret.mean() if len(ret) else np.nan,
            "IC95_basso_%": 100 * lo, "IC95_alto_%": 100 * hi, "p": p,
            "mediana_%": 100 * np.median(ret) if len(ret) else np.nan,
            "vincenti_%": 100 * (ret > 0).mean() if len(ret) else np.nan,
            "diplomati_%": 100 * grad.mean() if len(grad) else np.nan}


# ----------------------------------------------------------------------------------------------- rules
def no_flags(d: pd.DataFrame) -> pd.Series:
    f = (d["flag_creator_sold"].fillna(False) | d["flag_bundle_dumped"].fillna(False)
         | d["flag_curve_drained"].fillna(False) | d["flag_serial_rugger_creator"].fillna(False))
    return ~f.astype(bool)


RULES = {
    "S0 qualsiasi riga < 5 min": lambda d: (d.age_s < 300),
    "S1 1-2 min, riserva 0.5-10, senza segnali negativi": lambda d: (d.age_s >= 60) & (d.age_s < 120)
        & (d.f_rs >= 0.5) & (d.f_rs < 10) & no_flags(d),
    "S2 2-5 min, riserva 0.5-10, senza segnali negativi": lambda d: (d.age_s >= 120) & (d.age_s < 300)
        & (d.f_rs >= 0.5) & (d.f_rs < 10) & no_flags(d),
    "S3 30 s-5 min, >= 20 acquisti, riserva < 10, senza segnali": lambda d: (d.age_s >= 30) & (d.age_s < 300)
        & (d.f_n_buys >= 20) & (d.f_rs < 10) & no_flags(d),
    "S4 S3 + il creatore detiene ancora >= 1%": lambda d: RULES["S3 30 s-5 min, >= 20 acquisti, riserva < 10, senza segnali"](d)
        & (d.f_dev_share >= 0.01),
    "S5 S3 + creatore con un diploma precedente": lambda d: RULES["S3 30 s-5 min, >= 20 acquisti, riserva < 10, senza segnali"](d)
        & (d.f_rep_grad > 0),
    "S6 S3 + insider < 10% e <= 2 wallet bundle": lambda d: RULES["S3 30 s-5 min, >= 20 acquisti, riserva < 10, senza segnali"](d)
        & (d.f_insider_share < 0.10) & (d.f_bundle_wallets <= 2),
}


def first_rows(d: pd.DataFrame, mask: pd.Series) -> pd.DataFrame:
    sel = d[mask.fillna(False).astype(bool)]
    return sel.sort_values("t").drop_duplicates("mint", keep="first")


# ----------------------------------------------------------------------------------------------- load
def load_features() -> pd.DataFrame:
    import pyarrow.parquet as pq
    frames = []
    for p in download_prefix(LOOP, "data/features/"):
        names = pq.ParquetFile(p).schema_arrow.names
        frames.append(pq.read_table(p, columns=[c for c in FEATURE_COLS if c in names]).to_pandas())
    return pd.concat(frames, ignore_index=True)


def universe(f: pd.DataFrame) -> pd.DataFrame:
    keep = ((f.launch_quote_asset == "sol") & (f.launch_mayhem == 0) & (f.outcome_status == "settled")
            & (f.migrated_before_row == 0) & ~f.repaired.fillna(False).astype(bool)
            & (f.capture_lag_s.isna() | (f.capture_lag_s <= 10)) & (f.launch_decoder_complete == 1)
            & f.f_rs.notna() & (f.f_rs >= 0) & (f.f_rs < GRAD_RS))
    u = f[keep].copy()
    u["age_s"] = u["age_s"].clip(lower=0)
    return u


LAUNCH_COLS = ["mint", "creator", "t0", "name", "uri", "mayhem", "quote_asset", "dev_buy_sol", "dev_share",
               "graduated", "migrate_dt_s", "rugged", "rug_dt_s", "dev_first_sell_dt_s", "peak_rs", "terminal_rs",
               "f10_bundle_wallets", "f10_rep_n", "f10_rep_grad", "f10_insider_share"]


def load_launches(subset: str) -> pd.DataFrame:
    import pyarrow.parquet as pq
    frames = []
    for p in download_prefix(LOOP, f"data/{subset}/"):
        names = pq.ParquetFile(p).schema_arrow.names
        frames.append(pq.read_table(p, columns=[c for c in LAUNCH_COLS if c in names]).to_pandas())
    return pd.concat(frames, ignore_index=True)


# ----------------------------------------------------------------------------------------------- facts
def norm_name(s: pd.Series) -> pd.Series:
    return s.fillna("").str.lower().map(lambda x: re.sub(r"[^a-z0-9]", "", x))


def uri_kind(s: pd.Series) -> pd.Series:
    s = s.fillna("").str.lower()
    return np.select([s == "", s.str.contains("ipfs"), s.str.contains("arweave|irys"), s.str.startswith("http")],
                     ["nessuno", "ipfs", "arweave", "altro http"], default="altro")


def rate_table(df: pd.DataFrame, by: pd.Series, label: str) -> pd.DataFrame:
    g = df.groupby(by, observed=True)
    out = pd.DataFrame({
        label: g.size().index.astype(str),
        "lanci": g.size().values,
        "diploma_%": (100 * g["graduated"].mean()).values,
        "rug_%": (100 * g["rugged"].mean()).values,
        "creatore_vende_<60s_%": (100 * g["dev_sell_60"].mean()).values,
    })
    return out


def lifecycle_facts(r: Report, la: pd.DataFrame, period: str) -> None:
    c = la[(la.quote_asset == "sol") & (la.mayhem == 0)].copy()
    c["dev_sell_60"] = (c.dev_first_sell_dt_s <= 60).astype(float)
    r(f"\n### {period}: {len(c):,} lanci classici (SOL, non mayhem)")
    r(f"- diplomati: {100 * c.graduated.mean():.2f}% · rug (regola loopholetape, sui risolti): "
      f"{100 * c.rugged.mean():.1f}% · rug entro 5 min: {100 * ((c.rugged == 1) & (c.rug_dt_s <= 300)).mean():.1f}%")
    q = c.dev_first_sell_dt_s.dropna()
    r(f"- il creatore vende: {100 * c.dev_first_sell_dt_s.notna().mean():.1f}% dei lanci; tempo mediano alla prima "
      f"vendita {q.median():.0f} s (25° {q.quantile(.25):.0f} s, 75° {q.quantile(.75):.0f} s); entro 60 s nel "
      f"{100 * (q <= 60).sum() / len(c):.1f}% dei lanci")
    m = c.loc[c.graduated == 1, "migrate_dt_s"].dropna()
    if len(m):
        r(f"- tempo al diploma: mediana {m.median() / 60:.1f} min; entro 1 min {100 * (m <= 60).mean():.1f}%, "
          f"entro 10 min {100 * (m <= 600).mean():.1f}%, oltre 1 ora {100 * (m > 3600).mean():.1f}%")
    pk = c.peak_rs.dropna().clip(upper=GRAD_RS)
    r(f"- picco della curva (SOL reali): mediana {pk.median():.2f}; >= 5 SOL {100 * (pk >= 5).mean():.1f}%, "
      f">= 20 SOL {100 * (pk >= 20).mean():.1f}%, >= 60 SOL {100 * (pk >= 60).mean():.2f}%")
    r("\nPer acquisto iniziale del creatore (SOL):")
    r.table(rate_table(c, pd.cut(c.dev_buy_sol, [-0.001, 0.0001, 0.5, 1, 2, 5, 1e9],
                                labels=["0", "<0.5", "0.5-1", "1-2", "2-5", ">5"]), "acquisto_creatore"))
    c["ora"] = pd.to_datetime(c.t0, unit="s", utc=True).dt.hour // 3 * 3
    r("Per fascia oraria UTC (3 ore):")
    r.table(rate_table(c, c.ora, "ora_UTC"))
    r("Per metadati (uri):")
    r.table(rate_table(c, pd.Series(uri_kind(c.uri), index=c.index), "uri"))
    if "copy_rank" in c:
        r("Copie (stesso nome normalizzato già usato prima nel dataset):")
        r.table(rate_table(c, pd.cut(c.copy_rank, [-1, 0, 1, 5, 1e9], labels=["originale", "2a", "3a-6a", "oltre"]),
                           "copia"))
    if c.f10_bundle_wallets.notna().any():
        r("Per wallet bundle nei primi 10 s (solo lanci campionati, popolazione distorta: vedi KI-01):")
        s = c[c.f10_bundle_wallets.notna()]
        r.table(rate_table(s, pd.cut(s.f10_bundle_wallets, [-1, 0, 2, 5, 10, 1e9],
                                     labels=["0", "1-2", "3-5", "6-10", ">10"]), "bundle"))
        r("Per storico del creatore (lanci precedenti):")
        r.table(rate_table(s, pd.cut(s.f10_rep_n, [-1, 0, 5, 50, 1e9], labels=["primo", "1-5", "6-50", ">50"]),
                           "lanci_precedenti"))


# ----------------------------------------------------------------------------------------------- main
def main() -> None:
    r = Report("loop_curve")
    r("# Studio storico: ciclo di vita dei lanci e regole d'ingresso sulla curva (loopholetape, set-ott 2026)")
    r("\nPre-registrazione (scritta prima di vedere i risultati, testo originale):\n\n```\n"
      + __doc__.split("PRE-REGISTERED")[1].strip() + "\n```")

    # ---- part 1: lifecycle facts
    r("\n## 1. Cosa succede ai lanci")
    leg = load_launches("launches_legacy")
    new = load_launches("launches")
    allx = pd.concat([leg, new], ignore_index=True).sort_values("t0")
    allx["nn"] = norm_name(allx["name"])
    allx["copy_rank"] = allx.groupby("nn").cumcount()
    allx.loc[allx.nn == "", "copy_rank"] = np.nan
    ranks = allx.drop_duplicates("mint").set_index("mint")["copy_rank"]
    for df, label in ((leg, "31 ago - 26 set (decoder incompleto: acquisti sottostimati)"),
                      (new, "27 set - 27 ott (decoder completo)")):
        df["copy_rank"] = df["mint"].map(ranks)
        lifecycle_facts(r, df, label)
    del leg, allx

    # ---- part 2: curve entry rules
    r("\n## 2. Regole d'ingresso sulla curva (una operazione per token, costi inclusi)")
    f = universe(load_features())
    r(f"Righe utilizzabili: {len(f):,} (istantanee al minuto) di {f.mint.nunique():,} token classici.")
    rows, pvals = [], []
    for name, rule in RULES.items():
        e = first_rows(f, rule(f))
        if e.empty:
            continue
        grad = (e.graduated.fillna(0) == 1).to_numpy()
        for exit_kind in ("X1", "X2"):
            for h in (HAIRCUTS if exit_kind == "X1" else (0.30,)):
                ret = exit_returns(e, exit_kind, h)
                row = {"regola": name, "uscita": exit_kind, "taglio_pool": h, **summarize(ret, grad)}
                early = e.t < SPLIT_T
                for half, m in (("1a_metà", early.to_numpy()), ("2a_metà", ~early.to_numpy())):
                    row[f"{half}_media_%"] = 100 * ret[m].mean() if m.any() else np.nan
                    row[f"{half}_n"] = int(m.sum())
                rows.append(row)
                pvals.append(row["p"])
    res = pd.DataFrame(rows)
    res["q_BH"] = bh(pvals)
    res["verdetto"] = np.where((res.q_BH < 0.05) & (res["1a_metà_media_%"] > 0) & (res["2a_metà_media_%"] > 0),
                               "positiva e stabile", "non dimostrata")
    r.table(res)

    # X2 approximation check: entries whose own earlier sampled rows already exceeded the TP reserve
    f_sorted = f.sort_values("t")
    f_sorted["prior_max"] = f_sorted.groupby("mint")["f_rs"].cummax().groupby(f_sorted["mint"]).shift(1)
    e0 = first_rows(f_sorted, RULES["S3 30 s-5 min, >= 20 acquisti, riserva < 10, senza segnali"](f_sorted))
    r(f"Controllo X2 (S3): ingressi con un picco precedente già >= {TP_RS:.0f} SOL nelle righe campionate: "
      f"{100 * (e0.prior_max >= TP_RS).mean():.2f}%")

    # ---- part 3: map by age and reserve (descriptive, X1 with 30% haircut)
    r("\n## 3. Mappa descrittiva: età × riserva al momento dell'ingresso (X1, taglio 30%)")
    f["eta"] = pd.cut(f.age_s, [0, 30, 60, 120, 300, 900], right=False,
                      labels=["<30s", "30-60s", "1-2m", "2-5m", "5-15m"])
    f["riserva"] = pd.cut(f.f_rs, [0, 2, 5, 10, 20, 40, 85], right=False,
                          labels=["0-2", "2-5", "5-10", "10-20", "20-40", "40-85"])
    cells = []
    for (a, b), g in f.groupby(["eta", "riserva"], observed=True):
        e = g.sort_values("t").drop_duplicates("mint")
        if len(e) < 200:
            continue
        ret = exit_returns(e, "X1", 0.30)
        cells.append({"età": a, "riserva_SOL": b, "n": len(e), "media_%": 100 * ret.mean(),
                      "mediana_%": 100 * np.median(ret), "diplomati_%": 100 * (e.graduated == 1).mean(),
                      "pareggio_diploma_%": 100 * breakeven(e)})
    r.table(pd.DataFrame(cells))
    r("`pareggio_diploma_%` = quota di diplomi necessaria per andare in pari in quella cella (con i costi).")
    r.save()


def breakeven(e: pd.DataFrame) -> float:
    """Share of graduations at which X1 (30% haircut) breaks even, given the cell's entry reserves and floors."""
    dead = e[e.graduated.fillna(0) != 1]
    if dead.empty:
        return float("nan")
    win = net_return(e.f_rs, GRAD_RS, 0.30).mean()
    lose = net_return(dead.f_rs, np.clip(dead.terminal_rs.fillna(0), 0, GRAD_RS)).mean()
    return float(-lose / (win - lose)) if win > lose else float("nan")


if __name__ == "__main__":
    main()
