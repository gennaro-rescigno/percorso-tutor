"""Study 'probe2': cards, licences, files, schemas, sizes and date ranges of the free datasets not probed yet.

No analysis: it only says what each dataset contains, so that a study can be designed on it (or the dataset
rejected) without guessing. Files larger than MAX_MB are listed but not downloaded.
"""

from __future__ import annotations

import json
import urllib.request

import duckdb

from common import DATA, UA, Report, download, hf_tree, hf_url

DATASETS = ["launchtape/solana-launch-tape", "hussxamg04/trenches-pumpfun-forward-2026-08", "AratiKamat/red-pump-2026",
            "cryptodata/pumpfun-dataset-light", "pumpdatafun/pump-fun-trades-sample"]
MAX_MB = 1500
TABULAR = (".parquet", ".csv", ".csv.gz", ".jsonl", ".json")


def card(ds: str):
    for doc in ("README.md", "KNOWN_ISSUES.md"):
        try:
            req = urllib.request.Request(hf_url(ds, doc), headers=UA)
            with urllib.request.urlopen(req, timeout=60) as resp:
                yield doc, resp.read().decode("utf-8", "replace")
        except Exception as e:
            yield doc, f"(non disponibile: {e})"


def main() -> None:
    r = Report("probe2")
    r("# Probe dei dataset gratuiti non ancora esaminati")
    con = duckdb.connect()
    con.execute("SET memory_limit='4GB'")
    for ds in DATASETS:
        r(f"\n# {ds}")
        try:
            req = urllib.request.Request(f"https://huggingface.co/api/datasets/{ds}", headers=UA)
            with urllib.request.urlopen(req, timeout=60) as resp:
                meta = json.loads(resp.read())
            r(f"- licenza / tag: {[t for t in meta.get('tags', []) if t.startswith(('license', 'size', 'format'))]}")
            r(f"- ultima modifica: {meta.get('lastModified')} · download: {meta.get('downloads')}")
        except Exception as e:
            r(f"- metadati non disponibili: {e}")
        for doc, text in card(ds):
            r(f"\n## {doc}\n\n```\n{text[:7000]}\n```")
        try:
            files = hf_tree(ds)
        except Exception as e:
            r(f"- elenco dei file non disponibile: {e}")
            continue
        r("\n## File")
        for f in files[:200]:
            r(f"- `{f['path']}` {f.get('size', 0) / 1e6:,.1f} MB")
        if len(files) > 200:
            r(f"- ... altri {len(files) - 200} file")
        seen = set()
        for f in sorted(files, key=lambda x: x["path"]):
            p = f["path"]
            if not p.endswith(TABULAR):
                continue
            key = (p.rsplit("/", 1)[0] if "/" in p else "", p.split(".")[-1])
            if key in seen:
                continue
            seen.add(key)
            if f.get("size", 0) / 1e6 > MAX_MB:
                r(f"\n### {p}: {f.get('size', 0) / 1e6:,.0f} MB, troppo grande per il probe (solo elencato)")
                continue
            try:
                local = download(ds, p)
                reader = ("read_parquet" if p.endswith(".parquet") else
                          "read_json_auto" if p.endswith((".jsonl", ".json")) else "read_csv_auto")
                src = f"{reader}('{local}')"
                cols = con.execute(f"DESCRIBE SELECT * FROM {src}").fetchall()
                n = con.execute(f"SELECT count(*) FROM {src}").fetchone()[0]
                r(f"\n### {p}: {n:,} righe")
                r("\n".join(f"- `{c[0]}` {c[1]}" for c in cols[:80]))
                for c in cols:
                    if any(k in c[0].lower() for k in ("time", "date", "ts", "slot", "block")) and len(cols) < 200:
                        try:
                            lo, hi = con.execute(f'SELECT min("{c[0]}"), max("{c[0]}") FROM {src}').fetchone()
                            r(f"- intervallo di `{c[0]}`: {lo} → {hi}")
                        except Exception:
                            pass
                sample = con.execute(f"SELECT * FROM {src} LIMIT 3").df()
                r("\n```\n" + sample.to_string(max_colwidth=36)[:4000] + "\n```")
                local.unlink(missing_ok=True)
            except Exception as e:
                r(f"\n### {p}: errore {type(e).__name__}: {str(e)[:300]}")
    r.save()


if __name__ == "__main__":
    main()
