"""Shared helpers for the historical studies (run on GitHub runners by the memecoin-historical workflow).

Free public datasets only (Hugging Face, open licences). Nothing here is used by the bot at runtime.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

DATA = Path(os.environ.get("MCI_HIST_DATA", "/tmp/hist-data"))
OUT = Path(os.environ.get("MCI_HIST_OUT", "/tmp/out"))
UA = {"User-Agent": "Mozilla/5.0 (research bot; read-only)"}
JOCRY = "jocry/Pumpfun_Memecoin_Corpus"
LOOP = "loopholetape/pumpfun-launches"


def hf_url(ds: str, path: str) -> str:
    return f"https://huggingface.co/datasets/{ds}/resolve/main/{path}"


def hf_tree(ds: str) -> list[dict]:
    req = urllib.request.Request(f"https://huggingface.co/api/datasets/{ds}/tree/main?recursive=true", headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return [f for f in json.loads(r.read()) if f.get("type") == "file"]


def download(ds: str, path: str, retries: int = 4) -> Path:
    """Download one dataset file to DATA (skipped when already complete)."""
    dest = DATA / ds.replace("/", "__") / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    tmp = dest.with_suffix(dest.suffix + ".part")
    for attempt in range(retries):
        try:
            req = urllib.request.Request(hf_url(ds, path), headers=UA)
            with urllib.request.urlopen(req, timeout=300) as r, open(tmp, "wb") as f:
                while chunk := r.read(1 << 20):
                    f.write(chunk)
            tmp.rename(dest)
            return dest
        except Exception as e:  # network hiccup: retry with backoff
            print(f"download {path} failed ({e}); retry {attempt + 1}", file=sys.stderr)
            time.sleep(2 ** (attempt + 1))
    raise RuntimeError(f"cannot download {ds}/{path}")


def download_prefix(ds: str, prefix: str) -> list[Path]:
    files = [f["path"] for f in hf_tree(ds) if f["path"].startswith(prefix) and f["path"].endswith(".parquet")]
    return [download(ds, p) for p in sorted(files)]


class Report:
    """Markdown report written to OUT/<name>.md and echoed to stdout (the workflow log)."""

    def __init__(self, name: str):
        OUT.mkdir(parents=True, exist_ok=True)
        self.path = OUT / f"{name}.md"
        self.lines: list[str] = []

    def __call__(self, text: str = "") -> None:
        print(text, flush=True)
        self.lines.append(text)

    def table(self, df, floatfmt: str = "{:.4g}") -> None:
        cols = list(df.columns)
        self("| " + " | ".join(str(c) for c in cols) + " |")
        self("|" + "---|" * len(cols))
        for row in df.itertuples(index=False):
            cells = []
            for v in row:
                if isinstance(v, float):
                    cells.append(floatfmt.format(v) if v == v else "")
                else:
                    cells.append(str(v))
            self("| " + " | ".join(cells) + " |")
        self()

    def save(self) -> None:
        self.path.write_text("\n".join(self.lines) + "\n")
