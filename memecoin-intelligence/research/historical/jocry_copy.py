"""Study 'jocry_copy': do profitable wallets stay profitable, and does copying them a few seconds late pay?

Data: jocry/Pumpfun_Memecoin_Corpus (MIT), 33.6 million trades with the trading wallet, 2026-06-05 .. 07-14.
Cleaning as documented by the dataset (KNOWN_ISSUES): the placeholder wallet BwWK... is excluded, rows with
missing prices or with sol_amount inconsistent with token_amount x price (ratio outside 0.01-100) are dropped.
Known limit: the corpus does not hold the trades of every token (its own notes), so a wallet's record is only
the part we can see; the same rules are applied to leaders and to the control group.

PRE-REGISTERED (same rules as the live copy experiment, mci/paper_trading/copy_sim.py):
  * a position = a wallet's trades in one token; result in SOL with 1.25% fee per side; tokens not sold are valued
    at the token's last price in the corpus; sales beyond the bought tokens flag a transfer (insider); the creator's
    own trades are excluded; positions under 0.01 SOL are ignored;
  * a position is KNOWN at its end (last sale if fully sold, otherwise the token's last trade);
  * every UTC day D, leaders = top 50 by t-statistic among wallets whose positions that ended in the 3 days before D
    satisfy: >= 8 positions (<= 600), >= 50% winners, >= +1 SOL, >= +10% average, <= 50% held under 60 s,
    <= 50% entered in the first 20 s, no transfer sale, <= 50% on mayhem tokens; control = 50 random wallets with
    the same activity filters (no profit filter);
  * copies: every first buy of a token by a chosen wallet during day D; entry at the curve price `delay` seconds
    later (3 s and 10 s); exit at the price `delay` seconds after the wallet's first sale, at the latest 60 minutes
    after the entry; prices = last trade at or before the moment (the curve does not move without trades);
    costs: 1.25% fee and 0.5% own price impact per side, 0.001 SOL priority fees on 0.1 SOL;
  * persistence test (no copying): Spearman correlation of a wallet's average return between consecutive,
    non-overlapping 3-day windows, and next-window return of the previous window's top decile;
  * verdict per variant: bootstrap 95% interval above zero AND above the control, in both halves of the period.
"""

from __future__ import annotations

import os
import random

import duckdb
import numpy as np
import pandas as pd

from common import DATA, JOCRY, Report, download, hf_tree
from loop_curve import bh, boot_mean

SYSTEM = "BwWK17cbHxwWBKZkUYvzxLcNQ1YVyaFezduWbtm2de6s"
FEE, IMPACT, PRIO = 0.0125, 0.005, 0.01
DELAYS = (3, 10)
TOP_N = 50
DB = str(DATA / "jocry_copy.duckdb")


