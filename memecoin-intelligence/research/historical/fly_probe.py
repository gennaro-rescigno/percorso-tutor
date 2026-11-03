"""Study 'fly_probe': structure of bryceweiner/fly-trader-seed (MIT): a pg_dump of 1-minute PumpSwap candles.

Reads the dump with pg_restore (no database needed): table list, CREATE TABLE statements, first rows of the data.
"""

from __future__ import annotations

import itertools
import shutil
import subprocess

from common import Report, download

DS = "bryceweiner/fly-trader-seed"


def pg_restore() -> str:
    for cand in ("pg_restore", "/usr/lib/postgresql/18/bin/pg_restore", "/usr/lib/postgresql/17/bin/pg_restore",
                 "/usr/lib/postgresql/16/bin/pg_restore"):
        if shutil.which(cand) or cand.startswith("/") and shutil.os.path.exists(cand):
            return cand
    raise RuntimeError("pg_restore non trovato")


def main() -> None:
    r = Report("fly_probe")
    r("# Probe di fly-trader-seed")
    dump = download(DS, "fly_trader_core.dump")
    r(f"dump: {dump.stat().st_size / 1e9:.2f} GB")
    exe = pg_restore()
    ver = subprocess.run([exe, "--version"], capture_output=True, text=True).stdout.strip()
    r(f"pg_restore: {ver}")
    toc = subprocess.run([exe, "-l", str(dump)], capture_output=True, text=True)
    r("\n## Indice del dump\n```\n" + (toc.stdout or toc.stderr)[:20000] + "\n```")
    schema = subprocess.run([exe, "--schema-only", "-f", "-", str(dump)], capture_output=True, text=True)
    text = schema.stdout or schema.stderr
    blocks = [b for b in text.split(";\n") if "CREATE TABLE" in b]
    r("\n## Tabelle\n```\n" + ";\n".join(blocks)[:30000] + "\n```")
    for table in ("pump_minutes", "corpus_tokens", "corpus_features", "pump_pools", "pump_events", "tokens",
                  "token_insiders", "mature_days"):
        p = subprocess.Popen([exe, "--data-only", "-t", table, "-f", "-", str(dump)], stdout=subprocess.PIPE, text=True)
        lines = list(itertools.islice((ln for ln in p.stdout if ln.strip()), 12))
        p.kill()
        r(f"\n## {table}: prime righe\n```\n" + "".join(lines)[:6000] + "\n```")
    r.save()


if __name__ == "__main__":
    main()
