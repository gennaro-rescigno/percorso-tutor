"""Study 'fly_rules': simple rules on LISTED tokens (PumpSwap pools of pump.fun graduates), April-September 2026.

Data: bryceweiner/fly-trader-seed (MIT), table pump_minutes: 1-minute candles of every PumpSwap trade of graduated
tokens with buy/sell SOL, traders, SOL reserve of the pool, pool fee, wash, top-holder and insider selling.
The column `skill_buy` (buys by wallet-skill decile) is NOT used: the skill tables of that project may be fitted on
the whole period, which would leak the future.

PRE-REGISTERED (written before looking at any result):
  * checkpoints at the end of every hour after the graduation in which the token traded; one trade per token and
    rule: the first checkpoint that meets the rule;
  * rules (pool SOL reserve >= 20 SOL in all of them):
      L0 any traded hour from the 1st hour (reference);
      L1 momentum: close >= 1.5x the previous hour's close;
      L2 strong momentum: close >= 2x the close 3 hours before;
      L3 pullback: age >= 6 h, close <= 50% of the highest price since the graduation, >= 5 SOL traded in the hour;
      L4 survivor: age >= 24 h, reserve >= 50 SOL, >= 20 traders in the hour;
      L5 survivor without insider selling: L4 and no insider or top-holder selling in the last 6 hours;
      L6 accumulation: age >= 2 h, buys >= 2x sells (SOL) in the hour, >= 5 SOL bought;
  * exits after 1, 4 and 24 hours at the last price at or before that moment (no trade = unchanged price);
  * costs for a 0.1 SOL position: the pool's own fee rate on each side (1% when missing), price impact
    0.1 / reserve on entry and position value / reserve on exit, 1% priority fees;
  * statistics: mean with bootstrap 95% interval, Benjamini-Hochberg over all tests, verdict "positive and stable"
    only with q < 0.05 and a positive mean in at least 4 of the months covered; a gross (no cost) mean is shown too.
"""

from __future__ import annotations

import os
import subprocess

import duckdb
import numpy as np
import pandas as pd

from common import DATA, Report, download
from fly_probe import DS, pg_restore
from loop_curve import bh, boot_mean

PM_COLS = ("mint", "ts", "pool_id", "open", "high", "low", "close", "buy_sol", "sell_sol", "n_buys", "n_sells",
           "n_traders", "resq_sol", "fee_rate", "n_buyers", "wash_sol", "wash_buy_sol", "top_sell_sol",
           "insider_sell_sol", "skill_buy")
HOLDS_H = (1, 4, 24)
SIZE, PRIO = 0.1, 0.01


def extract(con: duckdb.DuckDBPyConnection, r: Report) -> str:
    """pump_minutes -> parquet, streaming the COPY block of the dump (no PostgreSQL server, bounded disk)."""
    out = str(DATA / "pump_minutes.parquet")
    if os.path.exists(out):
        return out
    dump = download(DS, "fly_trader_core.dump")
    tsv = str(DATA / "pm.tsv.gz")
    cmd = (f"'{pg_restore()}' --data-only -t pump_minutes -f - '{dump}' | "
           r"awk 'f && /^\\\.$/ {exit} f {print} /^COPY public.pump_minutes/ {f=1}' | gzip -1 > " + f"'{tsv}'")
    subprocess.run(["bash", "-o", "pipefail", "-c", cmd], check=False)
    os.remove(dump)
    tsv_to_parquet(con, tsv, out)
    os.remove(tsv)
    n = con.execute(f"SELECT count(*), count(DISTINCT mint), min(ts), max(ts) FROM read_parquet('{out}')").fetchone()
    r(f"Candele estratte: {n[0]:,} di {n[1]:,} token, dal {pd.Timestamp(n[2], unit='s'):%Y-%m-%d} "
      f"al {pd.Timestamp(n[3], unit='s'):%Y-%m-%d}.")
    return out


