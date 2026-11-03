"""On-chain enrichment of scanner candidates (own security checks, curve state, stream features, wallets).

Called by the scanner for each candidate, with per-token caching. Every RPC call goes through the pool budgets;
when a check cannot run, the related fields stay None ("non verificato"), which the trading filters treat as
missing data, never as safe.
"""

from __future__ import annotations

import base64
import logging
import time
from typing import Any

from mci.chain import pump
from mci.chain.pda import metaplex_metadata_address, pump_bonding_curve_address
from mci.chain.rpc_pool import RpcPool
from mci.chain.tokens import TOKEN_PROGRAM, MintSecurity, analyze_mint, apply_metaplex
from mci.database import repo
from mci.database.session import session_scope
from mci.domain import TokenSnapshot, utcnow
from mci.onchain.curve_features import curve_features, early_buyers
from mci.onchain.launches import LaunchTracker
from mci.onchain.wallets import WalletIntel, deployer_history
from mci.scoring.risk_opportunity import opportunity_index, risk_index
from mci.utils.http import SourceUnavailable

log = logging.getLogger(__name__)

# codes already handled by dedicated filters (mint / freeze authority)
_DEDICATED = {"MINT_AUTHORITY_ACTIVE", "FREEZE_AUTHORITY_ACTIVE"}


def apply_security(snap: TokenSnapshot, sec: MintSecurity) -> list[str]:
    """Write the own on-chain verdict into the snapshot (on-chain wins over third parties).

    Returns the disagreements with the previous (RugCheck) values, for the data-quality log."""
    diffs = []
    if not sec.complete and not sec.findings:
        return diffs
    if sec.complete:
        mint_ok = sec.mint_authority is None
        frz_ok = sec.freeze_authority is None
        if snap.mint_authority_revoked is not None and snap.mint_authority_revoked != mint_ok \
                and snap.sources.get("mint_authority") != "onchain":
            diffs.append(f"mint authority: {snap.sources.get('mint_authority', '?')}="
                         f"{'revocata' if snap.mint_authority_revoked else 'attiva'}, on-chain={'revocata' if mint_ok else 'attiva'}")
        if snap.freeze_authority_revoked is not None and snap.freeze_authority_revoked != frz_ok \
                and snap.sources.get("freeze_authority") != "onchain":
            diffs.append(f"freeze authority: {snap.sources.get('freeze_authority', '?')}="
                         f"{'revocata' if snap.freeze_authority_revoked else 'attiva'}, on-chain={'revocata' if frz_ok else 'attiva'}")
        snap.mint_authority_revoked, snap.freeze_authority_revoked = mint_ok, frz_ok
        snap.sources["mint_authority"] = snap.sources["freeze_authority"] = "onchain"
        snap.token_program = sec.program
        snap.metadata_mutable = sec.metadata_mutable
    snap.onchain_findings = [
        {"code": f.code, "severity": f.severity, "message": f.message,
         "blocking": f.blocking and f.code not in _DEDICATED}
        for f in sec.findings
    ]
    snap.sources["onchain_security"] = "rpc"
    return diffs


