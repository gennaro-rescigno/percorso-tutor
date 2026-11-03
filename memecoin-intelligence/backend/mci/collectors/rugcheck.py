"""RugCheck public API (read endpoints need no key; respect HTTP 429).

* ``GET /v1/tokens/{mint}/report/summary`` -> normalized score and risks
* ``GET /v1/tokens/{mint}/report``         -> full report (authorities, holders, markets, insiders)

No official documentation was retrievable during research (see RESEARCH_REPORT §9),
so every field is parsed defensively: unknown/missing -> None (never "safe").
"""

from __future__ import annotations

from typing import Any

from mci.domain import TokenSnapshot
from mci.utils.http import ApiClient, fnum, inum

# Accounts that hold supply but are not "holders" in the concentration sense.
NON_HOLDER_TYPES = {"amm", "locker", "burn", "pool", "bonding_curve", "program", "lp"}

DANGEROUS_EXTENSIONS = {
    "transferfeeconfig": "transfer_fee",
    "transferhook": "transfer_hook",
    "permanentdelegate": "permanent_delegate",
    "defaultaccountstate": "default_account_state",
    "nontransferable": "non_transferable",
    "confidentialtransfermint": "confidential_transfer",
    "pausableconfig": "pausable",
}


NULL_ADDRESSES = {"", "11111111111111111111111111111111", "null", "none"}


def _leaves(v):
    if isinstance(v, dict):
        for x in v.values():
            yield from _leaves(x)
    elif isinstance(v, (list, tuple)):
        for x in v:
            yield from _leaves(x)
    else:
        yield v


def extension_active(name: str, value) -> bool:
    """RugCheck lists every Token-2022 extension key, often with empty values (observed on live
    data, Nov 2026): an extension is dangerous only if it is actually configured."""
    if value in (None, False, {}, [], ""):
        return False
    key = name.replace("_", "").lower()
    if key == "transferfeeconfig":
        fees = []
        def walk(v, k=""):
            if isinstance(v, dict):
                for kk, vv in v.items():
                    walk(vv, kk)
            elif "basispoint" in k.lower() or k.lower() in ("fee", "feebps"):
                try:
                    fees.append(float(v))
                except (TypeError, ValueError):
                    pass
        walk(value)
        return any(f > 0 for f in fees)
    if key == "defaultaccountstate":
        states = [str(x).lower() for x in _leaves(value) if x is not None]
        return any("frozen" in s for s in states) or str(value).lower() == "frozen"
    for leaf in _leaves(value):
        if leaf is None or leaf is False or leaf == 0:
            continue
        if isinstance(leaf, str) and leaf.strip().lower() in NULL_ADDRESSES:
            continue
        return True
    return False