def build(con: duckdb.DuckDBPyConnection, r: Report) -> None:
    con.execute("CREATE TABLE IF NOT EXISTS positions (w VARCHAR, mint VARCHAR, buy_sol DOUBLE, buy_tok DOUBLE, "
                "sell_sol DOUBLE, sell_tok DOUBLE, first_buy DOUBLE, first_sell DOUBLE, last_sell DOUBLE, "
                "buy_age DOUBLE, n_buys BIGINT, n_sells BIGINT)")
    con.execute("CREATE TABLE IF NOT EXISTS prices (mint VARCHAR, ts DOUBLE, px DOUBLE)")
    con.execute("CREATE TABLE IF NOT EXISTS mints (mint VARCHAR, last_ts DOUBLE, last_px DOUBLE, n BIGINT)")
    shards = sorted(f["path"] for f in hf_tree(JOCRY) if f["path"].startswith("trades/") and f["path"].endswith(".parquet"))
    kept = total = 0
    for sh in shards:
        p = download(JOCRY, sh)
        total += con.execute(f"SELECT count(*) FROM read_parquet('{p}')").fetchone()[0]
        con.execute(f"""
            CREATE OR REPLACE TEMP TABLE t AS
            SELECT mint, epoch(event_time) AS ts, user_wallet AS w, is_buy, sol_amount AS sol, token_amount AS tok,
                   price_sol AS px, seconds_since_launch AS age
            FROM read_parquet('{p}')
            WHERE user_wallet IS NOT NULL AND user_wallet <> '{SYSTEM}' AND price_sol > 0 AND sol_amount > 0
              AND token_amount > 0 AND sol_amount / (token_amount * price_sol) BETWEEN 0.01 AND 100""")
        kept += con.execute("SELECT count(*) FROM t").fetchone()[0]
        con.execute("""
            INSERT INTO positions
            WITH x AS (SELECT *, min(CASE WHEN is_buy THEN ts END) OVER (PARTITION BY w, mint) AS fb FROM t)
            SELECT w, mint,
                   sum(CASE WHEN is_buy THEN sol ELSE 0 END), sum(CASE WHEN is_buy THEN tok ELSE 0 END),
                   sum(CASE WHEN NOT is_buy THEN sol ELSE 0 END), sum(CASE WHEN NOT is_buy THEN tok ELSE 0 END),
                   min(fb), min(CASE WHEN NOT is_buy AND ts >= fb THEN ts END), max(CASE WHEN NOT is_buy THEN ts END),
                   min(CASE WHEN is_buy AND ts = fb THEN age END),
                   sum(CASE WHEN is_buy THEN 1 ELSE 0 END), sum(CASE WHEN NOT is_buy THEN 1 ELSE 0 END)
            FROM x GROUP BY w, mint""")
        con.execute("INSERT INTO prices SELECT mint, ts, px FROM t")
        con.execute("INSERT INTO mints SELECT mint, max(ts), arg_max(px, ts), count(*) FROM t GROUP BY mint")
        os.remove(p)
        print(f"{sh}: fatto", flush=True)
    r(f"Operazioni nel corpus: {total:,}; usabili dopo la pulizia documentata: {kept:,} ({100 * kept / max(total, 1):.1f}%).")
    # a token's trades may span two shards: merge the partial positions and token summaries
    con.execute("""CREATE TABLE positions_m AS SELECT w, mint, sum(buy_sol) buy_sol, sum(buy_tok) buy_tok,
                   sum(sell_sol) sell_sol, sum(sell_tok) sell_tok, min(first_buy) first_buy, min(first_sell) first_sell,
                   max(last_sell) last_sell, min(buy_age) buy_age, sum(n_buys) n_buys, sum(n_sells) n_sells
                   FROM positions GROUP BY w, mint""")
    con.execute("""CREATE TABLE mints_m AS SELECT mint, max(last_ts) last_ts, arg_max(last_px, last_ts) last_px
                   FROM mints GROUP BY mint""")
    tok = download(JOCRY, "tokens.parquet")
    con.execute(f"CREATE TABLE tokens AS SELECT mint, creator, coalesce(is_mayhem_mode, false) AS mayhem "
                f"FROM read_parquet('{tok}')")
    con.execute("""
        CREATE TABLE pos AS
        SELECT *, CASE WHEN closed THEN last_sell ELSE last_ts END AS end_ts, value / cost - 1 AS ret FROM (
            SELECT p.*, m.last_ts, m.last_px, coalesce(k.mayhem, false) AS mayhem,
                   p.sell_tok >= 0.99 * p.buy_tok AS closed,
                   p.sell_tok > 1.01 * p.buy_tok AS transfer,
                   p.buy_sol * (1 + 0.0125) AS cost,
                   (p.sell_sol * least(1.0, p.buy_tok / nullif(p.sell_tok, 0)) +
                    greatest(p.buy_tok - p.sell_tok, 0) * m.last_px) * (1 - 0.0125) AS value
            FROM positions_m p JOIN mints_m m USING (mint) LEFT JOIN tokens k USING (mint)
            WHERE p.buy_tok > 0 AND p.buy_sol >= 0.01 AND (k.creator IS NULL OR p.w <> k.creator))""")
    con.execute("DROP TABLE positions; DROP TABLE mints; DROP TABLE positions_m")


