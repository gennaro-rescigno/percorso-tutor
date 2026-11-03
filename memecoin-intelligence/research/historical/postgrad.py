"""Study 'postgrad': what happens after the graduation to PumpSwap, and does any simple entry win after costs?

Data: jocry/Pumpfun_Memecoin_Corpus (MIT, 2026-06-05 .. 07-14: 5,669 graduated tokens with prices at fixed
delays after the graduation and pool snapshots about every 5 minutes for 2 days) and
loopholetape/pumpfun-launches `graduation_pools` (CC BY 4.0, 2026-09-23 .. 10-27: first 30 minutes of 39,967 pools).

PRE-REGISTERED (written before looking at any result):
  * entries at a fixed delay after the graduation: 1, 5, 10 and 30 minutes (jocry `price_at_*m_usd`);
  * exits: 1, 6 and 24 hours after the ENTRY, at the first pool snapshot at or after that moment; a token with no
    snapshot that late is closed at its last snapshot (the pool stopped trading or the collector stopped);
  * filters: P0 all graduates; P1 organic graduation (>= 5 minutes on the curve); P2 survived the first dump
    (price at 10 min >= 50% of the graduation price, entries at 10 and 30 min only); P3 dip buy (price at 10 min
    <= 20% of the graduation price, entries at 10 and 30 min only);
  * costs: entry 3% worse than the snapshot (latency), pool fee 0.3% per side, priority fees 1% per round trip;
  * statistics as in loop_curve: bootstrap 95% interval of the mean, Benjamini-Hochberg over all tests, verdict
    "positive and stable" only with q < 0.05 and both halves of the period positive (split on 2026-06-25).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from common import JOCRY, LOOP, Report, download
from loop_curve import bh, boot_mean

LAT, POOL_FEE, PRIO = 0.03, 0.003, 0.01
SPLIT = pd.Timestamp("2026-06-25", tz="UTC")
ENTRIES = {1: "price_at_1m_usd", 5: "price_at_5m_usd", 10: "price_at_10m_usd", 30: "price_at_30m_usd"}
HOLDS_H = (1, 6, 24)


def net(ratio):
    return np.asarray(ratio, float) / (1 + LAT) * (1 - POOL_FEE) ** 2 - PRIO - 1


def exit_prices(snaps: pd.DataFrame, targets: pd.DataFrame) -> pd.Series:
    """For each (mint, t_exit) the first snapshot price at or after t_exit, else the last snapshot price."""
    snaps = snaps.sort_values(["mint", "seconds_since_graduation"])
    out = {}
    groups = {m: g for m, g in snaps.groupby("mint")}
    for idx, (mint, t_exit) in targets[["mint", "t_exit"]].iterrows():
        g = groups.get(mint)
        if g is None or g.empty:
            out[idx] = np.nan
            continue
        ts = g["seconds_since_graduation"].to_numpy()
        pos = np.searchsorted(ts, t_exit, side="left")
        row = g.iloc[pos] if pos < len(g) else g.iloc[-1]
        out[idx] = row["price_usd"] if row["price_usd"] and row["price_usd"] > 0 else np.nan
    return pd.Series(out)


def part_jocry(r: Report) -> None:
    out = pd.read_parquet(download(JOCRY, "postgard_outcomes.parquet"))
    mig = pd.read_parquet(download(JOCRY, "migrations.parquet"))
    snaps = pd.read_parquet(download(JOCRY, "postgard_snapshots.parquet"),
                            columns=["mint", "seconds_since_graduation", "price_usd", "liquidity_usd"])
    snaps = snaps[snaps.price_usd.notna() & (snaps.price_usd > 0)]
    df = out.merge(mig[["mint", "migrated_at", "seconds_to_graduation"]].drop_duplicates("mint"), on="mint", how="left")
    df = df[df.price_at_grad_usd.notna() & (df.price_at_grad_usd > 0)]
    r(f"\n## 1. Dopo il diploma (giugno-luglio 2026, jocry): {len(df):,} token diplomati con prezzo al diploma")
    for m, col in ENTRIES.items():
        x = (df[col] / df.price_at_grad_usd).dropna()
        r(f"- prezzo a {m} min dal diploma rispetto al diploma: mediana ×{x.median():.2f}; sotto ×0,5 nel "
          f"{100 * (x < 0.5).mean():.1f}%; sotto ×0,2 nel {100 * (x < 0.2).mean():.1f}%; sopra ×2 nel {100 * (x > 2).mean():.1f}%")
    pk = (df.peak_price_usd / df.price_at_grad_usd).dropna()
    r(f"- massimo dopo il diploma: mediana ×{pk.median():.2f}; almeno ×2 nel {100 * (pk >= 2).mean():.1f}%; "
      f"almeno ×10 nel {100 * (pk >= 10).mean():.1f}%")
    r(f"- ancora liquidi dopo 24 h: {100 * df.still_liquid_at_24h.mean():.1f}%; rug segnalato: {100 * df.rug_detected.mean():.1f}%")
    r("- esiti (etichette del dataset): " + ", ".join(f"{k} {v}" for k, v in df.outcome_label.value_counts().items()))
    r(f"- copertura istantanee: mediana {snaps.groupby('mint').size().median():.0f} istantanee per token")

    filters = {
        "P0 tutti": lambda d, m: pd.Series(True, index=d.index),
        "P1 diploma organico (>= 5 min sulla curva)": lambda d, m: d.seconds_to_graduation >= 300,
        "P2 ha retto il primo crollo (a 10 min >= 50% del diploma)":
            lambda d, m: (m >= 10) & (d.price_at_10m_usd >= 0.5 * d.price_at_grad_usd),
        "P3 compra il crollo (a 10 min <= 20% del diploma)":
            lambda d, m: (m >= 10) & (d.price_at_10m_usd <= 0.2 * d.price_at_grad_usd),
    }
    rows, pvals = [], []
    for fname, f in filters.items():
        for m, col in ENTRIES.items():
            sel = df[f(df, m).fillna(False) & df[col].notna() & (df[col] > 0)].copy()
            if len(sel) < 30:
                continue
            for h in HOLDS_H:
                sel["t_exit"] = m * 60 + h * 3600
                px = exit_prices(snaps[snaps.mint.isin(sel.mint)], sel)
                ok = px.notna()
                ret = pd.Series(net(px[ok] / sel.loc[ok.index[ok], col]), index=ok.index[ok])
                lo, hi, p = boot_mean(ret.to_numpy())
                early = sel.loc[ok.index[ok], "migrated_at"] < SPLIT
                rows.append({"filtro": fname, "ingresso_min": m, "tenuta_h": h, "n": int(ok.sum()),
                             "media_%": 100 * ret.mean(), "IC95_basso_%": 100 * lo, "IC95_alto_%": 100 * hi, "p": p,
                             "mediana_%": 100 * ret.median(), "vincenti_%": 100 * (ret > 0).mean(),
                             "1a_metà_%": 100 * ret[early.to_numpy()].mean() if early.any() else np.nan,
                             "2a_metà_%": 100 * ret[~early.to_numpy()].mean() if (~early).any() else np.nan})
                pvals.append(p)
    res = pd.DataFrame(rows)
    res["q_BH"] = bh(pvals)
    res["verdetto"] = np.where((res.q_BH < 0.05) & (res["1a_metà_%"] > 0) & (res["2a_metà_%"] > 0),
                               "positiva e stabile", "non dimostrata")
    r("\n### Entrate dopo il diploma (costi inclusi, una operazione per token)")
    r.table(res)


def part_loop(r: Report) -> None:
    p = download(LOOP, "data/graduation_pools/graduation_pools.parquet")
    g = pd.read_parquet(p)
    full = g[(g.complete == 1) & (g.n_trades >= 5) & (g.open_reserve_lam >= 50e9)]
    x = full.price_ratio_30m
    r(f"\n## 2. Primi 30 minuti dei pool (settembre-ottobre 2026, loopholetape): {len(full):,} pool completi")
    r(f"- prezzo dopo 30 min rispetto al primo scambio nel pool: mediana ×{x.median():.3f}; <= ×0,1 nel "
      f"{100 * (x <= 0.1).mean():.1f}%; >= ×1 nel {100 * (x >= 1).mean():.1f}%; >= ×2 nel {100 * (x >= 2).mean():.1f}%")
    c = full.collapsed_t.dropna()
    r(f"- crollo a un decimo del prezzo iniziale: {100 * len(c) / len(full):.1f}% dei pool, tempo mediano {c.median():.0f} s")
    ret = net(x.to_numpy())
    lo, hi, pv = boot_mean(ret)
    r(f"- comprare al primo scambio e vendere dopo 30 minuti (costi inclusi): media {100 * ret.mean():.1f}% "
      f"[{100 * lo:.1f}%, {100 * hi:.1f}%], vincenti {100 * (ret > 0).mean():.1f}%")


def main() -> None:
    r = Report("postgrad")
    r("# Studio storico: cosa succede dopo il diploma e le entrate su PumpSwap")
    r("\nPre-registrazione (testo originale):\n\n```\n" + __doc__.split("PRE-REGISTERED")[1].strip() + "\n```")
    part_loop(r)
    part_jocry(r)
    r.save()


if __name__ == "__main__":
    main()
