"""Study 'jocry_probe': download the small jocry tables and describe them (DuckDB over HTTP got 403)."""

from __future__ import annotations

import duckdb

from common import JOCRY, Report, download

r = Report("jocry_probe")
r("# Probe jocry (download diretto)")
con = duckdb.connect()
for path in ("postgard_outcomes.parquet", "migrations.parquet", "postgard_snapshots.parquet", "tokens.parquet",
             "trades/trades-00000.parquet"):
    try:
        p = download(JOCRY, path)
        cols = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{p}')").fetchall()
        n = con.execute(f"SELECT count(*) FROM read_parquet('{p}')").fetchone()[0]
        r(f"\n## {path}: {n:,} righe, {p.stat().st_size / 1e6:.1f} MB")
        r("\n".join(f"- `{c[0]}` {c[1]}" for c in cols))
        r("\n```\n" + con.execute(f"SELECT * FROM read_parquet('{p}') LIMIT 3").df().to_string(max_colwidth=30) + "\n```")
    except Exception as e:
        r(f"\n## {path}: errore {type(e).__name__}: {str(e)[:300]}")
p = download(JOCRY, "postgard_snapshots.parquet")
r("\n## postgard_snapshots: intervallo tra istantanee e copertura per token")
r("```\n" + con.execute(f"""
    WITH s AS (SELECT mint, seconds_since_graduation AS t,
                      t - lag(seconds_since_graduation) OVER (PARTITION BY mint ORDER BY seconds_since_graduation) AS dt
               FROM read_parquet('{p}'))
    SELECT count(DISTINCT mint) AS mints, quantile_cont(dt, 0.5) AS dt_mediano_s, quantile_cont(dt, 0.9) AS dt_p90_s,
           quantile_cont(t, 0.5) AS t_mediano_s, max(t) AS t_max_s FROM s""").df().to_string() + "\n```")
p = download(JOCRY, "postgard_outcomes.parquet")
r("\n## postgard_outcomes: esiti")
r("```\n" + con.execute(f"SELECT outcome_label, count(*) n FROM read_parquet('{p}') GROUP BY 1 ORDER BY 2 DESC").df().to_string() + "\n```")
r.save()