def tsv_to_parquet(con: duckdb.DuckDBPyConnection, tsv: str, out: str) -> None:
    cols = {c: "VARCHAR" for c in PM_COLS}
    con.execute(f"""
        COPY (SELECT mint, epoch(CAST(ts AS TIMESTAMPTZ)) AS ts, CAST(close AS DOUBLE) AS close,
                     CAST(high AS DOUBLE) AS high, CAST(buy_sol AS DOUBLE) AS buy_sol,
                     CAST(sell_sol AS DOUBLE) AS sell_sol, CAST(n_traders AS INTEGER) AS n_traders,
                     CAST(n_buys AS INTEGER) AS n_buys, CAST(n_sells AS INTEGER) AS n_sells,
                     CAST(resq_sol AS DOUBLE) AS resq_sol, CAST(fee_rate AS DOUBLE) AS fee_rate,
                     CAST(top_sell_sol AS DOUBLE) AS top_sell_sol, CAST(insider_sell_sol AS DOUBLE) AS insider_sell_sol
              FROM read_csv('{tsv}', delim='\t', header=false, quote='', escape='', nullstr='\\N',
                            columns={cols}, auto_detect=false))
        TO '{out}' (FORMAT parquet)""")


def hourly(con: duckdb.DuckDBPyConnection, pm: str) -> None:
    con.execute(f"CREATE OR REPLACE VIEW pm AS SELECT * FROM read_parquet('{pm}') WHERE close > 0")
    con.execute("""
        CREATE OR REPLACE TABLE grad AS SELECT mint, min(ts) AS g FROM pm GROUP BY mint""")
    con.execute("""
        CREATE OR REPLACE TABLE hb AS
        WITH b AS (SELECT p.*, floor((p.ts - g.g) / 3600)::INTEGER AS b FROM pm p JOIN grad g USING (mint))
        SELECT mint, b, arg_max(close, ts) AS close, max(high) AS high, sum(buy_sol) AS buy, sum(sell_sol) AS sell,
               sum(n_traders) AS traders, arg_max(resq_sol, ts) AS resq, arg_max(fee_rate, ts) AS fee,
               sum(coalesce(insider_sell_sol, 0) + coalesce(top_sell_sol, 0)) AS insider
        FROM b GROUP BY mint, b""")
    con.execute("""
        CREATE OR REPLACE TABLE cp AS
        SELECT h.*, g.g + (h.b + 1) * 3600 AS t, (h.b + 1) AS age_h,
               lag(close) OVER w AS prev_close, lag(b) OVER w AS prev_b,
               max(high) OVER (PARTITION BY mint ORDER BY b ROWS UNBOUNDED PRECEDING) AS peak,
               sum(insider) OVER (PARTITION BY mint ORDER BY b RANGE BETWEEN 5 PRECEDING AND CURRENT ROW) AS insider6
        FROM hb h JOIN grad g USING (mint)
        WINDOW w AS (PARTITION BY mint ORDER BY b)""")
    con.execute("""
        CREATE OR REPLACE TABLE cp AS
        WITH c AS (SELECT *, b - 3 AS b3 FROM cp)
        SELECT c.*, x.close AS close_3h FROM c ASOF LEFT JOIN hb x ON c.mint = x.mint AND c.b3 >= x.b""")


RULES = {
    "L0 qualsiasi ora": "resq >= 20",
    "L1 slancio: x1,5 in un'ora": "resq >= 20 AND prev_b = b - 1 AND close >= 1.5 * prev_close",
    "L2 slancio forte: x2 in 3 ore": "resq >= 20 AND close_3h > 0 AND close >= 2 * close_3h",
    "L3 ritracciamento: <= 50% del massimo, età >= 6 h": "resq >= 20 AND age_h >= 6 AND close <= 0.5 * peak "
                                                        "AND buy + sell >= 5",
    "L4 sopravvissuto: età >= 24 h, riserva >= 50, >= 20 trader": "resq >= 50 AND age_h >= 24 AND traders >= 20",
    "L5 L4 senza vendite di insider/top holder in 6 h": "resq >= 50 AND age_h >= 24 AND traders >= 20 "
                                                        "AND insider6 = 0",
    "L6 accumulo: acquisti >= 2x vendite, età >= 2 h": "resq >= 20 AND age_h >= 2 AND buy >= 2 * sell AND buy >= 5",
}


