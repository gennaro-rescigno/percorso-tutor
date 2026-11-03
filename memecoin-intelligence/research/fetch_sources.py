"""Download the research sources as plain text (run by the memecoin-research-fetch workflow, not by the bot)."""

import html
import json
import re
import sys
import urllib.request
from pathlib import Path

OUT = Path(sys.argv[1])
HERE = Path(__file__).parent
UA = {"User-Agent": "Mozilla/5.0 (research bot; read-only)"}


def get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def to_text(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style|nav|footer|header|svg|noscript)[^>]*>.*?</\1>", " ", raw)
    raw = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</h[1-6]>|</li>|</tr>", "\n", raw)
    raw = re.sub(r"(?i)<h([1-6])[^>]*>", lambda m: "\n" + "#" * int(m.group(1)) + " ", raw)
    raw = re.sub(r"(?i)<li[^>]*>", "\n- ", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    raw = html.unescape(raw)
    raw = re.sub(r"[ \t\r\f\v]+", " ", raw)
    raw = re.sub(r"\n\s*\n\s*\n+", "\n\n", raw)
    return raw.strip()


OUT.mkdir(parents=True, exist_ok=True)
index = []
for line in (HERE / "sources.txt").read_text().splitlines():
    if not line.strip() or line.startswith("#"):
        continue
    slug, url = line.split(None, 1)
    try:
        body = get(url).decode("utf-8", "replace")
        text = body if url.endswith(".md") else to_text(body)
        (OUT / f"{slug}.md").write_text(f"# {slug}\n\nFonte: {url}\n\n{text}\n")
        index.append(f"- ok   {slug} ({len(text):,} caratteri) {url}")
    except Exception as e:
        index.append(f"- FAIL {slug} {url}: {type(e).__name__}: {str(e)[:120]}")

ds_out = OUT / "datasets"
ds_out.mkdir(exist_ok=True)
for ds in (HERE / "datasets.txt").read_text().splitlines():
    if not ds.strip() or ds.startswith("#"):
        continue
    slug = ds.replace("/", "__")
    try:
        meta = json.loads(get(f"https://huggingface.co/api/datasets/{ds}"))
        tree = json.loads(get(f"https://huggingface.co/api/datasets/{ds}/tree/main?recursive=true"))
        files = [{"path": f.get("path"), "size": f.get("size")} for f in tree if f.get("type") == "file"]
        total = sum(f["size"] or 0 for f in files)
        try:
            card = get(f"https://huggingface.co/datasets/{ds}/raw/main/README.md").decode("utf-8", "replace")
        except Exception:
            card = "(scheda non disponibile)"
        (ds_out / f"{slug}.md").write_text(
            f"# {ds}\n\nlicenza: {(meta.get('cardData') or {}).get('license')} · gated: {meta.get('gated')} · "
            f"file: {len(files)} · dimensione totale: {total / 1e9:.2f} GB\n\n## File\n"
            + "\n".join(f"- {f['path']} ({(f['size'] or 0) / 1e6:.1f} MB)" for f in files[:200])
            + f"\n\n## Scheda\n\n{card}\n")
        index.append(f"- ok   dataset {ds}: {len(files)} file, {total / 1e9:.2f} GB")
    except Exception as e:
        index.append(f"- FAIL dataset {ds}: {type(e).__name__}: {str(e)[:120]}")

(OUT / "INDEX.md").write_text("# Fonti scaricate\n\n" + "\n".join(index) + "\n")
print("\n".join(index))
