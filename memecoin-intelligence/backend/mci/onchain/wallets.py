"""Wallet intelligence from public RPC data: who funded the early buyers, which of them are linked.

Only FACTUAL links are used to build clusters (no arbitrary weights):

* same funder: two early buyers received their first SOL from the same wallet (that is not a "hub");
* funded by the creator: an early buyer's first SOL came from the token creator;
* funded by another early buyer.

A "hub" is a funder with very high activity (>= 1000 transactions within 6 hours, measured with one
``getSignaturesForAddress`` page): exchanges, bridges and services fund thousands of unrelated wallets, so a
shared hub is NOT evidence of coordination. Known limitation (documented): wallets funded through an exchange
withdrawal or several hops are not linked; the cluster share is therefore a lower bound.

Cost control: profiles are cached in the database for 7 days, hubs for 1 day; every RPC call goes through the
pool budgets, and a lookup that is refused by the budget simply leaves the wallet "non analizzato".
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from mci.chain.rpc_pool import RpcPool
from mci.chain.tx import funding_transfer
from mci.database.session import session_scope
from mci.domain import utcnow
from mci.utils.http import SourceUnavailable

log = logging.getLogger(__name__)

SIG_PAGE = 100
HUB_PAGE = 1000
HUB_SPAN_S = 6 * 3600
FRESH_DAYS = 3
PROFILE_TTL = timedelta(days=7)
HUB_TTL = timedelta(days=1)


def _ts(x: Any) -> datetime | None:
    try:
        return datetime.fromtimestamp(int(x), tz=timezone.utc) if x else None
    except (TypeError, ValueError, OSError):
        return None


class WalletIntel:
    def __init__(self, rpc: RpcPool):
        self.rpc = rpc
        self._mem: dict[str, dict[str, Any]] = {}
        self._hubs: dict[str, tuple[bool, datetime]] = {}
        self.stats = {"profiled": 0, "cache_hits": 0, "skipped_budget": 0, "errors": 0, "hub_checks": 0}

    # ------------------------------------------------------------------ cache
    def _load(self, addresses: list[str]) -> None:
        from sqlalchemy import select

        from mci.database.models import WalletProfile

        need = [a for a in addresses if a not in self._mem]
        if not need:
            return
        with session_scope() as s:
            for row in s.scalars(select(WalletProfile).where(WalletProfile.address.in_(need))).all():
                checked = row.checked_at if row.checked_at.tzinfo else row.checked_at.replace(tzinfo=timezone.utc)
                if utcnow() - checked > PROFILE_TTL:
                    continue
                self._mem[row.address] = {
                    "address": row.address, "n_signatures": row.n_signatures, "history_capped": row.history_capped,
                    "first_tx_at": row.first_tx_at, "funder": row.funder, "funded_lamports": row.funded_lamports,
                    "funded_at": row.funded_at, "is_hub": row.is_hub, "checked_at": checked,
                }

    def _save(self, p: dict[str, Any]) -> None:
        from mci.database.models import WalletProfile

        with session_scope() as s:
            row = s.get(WalletProfile, p["address"])
            if row is None:
                row = WalletProfile(address=p["address"])
                s.add(row)
            for k in ("n_signatures", "history_capped", "first_tx_at", "funder", "funded_lamports", "funded_at",
                      "is_hub"):
                setattr(row, k, p.get(k))
            row.checked_at = p["checked_at"]

    # ------------------------------------------------------------------ lookups
    async def profile(self, address: str) -> dict[str, Any] | None:
        """Facts about one wallet; None when it could not be analysed now (budget / RPC error)."""
        self._load([address])
        if address in self._mem:
            self.stats["cache_hits"] += 1
            return self._mem[address]
        try:
            sigs = await self.rpc.signatures(address, limit=SIG_PAGE)
            p: dict[str, Any] = {"address": address, "n_signatures": len(sigs), "history_capped": len(sigs) >= SIG_PAGE,
                                 "first_tx_at": None, "funder": None, "funded_lamports": None, "funded_at": None,
                                 "is_hub": None, "checked_at": utcnow()}
            if sigs and not p["history_capped"]:
                oldest = sigs[-1]
                p["first_tx_at"] = _ts(oldest.get("blockTime"))
                tx = await self.rpc.transaction(oldest["signature"])
                if tx:
                    ft = funding_transfer(tx, address)
                    if ft:
                        p["funder"], p["funded_lamports"] = ft.source, ft.lamports
                        p["funded_at"] = _ts(tx.get("blockTime"))
        except SourceUnavailable as e:
            key = "skipped_budget" if "budget" in str(e) else "errors"
            self.stats[key] += 1
            return None
        self._mem[address] = p
        self.stats["profiled"] += 1
        try:
            self._save(p)
        except Exception:
            log.exception("wallet profile not saved")
        return p

    async def is_hub(self, address: str) -> bool | None:
        hit = self._hubs.get(address)
        if hit and utcnow() - hit[1] < HUB_TTL:
            return hit[0]
        try:
            sigs = await self.rpc.signatures(address, limit=HUB_PAGE)
        except SourceUnavailable:
            return None
        self.stats["hub_checks"] += 1
        hub = False
        if len(sigs) >= HUB_PAGE:
            newest, oldest = sigs[0].get("blockTime"), sigs[-1].get("blockTime")
            hub = bool(newest and oldest and newest - oldest <= HUB_SPAN_S)
        self._hubs[address] = (hub, utcnow())
        return hub

    def health(self) -> dict[str, Any]:
        return {**self.stats, "cached": len(self._mem), "hubs_known": sum(1 for v, _ in self._hubs.values() if v)}

    # ------------------------------------------------------------------ analysis
    async def analyze_early_buyers(self, buyers: list[dict[str, Any]], creator: str | None, total_supply: int,
                                   creation_slot: int | None, max_new: int = 10) -> dict[str, Any]:
        """Profile the early buyers (at most ``max_new`` RPC lookups) and build factual funding clusters."""
        self._load([b["wallet"] for b in buyers])
        profiles: dict[str, dict[str, Any]] = {}
        new = 0
        for b in buyers:
            w = b["wallet"]
            if w in self._mem:
                profiles[w] = self._mem[w]
                continue
            if new >= max_new:
                continue
            new += 1
            p = await self.profile(w)
            if p:
                profiles[w] = p
        funders = {p["funder"] for p in profiles.values() if p.get("funder")}
        hubs: set[str] = set()
        shared = [f for f in funders if sum(1 for p in profiles.values() if p.get("funder") == f) >= 2]
        for f in shared[:5]:
            if await self.is_hub(f):
                hubs.add(f)
        return cluster_early_buyers(buyers, profiles, creator, hubs, total_supply, creation_slot)


def cluster_early_buyers(buyers: list[dict[str, Any]], profiles: dict[str, dict[str, Any]], creator: str | None,
                         hubs: set[str], total_supply: int, creation_slot: int | None) -> dict[str, Any]:
    parent = {b["wallet"]: b["wallet"] for b in buyers}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    wallets = set(parent)
    by_funder: dict[str, list[str]] = {}
    evidence: list[dict[str, str]] = []
    creator_linked: set[str] = set()
    for w, p in profiles.items():
        f = p.get("funder")
        if not f or w not in wallets:
            continue
        if creator and f == creator:
            creator_linked.add(w)
            evidence.append({"wallet": w, "link": "finanziato dal creatore"})
        if f in wallets:
            union(w, f)
            evidence.append({"wallet": w, "link": f"finanziato da un altro early buyer ({f[:6]}…)"})
        if f not in hubs:
            by_funder.setdefault(f, []).append(w)
    for f, ws in by_funder.items():
        if len(ws) >= 2:
            for w in ws[1:]:
                union(ws[0], w)
            evidence.append({"wallet": ",".join(x[:6] for x in ws), "link": f"stesso finanziatore {f[:6]}…"})
    groups: dict[str, list[str]] = {}
    for w in wallets:
        groups.setdefault(find(w), []).append(w)
    info = {b["wallet"]: b for b in buyers}

    def net_pct(ws: list[str] | set[str]) -> float:
        return round(sum(max(int(info[w]["net_tokens"]), 0) for w in ws if w in info) / (total_supply or 1) * 100, 3)

    clusters = sorted(
        ({"wallets": ws, "size": len(ws), "net_pct": net_pct(ws),
          "buy_sol": round(sum(info[w]["buy_sol"] for w in ws) / 1e9, 4),
          "creator_linked": any(w in creator_linked for w in ws)}
         for ws in groups.values() if len(ws) >= 2),
        key=lambda c: c["net_pct"], reverse=True,
    )
    clustered = {w for c in clusters for w in c["wallets"]} | creator_linked
    block0 = {b["wallet"] for b in buyers if creation_slot is not None and b.get("first_slot") == creation_slot}
    coordinated = clustered | block0
    fresh = [p for p in profiles.values()
             if p.get("first_tx_at") and not p.get("history_capped")
             and (utcnow() - p["first_tx_at"]).total_seconds() < FRESH_DAYS * 86400]
    coverage = len(profiles) / len(buyers) if buyers else 0.0
    total_buy = sum(b["buy_sol"] for b in buyers) or 0
    return {
        "early_buyers": len(buyers),
        "profiled": len(profiles),
        "coverage": round(coverage, 3),
        "clusters": clusters[:10],
        "clustered_wallets": len(clustered),
        "creator_linked_wallets": len(creator_linked),
        "creator_linked_pct": net_pct(creator_linked),
        "largest_cluster_pct": clusters[0]["net_pct"] if clusters else 0.0,
        "block0_wallets": len(block0),
        "coordinated_pct": net_pct(coordinated),
        "coordinated_buy_share": round(sum(info[w]["buy_sol"] for w in coordinated) / total_buy, 3) if total_buy else None,
        "independent_buyers": len(set(info) - coordinated),
        "fresh_wallets": len(fresh),
        "fresh_share": round(len(fresh) / len(profiles), 3) if profiles else None,
        "hubs_ignored": sorted(hubs),
        "evidence": evidence[:20],
    }


def deployer_history(creator: str | None, before: datetime, days: int = 30,
                     exclude_mint: str | None = None) -> dict[str, Any] | None:
    """Previous launches of the same creator seen by our own stream (facts from the database)."""
    if not creator:
        return None
    from sqlalchemy import func, select

    from mci.database.models import FeatureSnapshot, PumpLaunch

    since = before - timedelta(days=days)
    with session_scope() as s:
        rows = s.execute(select(PumpLaunch.mint, PumpLaunch.created_at, PumpLaunch.complete_at)
                         .where(PumpLaunch.creator == creator, PumpLaunch.created_at < before,
                                PumpLaunch.created_at >= since, PumpLaunch.mint != (exclude_mint or ""))).all()
        first_seen = s.scalar(select(func.min(PumpLaunch.created_at)))
        mints = [r[0] for r in rows]
        rugs = labeled = 0
        if mints:
            for lab in s.scalars(select(FeatureSnapshot.labels).where(FeatureSnapshot.token_address.in_(mints[:200]),
                                                                       FeatureSnapshot.horizon == "t+5m",
                                                                       FeatureSnapshot.labels.is_not(None))).all():
                labeled += 1
                rugs += 1 if (lab or {}).get("rug_60m") else 0
    if first_seen is not None and first_seen.tzinfo is None:
        first_seen = first_seen.replace(tzinfo=timezone.utc)

    def aware(d: datetime) -> datetime:
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)

    return {
        "launches_30d": len(rows),
        "launches_24h": sum(1 for r in rows if aware(r[1]) >= before - timedelta(hours=24)),
        "migrated": sum(1 for r in rows if r[2] is not None),
        "labeled": labeled,
        "rug_share": round(rugs / labeled, 3) if labeled else None,
        # how much history we have: with few days of collection a "0 previous launches" is weak evidence
        "observed_days": round((before - first_seen).total_seconds() / 86400, 2) if first_seen else 0.0,
    }