def wallet_window(con, lo: float, hi: float) -> pd.DataFrame:
    return con.execute(f"""
        SELECT w, count(*) AS n, sum(CASE WHEN ret > 0 THEN 1 ELSE 0 END) AS win, sum(value - cost) AS pnl,
               sum(ret) AS sum_ret, sum(ret * ret) AS sum_ret2,
               sum(CASE WHEN end_ts - first_buy < 60 THEN 1 ELSE 0 END) AS quick,
               sum(CASE WHEN buy_age < 20 THEN 1 ELSE 0 END) AS early,
               sum(CASE WHEN transfer THEN 1 ELSE 0 END) AS transfer_sells,
               sum(CASE WHEN mayhem THEN 1 ELSE 0 END) AS mayhem
        FROM pos WHERE end_ts >= {lo} AND end_ts < {hi} GROUP BY w HAVING count(*) >= 8""").df()


def eligible(df: pd.DataFrame) -> pd.Series:
    return ((df.n >= 8) & (df.n <= 600) & (df.quick / df.n <= 0.5) & (df.early / df.n <= 0.5)
            & (df.transfer_sells == 0) & (df.mayhem / df.n <= 0.5))


def tstat(df: pd.DataFrame) -> pd.Series:
    mean = df.sum_ret / df.n
    var = (df.sum_ret2 / df.n - mean ** 2).clip(lower=1e-9) * df.n / (df.n - 1).clip(lower=1)
    return mean / np.sqrt(var / df.n)


def copies(con, wallets: list[str], lo: float, hi: float, delay: int) -> pd.DataFrame:
    if not wallets:
        return pd.DataFrame()
    con.execute("CREATE OR REPLACE TEMP TABLE chosen (w VARCHAR)")
    con.executemany("INSERT INTO chosen VALUES (?)", [(w,) for w in wallets])
    return con.execute(f"""
        WITH c AS (
            SELECT p.w, p.mint, p.first_buy + {delay} AS t_in,
                   least(coalesce(p.first_sell, p.first_buy + 3600) + {delay}, p.first_buy + {delay} + 3600) AS t_out
            FROM pos p JOIN chosen USING (w) WHERE p.first_buy >= {lo} AND p.first_buy < {hi}),
        s AS (SELECT * FROM prices WHERE mint IN (SELECT DISTINCT mint FROM c)),
        a AS (SELECT c.*, s.px AS px_in FROM c ASOF JOIN s ON c.mint = s.mint AND c.t_in >= s.ts),
        b AS (SELECT a.*, s.px AS px_out FROM a ASOF JOIN s ON a.mint = s.mint AND a.t_out >= s.ts)
        SELECT w, mint, t_in, px_in, px_out FROM b WHERE px_in > 0 AND px_out > 0""").df()


def net(df: pd.DataFrame) -> np.ndarray:
    return (df.px_out / df.px_in * ((1 - FEE) * (1 - IMPACT)) ** 2 - PRIO - 1).to_numpy()