class RugCheckCollector:
    def __init__(self, base_url: str, client: ApiClient | None = None):
        self.api = client or ApiClient("rugcheck", base_url, rate_per_s=1.0, burst=2)

    async def close(self) -> None:
        await self.api.close()

    async def report(self, mint: str) -> dict[str, Any] | None:
        data = await self.api.get(f"/v1/tokens/{mint}/report", allow_404=True)
        return data if isinstance(data, dict) else None

    async def summary(self, mint: str) -> dict[str, Any] | None:
        data = await self.api.get(f"/v1/tokens/{mint}/report/summary", allow_404=True)
        return data if isinstance(data, dict) else None

    # ----------------------------------------------------------------------------
    @staticmethod
    def apply_report(
        snap: TokenSnapshot, rep: dict[str, Any] | None, extra_non_holders: set[str] | None = None
    ) -> TokenSnapshot:
        if not rep:
            return snap
        extra = {a for a in (extra_non_holders or set()) if a}
        if snap.pair_address:
            extra.add(snap.pair_address)

        if "mintAuthority" in rep and snap.sources.get("mint_authority") != "onchain":
            snap.mint_authority_revoked = not bool(rep.get("mintAuthority"))
            snap.sources["mint_authority"] = "rugcheck"
        if "freezeAuthority" in rep and snap.sources.get("freeze_authority") != "onchain":
            snap.freeze_authority_revoked = not bool(rep.get("freezeAuthority"))
            snap.sources["freeze_authority"] = "rugcheck"
        if snap.sources.get("onchain_security") != "rpc":
            snap.token_program = rep.get("tokenProgram") or snap.token_program
        if rep.get("creator"):
            snap.deployer = rep.get("creator")
        if isinstance(rep.get("rugged"), bool):
            snap.rugged_flag = rep["rugged"]

        # Token-2022 extensions
        ext = ((rep.get("token_extensions") or rep.get("tokenExtensions")) or {})
        found = []
        if isinstance(ext, dict):
            for k, v in ext.items():
                key = k.replace("_", "").lower()
                if key in DANGEROUS_EXTENSIONS and extension_active(k, v):
                    found.append(DANGEROUS_EXTENSIONS[key])
        if found:
            snap.dangerous_extensions = sorted(set(snap.dangerous_extensions) | set(found))

        risks = rep.get("risks") or []
        if isinstance(risks, list):
            snap.rugcheck_risks = [
                {
                    "name": r.get("name"),
                    "level": (r.get("level") or "").lower(),
                    "description": r.get("description"),
                    "score": inum(r.get("score")),
                }
                for r in risks
                if isinstance(r, dict)
            ]
        norm = fnum(rep.get("score_normalised"))
        if norm is not None:
            snap.rugcheck_score_norm = norm

        # LP lock (max over markets)
        lp_vals = []
        for m in rep.get("markets") or []:
            lp = (m or {}).get("lp") or {}
            v = fnum(lp.get("lpLockedPct"))
            if v is not None:
                lp_vals.append(v)
        if lp_vals:
            snap.lp_locked_pct = max(lp_vals)
            for m in rep.get("markets") or []:
                for key in ("pubkey", "liquidityA", "liquidityB"):
                    if (m or {}).get(key):
                        extra.add(m[key])

        # Known accounts (AMM vaults, lockers...) are excluded from concentration
        known = rep.get("knownAccounts") or {}
        non_holders = set(extra)
        if isinstance(known, dict):
            for addr, meta in known.items():
                t = ((meta or {}).get("type") or "").lower()
                if t in NON_HOLDER_TYPES or "amm" in t:
                    non_holders.add(addr)

        holders = rep.get("topHolders") or []
        holder_wallets: list[str] = []  # real holders (pools excluded): used for the on-chain sell simulation
        pcts = []
        insider_pct = 0.0
        insider_seen = False
        creator = snap.deployer
        dev_pct = None
        for h in holders:
            if not isinstance(h, dict):
                continue
            addr, owner = h.get("address"), h.get("owner")
            if addr in non_holders or owner in non_holders:
                continue
            pct = fnum(h.get("pct"))
            if pct is None:
                continue
            pcts.append(pct)
            if owner and pct > 0 and len(holder_wallets) < 5:
                holder_wallets.append(owner)
            if h.get("insider") is True:
                insider_pct += pct
                insider_seen = True
            if creator and owner == creator:
                dev_pct = (dev_pct or 0.0) + pct
        if holder_wallets:
            snap.onchain["holder_wallets"] = holder_wallets
        if pcts:
            pcts.sort(reverse=True)
            snap.top1_pct = pcts[0]
            snap.top10_pct = sum(pcts[:10])
            snap.sources["holders"] = "rugcheck"
        if insider_seen or "graphInsidersDetected" in rep:
            snap.insider_cluster_pct = insider_pct
        if dev_pct is not None:
            snap.dev_pct = dev_pct
        elif creator and pcts:
            snap.dev_pct = 0.0  # creator not among top holders

        th = inum(rep.get("totalHolders"))
        if th is not None:
            snap.holders_count = th
        snap.sources["security"] = "rugcheck"
        return snap
