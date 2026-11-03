"""Honeypot check by simulation: can a REAL holder sell right now?

1. find a holder wallet: an early buyer still holding (chain stream) or, otherwise, the owner of one of the
   largest token accounts whose owner is a wallet (an ed25519 point: pool vaults and curves are PDAs, off-curve);
2. check its current token balance (``getTokenAccountsByOwner``);
3. ask Jupiter for a sell quote and build the swap transaction for THAT holder (nothing is signed);
4. ``simulateTransaction`` (sigVerify off, recent blockhash replaced): free and read-only.

Tri-state result: True (sell simulated successfully), False (sell blocked by the token: frozen account,
transfer hook / non-transferable), None (not verifiable now: no holder, fee balance, slippage, budget...).
Only clear token-side failures become False; everything else stays "non verificato", never invented.
"""

from __future__ import annotations

import logging
from typing import Any

from mci.chain.borsh import b58decode
from mci.chain.pda import is_on_curve
from mci.chain.rpc_pool import RpcPool
from mci.collectors.jupiter import JupiterCollector
from mci.utils.http import SourceUnavailable

log = logging.getLogger(__name__)

BLOCKED_MARKERS = ("account is frozen", "accountfrozen", "non-transferable", "nontransferable",
                   "transfer hook", "transferhook")
NOT_VERIFIABLE_ERRORS = ("InsufficientFundsForFee", "AccountNotFound", "BlockhashNotFound", "InsufficientFundsForRent")


def classify_simulation(value: dict[str, Any] | None) -> tuple[bool | None, str]:
    if value is None:
        return None, "simulazione non disponibile"
    err = value.get("err")
    logs = " ".join(value.get("logs") or []).lower()
    if err is None:
        return True, "vendita simulata con successo"
    if any(m in logs for m in BLOCKED_MARKERS):
        return False, "vendita bloccata dal token (" + next(m for m in BLOCKED_MARKERS if m in logs) + ")"
    if isinstance(err, str) and err in NOT_VERIFIABLE_ERRORS:
        return None, f"non verificabile ({err})"
    return None, f"errore di simulazione non attribuibile al token: {str(err)[:80]}"


async def find_holder(rpc: RpcPool, mint: str, candidates: list[str] | None = None) -> tuple[str, int] | None:
    for w in candidates or []:
        try:
            bal = await rpc.token_balance_raw(w, mint)
        except SourceUnavailable:
            return None
        if bal > 0:
            return w, bal
    if candidates:
        return None  # known holders sold out: do not spend the scarce getTokenLargestAccounts budget
    try:
        largest = await rpc.largest_accounts(mint)
    except SourceUnavailable:
        return None
    for acc in largest[:6]:
        try:
            info = await rpc.account(acc.get("address"), "jsonParsed")
        except SourceUnavailable:
            return None
        parsed = (((info or {}).get("data") or {}).get("parsed") or {}).get("info") or {}
        owner = parsed.get("owner")
        amount = int((parsed.get("tokenAmount") or {}).get("amount") or 0)
        if owner and amount > 0 and is_on_curve(b58decode(owner)):
            return owner, amount
    return None


async def simulate_holder_sell(jup: JupiterCollector, rpc: RpcPool, mint: str, probe_raw: int,
                               candidates: list[str] | None = None) -> tuple[bool | None, str]:
    holder = await find_holder(rpc, mint, candidates)
    if holder is None:
        return None, "nessun holder verificabile"
    wallet, bal = holder
    amount = max(1, min(probe_raw, bal))
    try:
        q = await jup.sell_quote(mint, amount)
        if q is None:
            return None, "nessuna rotta di vendita per l'importo del test"
        tx = await jup.swap_transaction(q, wallet, priority_fee_lamports=10_000)
        value = await rpc.simulate(tx)
    except SourceUnavailable as e:
        return None, f"non verificabile ora ({e.detail[:60]})"
    ok, detail = classify_simulation(value)
    route = "/".join(q.route_labels[:2]) if q.route_labels else "?"
    return ok, f"{detail}, rotta {route}"
