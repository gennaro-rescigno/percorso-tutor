"""Facts extracted from a ``getTransaction`` (jsonParsed, maxSupportedTransactionVersion=1) result.

Only facts present in the transaction are reported: fee payer and signers, compute-budget price/limit, the
priority fee actually paid, Jito tips, native SOL transfers (top-level and inner) and pump.fun events.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from mci.chain import pump
from mci.chain.borsh import Reader, b58decode

COMPUTE_BUDGET = "ComputeBudget111111111111111111111111111111"
SYSTEM_PROGRAM = "11111111111111111111111111111111"
BASE_FEE_PER_SIGNATURE = 5000
# public, documented Jito tip accounts (also returned by the block engine's getTipAccounts)
JITO_TIP_ACCOUNTS = frozenset({
    "96gYZGLnJYVFmbjzopPSU6QiEV5fGqZNyN9nmNhvrZU5", "HFqU5x63VTqvQss8hp11i4wVV8bD44PvwucfZ2bU7gRe",
    "Cw8CFyM9FkoMi7K7Crf6HNQqf4uEMzpKw6QNghXLvLkY", "ADaUMid9yfUytqMBgopwjb2DTLSokTSzL1zt6iGPaS49",
    "DfXygSm4jCyNCybVYYK6DwvWqjKee8pbDmJGcLWNDXjh", "ADuUkR4vqLUMWXxW9gh6D6L8pMSawimctcNZ5pGwDcEt",
    "DttWaMuVvTiduZRnguLF7jNxTgiMBZ1hyAumKUiL2KRL", "3AVi9Tg9Uo68tJfuvoKvqKNWKkC5wPdSSdeBnizKZ6jT",
})


@dataclass
class SolTransfer:
    source: str
    destination: str
    lamports: int
    kind: str = "transfer"  # transfer | createAccount


@dataclass
class TxFacts:
    signature: str | None
    slot: int | None
    block_time: int | None
    ok: bool
    fee_lamports: int
    fee_payer: str | None
    signers: list[str]
    programs: list[str]
    cu_limit: int | None = None
    cu_price_micro: int | None = None
    priority_lamports: int = 0
    jito_tip_lamports: int = 0
    transfers: list[SolTransfer] = field(default_factory=list)
    events: list[Any] = field(default_factory=list)

    @property
    def uses_jito(self) -> bool:
        return self.jito_tip_lamports > 0


def _compute_budget(ix: dict[str, Any], facts: TxFacts) -> None:
    try:
        data = b58decode(ix.get("data") or "")
    except ValueError:
        return
    if not data:
        return
    r = Reader(data, 1)
    try:
        if data[0] == 2:
            facts.cu_limit = r.u32()
        elif data[0] == 3:
            facts.cu_price_micro = r.u64()
    except ValueError:
        pass


def _system(ix: dict[str, Any], facts: TxFacts, tip_accounts: frozenset[str]) -> None:
    parsed = ix.get("parsed")
    if not isinstance(parsed, dict):
        return
    info = parsed.get("info") or {}
    kind = parsed.get("type")
    if kind in ("transfer", "transferWithSeed"):
        src, dst, lam = info.get("source"), info.get("destination"), int(info.get("lamports") or 0)
        if src and dst and lam > 0:
            facts.transfers.append(SolTransfer(src, dst, lam))
            if dst in tip_accounts:
                facts.jito_tip_lamports += lam
    elif kind in ("createAccount", "createAccountWithSeed"):
        src, dst, lam = info.get("source"), info.get("newAccount"), int(info.get("lamports") or 0)
        if src and dst and lam > 0:
            facts.transfers.append(SolTransfer(src, dst, lam, "createAccount"))


def parse_transaction(tx: dict[str, Any], tip_accounts: frozenset[str] = JITO_TIP_ACCOUNTS) -> TxFacts:
    meta = tx.get("meta") or {}
    t = tx.get("transaction") or {}
    msg = t.get("message") or {}
    keys = msg.get("accountKeys") or []
    pubkeys = [k.get("pubkey") if isinstance(k, dict) else k for k in keys]
    signers = [k.get("pubkey") for k in keys if isinstance(k, dict) and k.get("signer")]
    sigs = t.get("signatures") or []
    facts = TxFacts(
        signature=sigs[0] if sigs else None, slot=tx.get("slot"), block_time=tx.get("blockTime"),
        ok=meta.get("err") is None, fee_lamports=int(meta.get("fee") or 0),
        fee_payer=pubkeys[0] if pubkeys else None, signers=signers, programs=[],
    )
    n_sig = max(len(sigs), 1)
    facts.priority_lamports = max(facts.fee_lamports - BASE_FEE_PER_SIGNATURE * n_sig, 0)
    top = msg.get("instructions") or []
    inner = [ix for group in (meta.get("innerInstructions") or []) for ix in (group.get("instructions") or [])]
    for ix in top:
        pid = ix.get("programId")
        if pid and pid not in facts.programs:
            facts.programs.append(pid)
        if pid == COMPUTE_BUDGET:
            _compute_budget(ix, facts)
    for ix in top + inner:
        if ix.get("programId") == SYSTEM_PROGRAM:
            _system(ix, facts, tip_accounts)
    if facts.ok:
        facts.events = pump.events_from_logs(meta.get("logMessages"), facts.signature, facts.slot)
    return facts


def funding_transfer(tx: dict[str, Any], wallet: str) -> SolTransfer | None:
    """The largest native SOL transfer INTO ``wallet`` in this transaction (its funding, for an oldest tx)."""
    facts = parse_transaction(tx)
    incoming = [x for x in facts.transfers if x.destination == wallet and x.source != wallet]
    return max(incoming, key=lambda x: x.lamports) if incoming else None