def trades(con, rule_sql: str, hold_h: int) -> pd.DataFrame:
    return con.execute(f"""
        WITH e AS (SELECT mint, t, close AS px_in, resq AS rq_in, coalesce(fee, 0.01) AS fee
                   FROM cp WHERE {rule_sql} QUALIFY row_number() OVER (PARTITION BY mint ORDER BY t) = 1),
        x AS (SELECT e.*, e.t + {hold_h * 3600} AS t_out FROM e),
        s AS (SELECT mint, ts, close, resq_sol FROM pm WHERE mint IN (SELECT mint FROM e))
        SELECT x.*, s.close AS px_out, s.resq_sol AS rq_out FROM x ASOF JOIN s ON x.mint = s.mint AND x.t_out >= s.ts
        """).df()


def net(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    gross = (df.px_out / df.px_in).to_numpy()
    imp_in = np.clip(SIZE / df.rq_in.clip(lower=1e-9), 0, 0.9).to_numpy()
    value = SIZE * gross
    imp_out = np.clip(value / df.rq_out.fillna(0).clip(lower=1e-9).to_numpy(), 0, 0.9)
    fee = df.fee.clip(0, 0.05).to_numpy()
    netr = gross * (1 - fee) ** 2 * (1 - imp_in) * (1 - imp_out) - PRIO - 1
    return netr, gross - 1


def main() -> None:
    r = Report("fly_rules")
    r("# Studio storico: regole semplici sui token già quotati su PumpSwap (aprile-settembre 2026)")
    r("\nPre-registrazione (testo originale):\n\n```\n" + __doc__.split("PRE-REGISTERED")[1].strip() + "\n```")
    DATA.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DATA / "fly.duckdb"))
    con.execute("SET memory_limit='5GB'; SET temp_directory='/tmp/duck'; SET preserve_insertion_order=false")
    pm = extract(con, r)
    hourly(con, pm)
    n_cp, n_tok = con.execute("SELECT count(*), count(DISTINCT mint) FROM cp").fetchone()
    r(f"Checkpoint orari: {n_cp:,} di {n_tok:,} token.")
    life = con.execute("""SELECT quantile_cont(age_h, 0.5), avg(CASE WHEN age_h >= 24 THEN 1 ELSE 0 END)
                          FROM (SELECT mint, max(age_h) AS age_h FROM cp GROUP BY mint)""").fetchone()
    r(f"Vita (ultima ora con scambi dopo il diploma): mediana {life[0]:.0f} h; ancora scambiato dopo 24 h: {100 * life[1]:.1f}%.")
    rows, pvals = [], []
    for name, sql in RULES.items():
        for h in HOLDS_H:
            df = trades(con, sql, h)
            df = df[df.px_out.notna() & (df.px_out > 0)]
            if len(df) < 30:
                continue
            ret, gross = net(df)
            lo, hi, p = boot_mean(ret)
            month = pd.to_datetime(df.t, unit="s").dt.to_period("M").astype(str).to_numpy()
            by_m = pd.Series(ret).groupby(month).mean()
            rows.append({"regola": name, "tenuta_h": h, "n": len(ret), "media_%": 100 * ret.mean(),
                         "IC95_basso_%": 100 * lo, "IC95_alto_%": 100 * hi, "p": p,
                         "mediana_%": 100 * np.median(ret), "vincenti_%": 100 * (ret > 0).mean(),
                         "lorda_media_%": 100 * gross.mean(), "lorda_mediana_%": 100 * np.median(gross),
                         "mesi_positivi": f"{int((by_m > 0).sum())}/{len(by_m)}"})
            pvals.append(p)
    tab = pd.DataFrame(rows)
    if not tab.empty:
        tab["q_BH"] = bh(pvals)
        pos = tab.mesi_positivi.str.split("/").map(lambda x: int(x[0]) >= max(4, int(x[1]) - 1))
        tab["verdetto"] = np.where((tab.q_BH < 0.05) & (tab["media_%"] > 0) & pos, "positiva e stabile", "non dimostrata")
    r.table(tab)
    r.save()


if __name__ == "__main__":
    main()
