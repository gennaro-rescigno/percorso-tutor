"""Weekly contract check: does the official pump.fun IDL still match the layouts our decoders rely on?

Run by the memecoin-contract-check GitHub workflow (free). Exit code 1 + a clear message when pump.fun changed
a field inside the prefix we decode, so the decoders are fixed BEFORE wrong data reach the bot.
"""

import json
import sys
import urllib.request

sys.path.insert(0, "memecoin-intelligence/backend")
from mci.chain.pump import check_idl  # noqa: E402

URL = "https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/idl/pump.json"

with urllib.request.urlopen(URL, timeout=30) as r:
    idl = json.load(r)
problems = check_idl(idl)
if problems:
    print("ATTENZIONE: il formato ufficiale di pump.fun è cambiato:")
    for p in problems:
        print(" -", p)
    sys.exit(1)
print("OK: l'IDL ufficiale di pump.fun è compatibile con i decoder del bot")
