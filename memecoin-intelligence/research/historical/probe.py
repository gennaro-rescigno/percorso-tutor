"""Study 'probe': schemas, sizes and sample rows of the free datasets (no analysis)."""

from __future__ import annotations

import urllib.request

import duckdb

from common import JOCRY, LOOP, UA, Report, download, hf_tree, hf_url

r = Report("probe")
r("# Probe dei dataset storici gratuiti")
for ds in (JOCRY, LOOP):
    for doc in ("KNOWN_ISSUES.md", "quickstart.py"):
        try:
            req = urllib.request.Request(hf_url(ds, doc), headers=UA)
            with urllib.request.urlopen(req, timeout=60) as resp:
                text = resp.read().decode("utf-8", "replace")
            r(f"\n## {ds} / {doc}\n\n```\n{text}\n```")
        except Exception as e:
            r(f"\n## {ds} / {doc}: non disponibile ({e})")

con = duckdb.connect()
con.execute("INSTALL httpfs; LOAD httpfs;")
for ds in (JOCRY, LOOP):
    files = [f["path"] for f in hf_tree(ds) if f["path"].endswith(".parquet")]
    seen_dirs = set()
    for p in sorted(files):
        d = p.rsplit("/", 1)[0] if "/" in p else p
        if d in seen_dirs:
            continue
        seen_dirs.add(d)
        url = hf_url(ds, p)
        try:
            cols = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{url}')").fetchall()
            n = con.execute(f"SELECT count(*) FROM read_parquet('{url}')").fetchone()[0]
            r(f"\n## {ds} / {p} — {n:,} righe nel file")
            r("\n".join(f"- `{c[0]}` {c[1]}" for c in cols))
            sample = con.execute(f"SELECT * FROM read_parquet('{url}') LIMIT 3").df()
            r("\n```\n" + sample.to_string(max_colwidth=40) + "\n```")
        except Exception as e:
            r(f"\n## {ds} / {p}: errore {type(e).__name__}: {str(e)[:300]}")
r.save()
