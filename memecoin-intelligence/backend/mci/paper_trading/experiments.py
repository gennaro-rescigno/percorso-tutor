"""Shadow experiments: virtual portfolios that test a change WITHOUT touching the main portfolio.

* ``x_safe``  - same strategies and candidates as the Laboratorio, but the shadow rules are applied
  (tokens hit by HIGH_RISK_INDEX / COORDINATED_SUPPLY / CREATOR_SOLD / SERIAL_DEPLOYER are skipped).
  Comparing x_safe with the Laboratorio measures what those rules are worth.
* ``x_curve`` - the experimental "O - Curva organica" strategy on pump.fun launches observed on the free chain
  stream, 2-15 minutes after creation, with fills on the exact bonding-curve constant product.

Both never send messages and never affect /pause, /kill or the main portfolio's limits.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

from mci.chain.rpc_pool import BudgetExceeded
from mci.config import Settings
from mci.domain import TokenSnapshot, utcnow
from mci.execution.costs import CostModel
from mci.onchain.curve_features import curve_features
from mci.paper_trading.lab import LabEngine
from mci.scanner.service import Scanner, TrackedToken
from mci.scoring.filters import FilterConfig
from mci.scoring.scorer import score_token
from mci.strategies.curve import OrganicCurve
from mci.utils.http import SourceUnavailable

log = logging.getLogger(__name__)

EXPERIMENTS = {
    "x_safe": {"title": "Laboratorio + regole shadow",
               "hypothesis": "escludere i token segnalati dalle regole shadow migliora il rendimento per operazione"},
    "x_curve": {"title": "Curva organica (nuova strategia)",
                "hypothesis": "la domanda ampia e indipendente nei primi minuti sulla curva prosegue abbastanza da "
                              "superare i costi"},
}
# launchpad tokens are small by design: the dedicated filter keeps every safety rule, lowers only size limits
CURVE_FILTERS = FilterConfig(min_liquidity_usd=3_000.0, min_age_minutes=2.0, max_top10_pct=35.0, max_top1_pct=10.0)


class SafeRulesExperiment(LabEngine):
    version = 1

    def __init__(self, settings: Settings, scanner: Scanner, costs: CostModel, **kw: Any):
        super().__init__(settings, scanner, costs, mode="x_safe", **kw)

    def gate(self, tt: TrackedToken) -> bool:
        hits = ((tt.snapshot.onchain or {}).get("risk") or {}).get("shadow_hits") or []
        if not hits:
            return True
        from mci.database.session import session_scope

        with session_scope() as s:
            self._count_skip(s, "regola shadow: " + ", ".join(hits))
        return False


class CurveExperiment(LabEngine):
    version = 1

    def __init__(self, settings: Settings, scanner: Scanner, costs: CostModel, **kw: Any):
        super().__init__(settings, scanner, costs, mode="x_curve", strategies=[OrganicCurve()], **kw)
        self.tokens: dict[str, TrackedToken] = {}
        self.last_candidates = 0

    @property
    def onchain(self):
        return self.scanner.onchain

    def _snapshot(self, st, f: dict[str, Any], sol_usd: float | None) -> TokenSnapshot:
        now = utcnow()
        snap = TokenSnapshot(chain="solana", token_address=st.mint, observed_at=now, symbol=st.symbol, name=st.name,
                             dex_id="pumpfun", bonding_curve=True, deployer=st.creator,
                             created_at=datetime.fromtimestamp(st.created_ts, tz=timezone.utc), quote_symbol="SOL")
        last = st.last
        snap.price_native = f.get("price")
        if last is not None:
            snap.liquidity_quote = last.vsol / 1e9  # constant product on the virtual SOL reserve (pump.fun curve)
            snap.v_sol_in_curve = snap.liquidity_quote
        if sol_usd and snap.price_native:
            snap.price_usd = snap.price_native * sol_usd
            snap.market_cap_usd = snap.price_usd * (st.total_supply / 1e6)
            snap.fdv_usd = snap.market_cap_usd
        if sol_usd and snap.liquidity_quote:
            snap.liquidity_usd = 2 * snap.liquidity_quote * sol_usd
        snap.mayhem = st.mayhem
        snap.bonding_progress_pct = f.get("progress_pct")
        snap.holders_count = f.get("holders_net")
        snap.top10_pct, snap.top1_pct, snap.dev_pct = f.get("top10_net_pct"), f.get("top1_net_pct"), f.get("creator_net_pct")
        snap.buyers = {"m5": f.get("unique_buyers")}
        snap.sources.update({"price": "chain_stream", "holders": "chain_stream", "curve_features": "chain_stream"})
        snap.onchain["curve"] = f
        return snap

    async def on_scan(self, candidates: list[TrackedToken]) -> None:
        oc = self.onchain
        if oc is None:
            return
        fxp = self.scanner.fx.last
        sol_usd = fxp.usd if fxp else None
        now = time.time()
        pre = []
        for st in list(oc.tracker.launches.values()):
            if st.source != "stream" or st.complete_ts or not (120 <= now - st.created_ts <= 900):
                continue
            f = curve_features(st, now, oc.tracker)
            if OrganicCurve.precheck(f):
                pre.append((st, f))
        pre.sort(key=lambda x: x[1]["unique_buyers"], reverse=True)
        out = []
        for st, f in pre[:5]:
            tt = self.tokens.get(st.mint)
            snap = self._snapshot(st, f, sol_usd)
            if tt is None:
                tt = self.tokens[st.mint] = TrackedToken(st.mint, snap, utcnow(), "chain_stream")
            else:  # keep the cached security verdict
                for k in ("mint_authority_revoked", "freeze_authority_revoked", "onchain_findings", "metadata_mutable",
                          "token_program"):
                    setattr(snap, k, getattr(tt.snapshot, k))
                snap.sources.update({k: v for k, v in tt.snapshot.sources.items() if k not in snap.sources})
                tt.snapshot = snap
            if tt.due("onchain_sec", 3600):
                try:
                    await oc.security(snap)
                    tt.mark("onchain_sec")
                except (BudgetExceeded, SourceUnavailable):
                    pass
            if "onchain_security" in snap.sources and not any(x.get("blocking") for x in snap.onchain_findings) \
                    and snap.freeze_authority_revoked:
                # on the curve the program itself always buys back: the sell route exists unless the token is frozen
                snap.sell_route_ok = True
                snap.sources["sell_route"] = "bonding_curve"
            try:
                snap.onchain["deployer"] = oc.deployer(snap)
            except Exception:
                log.exception("deployer history failed")
            oc.indices(snap)
            tt.candles["1m"] = oc.tracker.candles(st.mint, sol_usd)
            tt.candle_source["1m"] = "stream"
            tt.score = score_token(snap, tt.candles["1m"], CURVE_FILTERS)
            tt.trade_score = score_token(snap, tt.candles["1m"], CURVE_FILTERS, for_trading=True)
            out.append(tt)
        self.last_candidates = len(out)
        for m in [m for m, tt in self.tokens.items() if m not in oc.tracker.launches]:
            del self.tokens[m]
        await super().on_scan(out)

    async def monitor_positions(self) -> None:
        """Curve positions are priced from the chain stream (exact, real time); after migration, DexScreener."""
        from mci.database import repo
        from mci.database.session import session_scope

        oc = self.onchain
        with session_scope() as s:
            positions = [(p.id, p.token_address) for p in repo.open_positions(s, self.mode)]
        rest: list[tuple[int, str]] = []
        for pid, token in positions:
            st = oc.tracker.get(token) if oc else None
            live = oc.tracker.price(token) if oc else None
            if st is not None and live and not st.complete_ts and st.last is not None:
                await self._check_exit(pid, live[0], st.last.vsol / 1e9, None)
            else:
                rest.append((pid, token))
        if not rest:
            return
        from mci.collectors.dexscreener import DexScreenerCollector

        try:  # migrated (or no longer streamed) tokens: DexScreener price, as the other portfolios
            pairs = await self.scanner.dex.pairs_for_tokens(self.s.chain, [t for _, t in rest])
            best = DexScreenerCollector.best_pair_per_token(pairs, self.s.chain)
        except SourceUnavailable:
            return
        fxp = self.scanner.fx.last
        sol_usd = fxp.usd if fxp else None
        for pid, token in rest:
            pair = best.get(token)
            if not pair:
                continue
            snap = DexScreenerCollector.pair_to_snapshot(pair)
            px = snap.price_native or (snap.price_usd / sol_usd if snap.price_usd and sol_usd else None)
            reserve = snap.liquidity_quote or (snap.liquidity_usd / 2 / sol_usd if snap.liquidity_usd and sol_usd else None)
            if px:
                await self._check_exit(pid, px, reserve, None)