class OnchainService:
    def __init__(self, rpc: RpcPool, tracker: LaunchTracker, wallets: WalletIntel | None = None):
        self.rpc = rpc
        self.tracker = tracker
        self.wallets = wallets or WalletIntel(rpc)
        self.discrepancies = 0
        self._reported: set[str] = set()
        self.stats = {"security_checks": 0, "curve_reads": 0, "wallet_analyses": 0, "errors": 0,
                      "sell_sims": 0, "sell_sim_ok": 0, "sell_sim_blocked": 0, "sell_sim_unverified": 0}
        self.last_sell_sim: str | None = None

    async def security(self, snap: TokenSnapshot) -> None:
        mint = snap.token_address
        acc = await self.rpc.account(mint, "jsonParsed")
        sec = analyze_mint(mint, acc)
        if sec.complete and sec.program == TOKEN_PROGRAM:
            # classic SPL token: name/symbol/uri and mutability live in the Metaplex metadata account
            try:
                apply_metaplex(sec, await self.rpc.account(metaplex_metadata_address(mint), "base64"))
            except SourceUnavailable:
                pass
        self.stats["security_checks"] += 1
        diffs = apply_security(snap, sec)
        if diffs:
            self.discrepancies += 1
            if mint not in self._reported:
                self._reported.add(mint)
                with session_scope() as s:
                    repo.log_event(s, "data", f"{snap.symbol or mint[:8]}: RugCheck e blockchain non concordano ("
                                   + "; ".join(diffs) + "): vale il dato on-chain", level="warn", token=mint)

    async def curve_state(self, snap: TokenSnapshot) -> None:
        """Read the pump.fun bonding-curve account: real reserves, progress, completion, mayhem flag."""
        acc = await self.rpc.account(pump_bonding_curve_address(snap.token_address), "base64")
        self.stats["curve_reads"] += 1
        if not acc or acc.get("owner") != pump.PUMP_PROGRAM_ID:
            return  # not a pump.fun token (or curve closed): nothing to say
        data = acc.get("data")
        try:
            st = pump.decode_bonding_curve(base64.b64decode(data[0]))
        except (ValueError, TypeError, IndexError):
            return
        snap.mayhem = st.is_mayhem_mode
        snap.social_metrics["curve_complete"] = st.complete
        if st.complete:
            snap.bonding_curve = False
            return
        snap.bonding_curve = True
        snap.v_sol_in_curve = st.virtual_quote_reserves / 1e9
        init = 793_100_000 * 10**6
        snap.bonding_progress_pct = round(max(0.0, min(100.0, (init - st.real_token_reserves) / init * 100)), 2)
        snap.sources["curve"] = "onchain"

    def stream_view(self, snap: TokenSnapshot) -> dict[str, Any] | None:
        """Point-in-time curve features of a launch observed on the chain stream (None if not observed)."""
        st = self.tracker.get(snap.token_address)
        if st is None or st.source == "trade":
            if snap.bonding_curve or snap.token_address.endswith("pump"):
                self.tracker.watch_mint(snap.token_address)  # candles and live price from the stream
            return None
        f = curve_features(st, time.time(), self.tracker)
        if st.mayhem is not None:
            snap.mayhem = st.mayhem
        if st.creator and not snap.deployer:
            snap.deployer = st.creator
        return f

    async def analyze_wallets(self, snap: TokenSnapshot, max_new: int = 10) -> dict[str, Any] | None:
        st = self.tracker.get(snap.token_address)
        if st is None or st.source == "trade" or not st.trades:
            return None
        buyers = early_buyers(st, st.created_ts + 300)
        if not buyers:
            return None
        res = await self.wallets.analyze_early_buyers(buyers, st.creator, st.total_supply, st.slot, max_new=max_new)
        self.stats["wallet_analyses"] += 1
        return res

    def indices(self, snap: TokenSnapshot) -> None:
        oc = snap.onchain
        r = risk_index(snap, oc.get("curve"), oc.get("wallets"), oc.get("deployer"))
        o = opportunity_index(snap, oc.get("curve"), oc.get("wallets"))
        oc["risk"], oc["opportunity"] = r.to_dict(), o.to_dict()

    def health(self) -> dict[str, Any]:
        return {**self.stats, "rugcheck_disagreements": self.discrepancies, "last_sell_sim": self.last_sell_sim,
                "wallets": self.wallets.health(),
                "rpc": self.rpc.health(), "launches": self.tracker.health()}

    @staticmethod
    def deployer(snap: TokenSnapshot) -> dict[str, Any] | None:
        h = deployer_history(snap.deployer, snap.created_at or utcnow(), exclude_mint=snap.token_address)
        if h is not None:
            snap.deployer_token_count = h["launches_30d"]
        return h
