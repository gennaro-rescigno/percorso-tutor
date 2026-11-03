"""Study 'jocry_copy2': where does the edge of the best wallets go, and can a slower follower keep any of it?

Follow-up of jocry_copy (same data, same cleaning, same daily out-of-sample leader choice). That study found that
wallet results persist (rank correlation 0.22-0.68 between consecutive 3-day windows) but copying the leaders
3-10 s late loses about 6% per copy (control: -9%). These variants were written AFTER that result and BEFORE
running them; being designed on the same period, any positive one must still pass the live test.

PRE-REGISTERED variants (each also run on the random control group with the same rule):
  V0 perfect copy (delay 0: the wallet's own entry and first-sale prices): NOT feasible, measures what the delay costs;
  V1 delay 1 s, exit 1 s after the wallet's first sale (needs fast infrastructure, not ours: an upper bound);
  V2 slow leaders: leaders as before but with <= 10% of positions held under 60 s and <= 30% under 5 minutes;
     delay 3 s, exit 3 s after their first sale;
  V3 fixed exit: delay 3 s, exit 120 s after the entry whatever the wallet does;
  V4 consensus: only tokens bought by >= 2 leaders within 10 minutes; entry 3 s after the second buy, exit 3 s
     after the first sale of either, at the latest 60 minutes after the entry.
Costs, prices, statistics and verdict as in jocry_copy (fee 1.25% + 0.5% impact per side, 1% priority fees).
"""

from __future__ import annotations

import random

import duckdb
import numpy as np
import pandas as pd

import jocry_copy as base
from common import DATA, Report
from loop_curve import bh, boot_mean


def leaders(el: pd.DataFrame, slow: bool = False) -> list[str]:
    el = el.copy()
    el["t"] = base.tstat(el)
    m = (el.win / el.n >= 0.5) & (el.pnl >= 1.0) & (el.sum_ret / el.n >= 0.10)
    if slow:
        m &= (el.quick / el.n <= 0.10) & (el.mid / el.n <= 0.30)
    return el[m].nlargest(base.TOP_N, "t").w.tolist()


def window(con, lo: float, hi: float) -> pd.DataFrame:
    df = base.wallet_window(con, lo, hi)
    mid = con.execute(f"""SELECT w, sum(CASE WHEN end_ts - first_buy < 300 THEN 1 ELSE 0 END) AS mid
                          FROM pos WHERE end_ts >= {lo} AND end_ts < {hi} GROUP BY w""").df()
    return df.merge(mid, on="w", how="left")


def run_copies(con, ws: list[str], lo: float, hi: float, delay: float, exit_mode: str) -> pd.DataFrame:
    if not ws:
        return pd.DataFrame()
    con.execute("CREATE OR REPLACE TEMP TABLE chosen (w VARCHAR)")
    con.executemany("INSERT INTO chosen VALUES (?)", [(w,) for w in ws])
    if exit_mode == "fixed":
        out_expr = f"p.first_buy + {delay} + 120"
    else:
        out_expr = f"least(coalesce(p.first_sell, p.first_buy + 3600) + {delay}, p.first_buy + {delay} + 3600)"
    return con.execute(f"""
        WITH c AS (SELECT p.w, p.mint, p.first_buy + {delay} AS t_in, {out_expr} AS t_out
                   FROM pos p JOIN chosen USING (w) WHERE p.first_buy >= {lo} AND p.first_buy < {hi}),
        s AS (SELECT * FROM prices WHERE mint IN (SELECT DISTINCT mint FROM c)),
        a AS (SELECT c.*, s.px AS px_in FROM c ASOF JOIN s ON c.mint = s.mint AND c.t_in >= s.ts),
        b AS (SELECT a.*, s.px AS px_out FROM a ASOF JOIN s ON a.mint = s.mint AND a.t_out >= s.ts)
        SELECT w, mint, t_in, px_in, px_out FROM b WHERE px_in > 0 AND px_out > 0 ORDER BY t_in""").df()


