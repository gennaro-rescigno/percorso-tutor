"""Study 'tg_probe': download the public history of a Telegram channel (web preview t.me/s/<channel>), no analysis.

Read-only, no account, no login: only what Telegram shows to anyone on the channel's public web page. Every post
still visible is saved with its id, date (UTC), text and whether it was edited, so that the signal format can be
read before writing any parser. Posts the channel deleted are not visible: the backtest must say so.
Output: OUT/tg_<channel>_raw.json and a summary with the date range and sample posts.
"""

from __future__ import annotations

import html
import json
import os
import re
import time
import urllib.request

from common import OUT, UA, Report

CHANNEL = os.environ.get("TG_CHANNEL", "BINANCE_CRYPTO_SIGNALS_ML")
MAX_PAGES = 400

POST_RE = re.compile(r'<div class="tgme_widget_message_wrap.*?(?=<div class="tgme_widget_message_wrap|\Z)', re.S)
ID_RE = re.compile(r'data-post="[^"/]+/(\d+)"')
TEXT_RE = re.compile(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', re.S)
TIME_RE = re.compile(r'<time[^>]*datetime="([^"]+)"')
EDITED_RE = re.compile(r'class="tgme_widget_message_meta"[^>]*>\s*<span class="tgme_widget_message_views"|edited', re.I)


def clean(fragment: str) -> str:
    t = re.sub(r"<br\s*/?>", "\n", fragment)
    t = re.sub(r"<[^>]+>", "", t)
    return html.unescape(t).strip()


def fetch(url: str) -> str:
    for k in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:
            time.sleep(2 ** k)
    return ""


def main() -> None:
    r = Report(f"tg_probe_{CHANNEL.lower()}")
    r(f"# Storico pubblico del canale Telegram @{CHANNEL} (anteprima web, sola lettura)")
    posts: dict[int, dict] = {}
    before = None
    for page in range(MAX_PAGES):
        url = f"https://t.me/s/{CHANNEL}" + (f"?before={before}" if before else "")
        doc = fetch(url)
        if not doc:
            r(f"Pagina non scaricabile: {url}")
            break
        if page == 0 and "tgme_widget_message" not in doc:
            r("Il canale non ha un'anteprima web pubblica (privato, inesistente o con anteprima disattivata).")
            title = re.search(r"<title>(.*?)</title>", doc, re.S)
            r(f"Titolo della pagina: {html.unescape(title.group(1).strip()) if title else '-'}")
            break
        found = 0
        for block in POST_RE.findall(doc):
            m = ID_RE.search(block)
            if not m:
                continue
            pid = int(m.group(1))
            if pid in posts:
                continue
            tm = TIME_RE.search(block)
            tx = TEXT_RE.search(block)
            posts[pid] = {"id": pid, "date": tm.group(1) if tm else None, "text": clean(tx.group(1)) if tx else "",
                          "edited": "edited" in block, "has_photo": "tgme_widget_message_photo" in block}
            found += 1
        if not found:
            break
        before = min(posts)
        if before <= 1:
            break
        time.sleep(1.0)
    items = sorted(posts.values(), key=lambda p: p["id"])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"tg_{CHANNEL.lower()}_raw.json").write_text(json.dumps(items, ensure_ascii=False, indent=1))
    if not items:
        r("Nessun messaggio scaricato.")
        r.save()
        return
    with_text = [p for p in items if p["text"]]
    r(f"Messaggi visibili: **{len(items):,}** (con testo {len(with_text):,}, modificati {sum(p['edited'] for p in items):,}, "
      f"con immagine {sum(p['has_photo'] for p in items):,}); id da {items[0]['id']} a {items[-1]['id']} "
      f"(id mancanti nell'intervallo: {items[-1]['id'] - items[0]['id'] + 1 - len(items):,}, cioè cancellati o non pubblici); "
      f"date da {items[0]['date']} a {items[-1]['date']}.")
    words = {}
    for p in with_text:
        for w in re.findall(r"[A-Za-z#]{3,}", p["text"].upper()):
            words[w] = words.get(w, 0) + 1
    r("\nParole più frequenti: " + ", ".join(f"{w} ({n})" for w, n in sorted(words.items(), key=lambda x: -x[1])[:40]))
    r("\n## Esempi (30 messaggi distribuiti nel tempo)")
    step = max(1, len(with_text) // 30)
    for p in with_text[::step][:30]:
        r(f"\n### id {p['id']} · {p['date']}{' · modificato' if p['edited'] else ''}\n```\n{p['text'][:900]}\n```")
    r.save()


if __name__ == "__main__":
    main()