def main() -> None:
    r = Report("jocry_copy")
    r("# Studio storico: i wallet che guadagnano continuano a guadagnare? Copiarli conviene? (jocry, giu-lug 2026)")
    r("\nPre-registrazione (testo originale):\n\n```\n" + __doc__.split("PRE-REGISTERED")[1].strip() + "\n```")
    DATA.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(DB)
    con.execute("SET memory_limit='5GB'; SET temp_directory='/tmp/duck'; SET preserve_insertion_order=false")
    build(con, r)
    n_pos, n_w = con.execute("SELECT count(*), count(DISTINCT w) FROM pos").fetchone()
    r(f"Posizioni: {n_pos:,} di {n_w:,} wallet.")

    # --- who earns
    w_all = con.execute("SELECT w, sum(value - cost) AS pnl, count(*) AS n FROM pos GROUP BY w").df()
    pos_w = w_all[w_all.pnl > 0]
    top = w_all.sort_values("pnl", ascending=False)
    k1 = max(1, len(top) // 100)
    r("\n## 1. Chi guadagna sulle curve (tutto il periodo)")
    r(f"- wallet in guadagno: {100 * len(pos_w) / len(w_all):.1f}%; guadagno totale dei vincenti {pos_w.pnl.sum():,.0f} SOL, "
      f"perdita totale dei perdenti {-w_all[w_all.pnl <= 0].pnl.sum():,.0f} SOL")
    r(f"- il miglior 1% dei wallet ({k1:,}) prende il {100 * top.pnl.head(k1).clip(lower=0).sum() / max(pos_w.pnl.sum(), 1e-9):.1f}% "
      "dei guadagni")

    # --- persistence
    t0, t1 = con.execute("SELECT min(end_ts), max(end_ts) FROM pos").fetchone()
    d0 = int(t0 // 86400) + 1
    d1 = int(t1 // 86400)
    rows = []
    for d in range(d0, d1 - 5, 3):
        a = wallet_window(con, d * 86400, (d + 3) * 86400)
        b = wallet_window(con, (d + 3) * 86400, (d + 6) * 86400)
        a, b = a[eligible(a)], b[eligible(b)]
        m = a.merge(b, on="w", suffixes=("_a", "_b"))
        if len(m) < 30:
            continue
        ra, rb = m.sum_ret_a / m.n_a, m.sum_ret_b / m.n_b
        rho = pd.Series(ra).rank().corr(pd.Series(rb).rank())
        topd = ra >= ra.quantile(0.9)
        rows.append({"finestra": pd.Timestamp(d * 86400, unit="s").date(), "wallet": len(m), "spearman": rho,
                     "top10%_poi_media_%": 100 * rb[topd].mean(), "altri_poi_media_%": 100 * rb[~topd].mean()})
    r("\n## 2. Persistenza: chi guadagna in 3 giorni guadagna nei 3 successivi?")
    r.table(pd.DataFrame(rows))

    # --- copy simulation
    r("\n## 3. Copiare i migliori dal giorno dopo (fuori campione)")
    res = {}
    for d in range(d0 + 3, d1 + 1):
        win = wallet_window(con, (d - 3) * 86400, d * 86400)
        el = win[eligible(win)].copy()
        if el.empty:
            continue
        el["t"] = tstat(el)
        lead = el[(el.win / el.n >= 0.5) & (el.pnl >= 1.0) & (el.sum_ret / el.n >= 0.10)].nlargest(TOP_N, "t").w.tolist()
        ctrl = random.Random(d).sample(sorted(el.w), min(TOP_N, len(el)))
        for delay in DELAYS:
            for group, ws in (("migliori", lead), ("controllo", ctrl)):
                c = copies(con, ws, d * 86400, (d + 1) * 86400, delay)
                if c.empty:
                    continue
                c = c.drop_duplicates("mint")  # one copy per token and variant, as live
                c["ret"] = net(c)
                c["day"] = d
                res.setdefault((group, delay), []).append(c[["day", "ret"]])
    out, pvals = [], []
    mid = (d0 + 3 + d1) / 2
    for (group, delay), parts in sorted(res.items()):
        x = pd.concat(parts)
        lo, hi, p = boot_mean(x.ret.to_numpy())
        early = x.day < mid
        out.append({"gruppo": group, "ritardo_s": delay, "copie": len(x), "giorni": x.day.nunique(),
                    "media_%": 100 * x.ret.mean(), "IC95_basso_%": 100 * lo, "IC95_alto_%": 100 * hi, "p": p,
                    "mediana_%": 100 * x.ret.median(), "vincenti_%": 100 * (x.ret > 0).mean(),
                    "1a_metà_%": 100 * x.ret[early].mean(), "2a_metà_%": 100 * x.ret[~early].mean()})
        pvals.append(p)
    tab = pd.DataFrame(out)
    if not tab.empty:
        tab["q_BH"] = bh(pvals)
        ctrl_mean = {row.ritardo_s: row["media_%"] for _, row in tab[tab.gruppo == "controllo"].iterrows()}
        tab["verdetto"] = [
            "positiva, stabile e sopra il controllo" if (row.gruppo == "migliori" and row.q_BH < 0.05
                                                        and row["1a_metà_%"] > 0 and row["2a_metà_%"] > 0
                                                        and row["IC95_basso_%"] > ctrl_mean.get(row.ritardo_s, 0))
            else ("controllo" if row.gruppo == "controllo" else "non dimostrata") for _, row in tab.iterrows()]
    r.table(tab)
    r.save()


if __name__ == "__main__":
    main()
