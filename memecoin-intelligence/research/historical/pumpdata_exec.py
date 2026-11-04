"""Study 'pumpdata_exec': how often a trade FAILS on pump.fun and PumpSwap, by the token's age (real data, one day).

Data: pumpdatafun/pump-fun-trades-sample (CC BY 4.0): every curve and PumpSwap trade of 2026-10-15 that the
archive ties to a coin, the transactions that failed on chain kept beside the ones that landed, with the fee each
failed transaction paid and its error. Descriptive only (no strategy): it gives the backtests a measured
"orders not executable" rate and the cost of a failed attempt instead of an assumption.

Method (fixed before reading the data): a transaction is one (slot, idx); a token's age is the block time of the
trade minus the block time of its creation (the day's launches table; tokens created before the day are reported
apart); age buckets 0-10 s, 10-30 s, 30-60 s, 1-5 min, 5-60 min, 1-24 h; failure share = failed transactions /
(failed + landed) per venue, side and bucket; a failed transaction's fee is counted once.
"""

from __future__ import annotations

import os

import duckdb
import pandas as pd

from common import Report, download, hf_tree

DS = "pumpdatafun/pump-fun-trades-sample"
BUCKETS = "CASE WHEN age IS NULL OR age < 0 THEN '9 creato prima del giorno' WHEN age < 10 THEN '1 0-10 s' WHEN age < 30 THEN '2 10-30 s' " \
          "WHEN age < 60 THEN '3 30-60 s' WHEN age < 300 THEN '4 1-5 min' WHEN age < 3600 THEN '5 5-60 min' ELSE '6 1-24 h' END"


def main() -> None:
    r = Report("pumpdata_exec")
    r("# Operazioni fallite su pump.fun e PumpSwap per età del token (15 ottobre 2026, dati reali)")
    r("\n" + __doc__.split("\n\n", 1)[1].strip())
    files = [f["path"] for f in hf_tree(DS)]
    con = duckdb.connect()
    con.execute("SET memory_limit='4GB'; SET temp_directory='/tmp/duck'; SET preserve_insertion_order=false")
    lp = [p for p in files if p.startswith("launches/") and p.endswith(".parquet")]
    launch = download(DS, lp[0])
    con.execute(f"CREATE TABLE created AS SELECT mint, min(ts) AS t0 FROM read_parquet('{launch}') GROUP BY mint")
    r(f"Lanci del giorno: {con.execute('SELECT count(*) FROM created').fetchone()[0]:,}.")
    con.execute("CREATE TABLE agg (venue VARCHAR, side VARCHAR, failed BOOLEAN, bucket VARCHAR, tx BIGINT, fee_sol DOUBLE)")
    con.execute("CREATE TABLE err (venue VARCHAR, side VARCHAR, bucket VARCHAR, error VARCHAR, tx BIGINT)")
    con.execute("CREATE TABLE wal (venue VARCHAR, bucket VARCHAR, wallet VARCHAR, failed BOOLEAN, tx BIGINT)")
    for p in sorted(x for x in files if x.startswith("data/") and x.endswith(".parquet")):
        loc = download(DS, p)
        con.execute(f"""
            CREATE OR REPLACE TEMP TABLE t AS
            SELECT d.venue, d.side, d.failed, d.slot, d.idx, d.wallet, d.fee_lamports, d.error,
                   d.ts - c.t0 AS age
            FROM read_parquet('{loc}') d LEFT JOIN created c USING (mint)""")
        con.execute(f"""
            INSERT INTO agg
            SELECT venue, side, failed, {BUCKETS} AS bucket, count(DISTINCT slot * 100000 + idx) AS tx,
                   sum(CASE WHEN failed THEN fee_lamports ELSE 0 END) / 1e9 AS fee_sol
            FROM (SELECT DISTINCT venue, side, failed, slot, idx, age, fee_lamports FROM t) GROUP BY ALL""")
        con.execute(f"""
            INSERT INTO err SELECT venue, side, {BUCKETS} AS bucket, coalesce(error, '?') AS error, count(DISTINCT slot * 100000 + idx)
            FROM t WHERE failed GROUP BY ALL""")
        con.execute(f"""
            INSERT INTO wal SELECT venue, {BUCKETS} AS bucket, wallet, failed, count(DISTINCT slot * 100000 + idx)
            FROM t WHERE side = 'buy' AND (age < 60) GROUP BY ALL""")
        os.remove(loc)
        print(f"{p}: fatto", flush=True)
    a = con.execute("""
        SELECT venue, side, bucket, sum(CASE WHEN NOT failed THEN tx ELSE 0 END) AS riuscite,
               sum(CASE WHEN failed THEN tx ELSE 0 END) AS fallite,
               sum(fee_sol) AS commissioni_fallite_SOL
        FROM agg GROUP BY ALL ORDER BY venue, side, bucket""").df()
    a["fallite_%"] = 100 * a.fallite / (a.fallite + a.riuscite).where(a.fallite + a.riuscite > 0)
    a["commissione_media_fallita_SOL"] = a.commissioni_fallite_SOL / a.fallite.where(a.fallite > 0)
    a["bucket"] = a.bucket.str[2:]
    r("\n## Quota di transazioni fallite per mercato, lato ed età del token")
    r.table(a)
    e = con.execute("""
        WITH x AS (SELECT venue, side, bucket, error, sum(tx) AS tx FROM err GROUP BY ALL),
        y AS (SELECT *, tx / sum(tx) OVER (PARTITION BY venue, side, bucket) AS share,
                     row_number() OVER (PARTITION BY venue, side, bucket ORDER BY tx DESC) AS rk FROM x)
        SELECT venue, side, bucket, left(error, 90) AS errore, tx AS transazioni, 100 * share AS quota_pct FROM y
        WHERE rk <= 4 AND bucket IN ('1 0-10 s', '3 30-60 s', '5 5-60 min') ORDER BY venue, side, bucket, rk""").df()
    e["bucket"] = e.bucket.str[2:]
    r("\n## Errori più frequenti delle transazioni fallite")
    r.table(e)
    w = con.execute("""
        WITH x AS (SELECT venue, wallet, sum(CASE WHEN failed THEN tx ELSE 0 END) AS f, sum(CASE WHEN NOT failed THEN tx ELSE 0 END) AS ok
                   FROM wal WHERE venue = 'curve' GROUP BY ALL)
        SELECT count(*) AS wallet, sum(CASE WHEN ok = 0 THEN 1 ELSE 0 END) AS mai_riusciti,
               median(f / (f + ok)) AS quota_fallita_mediana, avg(f) AS tentativi_falliti_medi
        FROM x""").df()
    r("\n## Acquisti sulla curva nei primi 60 secondi: per wallet")
    r.table(w)
    r.save()


if __name__ == "__main__":
    main()