def run_consensus(con, ws: list[str], lo: float, hi: float, delay: float = 3) -> pd.DataFrame:
    if len(ws) < 2:
        return pd.DataFrame()
    con.execute("CREATE OR REPLACE TEMP TABLE chosen (w VARCHAR)")
    con.executemany("INSERT INTO chosen VALUES (?)", [(w,) for w in ws])
    return con.execute(f"""
        WITH b AS (SELECT p.mint, p.first_buy, p.first_sell,
                          row_number() OVER (PARTITION BY p.mint ORDER BY p.first_buy) AS k,
                          min(p.first_buy) OVER (PARTITION BY p.mint) AS fb1
                   FROM pos p JOIN chosen USING (w) WHERE p.first_buy >= {lo} AND p.first_buy < {hi}),
        two AS (SELECT mint, first_buy AS fb2 FROM b WHERE k = 2 AND first_buy - fb1 <= 600),
        sells AS (SELECT b.mint, min(b.first_sell) AS fs FROM b JOIN two USING (mint) WHERE b.k <= 2 GROUP BY b.mint),
        c AS (SELECT two.mint, fb2 + {delay} AS t_in,
                     least(coalesce(greatest(fs, fb2) + {delay}, fb2 + 3600), fb2 + {delay} + 3600) AS t_out
              FROM two LEFT JOIN sells USING (mint)),
        s AS (SELECT * FROM prices WHERE mint IN (SELECT mint FROM c)),
        a AS (SELECT c.*, s.px AS px_in FROM c ASOF JOIN s ON c.mint = s.mint AND c.t_in >= s.ts),
        d AS (SELECT a.*, s.px AS px_out FROM a ASOF JOIN s ON a.mint = s.mint AND a.t_out >= s.ts)
        SELECT mint, t_in, px_in, px_out FROM d WHERE px_in > 0 AND px_out > 0""").df()


def main() -> None:
    r = Report("jocry_copy2")
    r("# Studio storico: dove finisce il vantaggio dei wallet migliori (jocry, giu-lug 2026)")
    r("\nPre-registrazione (testo originale):\n\n```\n" + __doc__.split("PRE-REGISTERED")[1].strip() + "\n```")
    DATA.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(base.DB)
    con.execute("SET memory_limit='5GB'; SET temp_directory='/tmp/duck'; SET preserve_insertion_order=false")
    base.build(con, r)
    t0, t1 = con.execute("SELECT min(end_ts), max(end_ts) FROM pos").fetchone()
    d0, d1 = int(t0 // 86400) + 1, int(t1 // 86400)
    res: dict[tuple[str, str], list] = {}
    for d in range(d0 + 3, d1 + 1):
        win = window(con, (d - 3) * 86400, d * 86400)
        el = win[base.eligible(win)]
        if el.empty:
            continue
        lead, slow = leaders(el), leaders(el, slow=True)
        ctrl = random.Random(d).sample(sorted(el.w), min(base.TOP_N, len(el)))
        lo, hi = d * 86400, (d + 1) * 86400
        plans = {"V0 copia perfetta (impossibile)": (0, "leader"), "V1 ritardo 1 s": (1, "leader"),
                 "V3 uscita fissa a 120 s": (3, "fixed")}
        for name, (delay, mode) in plans.items():
            for group, ws in (("migliori", lead), ("controllo", ctrl)):
                c = run_copies(con, ws, lo, hi, delay, mode)
                if not c.empty:
                    c = c.drop_duplicates("mint")
                    res.setdefault((name, group), []).append(pd.DataFrame({"day": d, "ret": base.net(c)}))
        c = run_copies(con, slow, lo, hi, 3, "leader")
        if not c.empty:
            c = c.drop_duplicates("mint")
            res.setdefault(("V2 wallet lenti, 3 s", "migliori"), []).append(pd.DataFrame({"day": d, "ret": base.net(c)}))
        for group, ws in (("migliori", lead), ("controllo", ctrl)):
            c = run_consensus(con, ws, lo, hi)
            if not c.empty:
                res.setdefault(("V4 consenso di 2 wallet", group), []).append(pd.DataFrame({"day": d, "ret": base.net(c)}))
    mid = (d0 + 3 + d1) / 2
    rows, pvals = [], []
    for (name, group), parts in sorted(res.items()):
        x = pd.concat(parts)
        lo_, hi_, p = boot_mean(x.ret.to_numpy())
        early = x.day < mid
        rows.append({"variante": name, "gruppo": group, "copie": len(x), "giorni": x.day.nunique(),
                     "media_%": 100 * x.ret.mean(), "IC95_basso_%": 100 * lo_, "IC95_alto_%": 100 * hi_, "p": p,
                     "mediana_%": 100 * x.ret.median(), "vincenti_%": 100 * (x.ret > 0).mean(),
                     "1a_metà_%": 100 * x.ret[early].mean() if early.any() else np.nan,
                     "2a_metà_%": 100 * x.ret[~early].mean() if (~early).any() else np.nan})
        pvals.append(p)
    tab = pd.DataFrame(rows)
    if not tab.empty:
        tab["q_BH"] = bh(pvals)
        ctrl = {v: m for v, g, m in zip(tab.variante, tab.gruppo, tab["media_%"]) if g == "controllo"}
        ok = ((tab.gruppo == "migliori") & (tab.q_BH < 0.05) & (tab["1a_metà_%"] > 0) & (tab["2a_metà_%"] > 0)
              & (tab["IC95_basso_%"] > tab.variante.map(ctrl).fillna(0)))
        tab["verdetto"] = np.where(ok, "positiva, stabile e sopra il controllo",
                                   np.where(tab.gruppo == "controllo", "controllo", "non dimostrata"))
    r.table(tab)
    r.save()


if __name__ == "__main__":
    main()
