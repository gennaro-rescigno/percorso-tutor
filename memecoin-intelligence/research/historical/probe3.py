"""Study 'probe3': full cards of the two useful new datasets (column meanings), no analysis."""

from __future__ import annotations

import urllib.request

from common import UA, Report, hf_url

DOCS = [("pumpdatafun/pump-fun-trades-sample", "README.md"),
        ("hussxamg04/trenches-pumpfun-forward-2026-08", "README.md"),
        ("hussxamg04/trenches-pumpfun-forward-2026-08", "DATASHEET.md")]


def main() -> None:
    r = Report("probe3")
    r("# Schede complete dei dataset pumpdata (15 ottobre 2026) e trenches (agosto 2026)")
    for ds, doc in DOCS:
        try:
            req = urllib.request.Request(hf_url(ds, doc), headers=UA)
            with urllib.request.urlopen(req, timeout=60) as resp:
                text = resp.read().decode("utf-8", "replace")
            r(f"\n## {ds} / {doc}\n\n```\n{text}\n```")
        except Exception as e:
            r(f"\n## {ds} / {doc}: non disponibile ({e})")
    r.save()


if __name__ == "__main__":
    main()
