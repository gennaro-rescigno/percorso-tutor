"""Market scanner: discovery -> market update -> candidate enrichment -> scoring -> recording.

Budget-aware design for FREE rate limits:
* DexScreener (pairs, 300 rpm): market data for every tracked token, in batches of 30;
* GeckoTerminal (30 rpm): new/trending pools + rotating enrichment of a few candidates
  per cycle (pool windows with unique buyers, trades for wash metrics, OHLCV candles);
* RugCheck: security report per candidate, cached;
* Jupiter (0.5 RPS keyless): batch prices (divergence check) + sell-probe quotes, cached.

EVERY discovered token is recorded with point-in-time snapshots, including the ones
that are excluded or later die, to build a survivorship-bias-free dataset.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from mci.collectors.dexscreener import DexScreenerCollector
from mci.collectors.fx import SolPriceFeed
from mci.collectors.geckoterminal import GeckoTerminalCollector
from mci.collectors.jupiter import JupiterCollector
from mci.collectors.pumpportal import event_to_snapshot
from mci.collectors.rugcheck import RugCheckCollector
from mci.collectors.social import RedditCollector
from mci.config import Settings
from mci.database import repo
from mci.database.session import session_scope
from mci.domain import Candle, ScoreResult, TokenSnapshot, to_utc, utcnow
from mci.onchain.wash import wash_metrics
from mci.scoring.scorer import score_token
from mci.utils.http import SourceUnavailable

log = logging.getLogger(__name__)

SNAPSHOT_EVERY_CANDIDATE_S = 300
SNAPSHOT_EVERY_OTHER_S = 1800
DEAD_LIQUIDITY_USD = 1_000.0


@dataclass
class TrackedToken:
    address: str
    snapshot: TokenSnapshot
    first_seen: datetime
    source: str
    score: ScoreResult | None = None
    trade_score: ScoreResult | None = None  # for_trading=True evaluation
    history: deque = field(default_factory=lambda: deque(maxlen=96))  # recent snapshots (5 min spacing)
    candles: dict[str, list[Candle]] = field(default_factory=dict)
    last_enriched: dict[str, float] = field(default_factory=dict)
    last_recorded: float = 0.0
    low_liq_since: float | None = None
    pump_trades: deque = field(default_factory=lambda: deque(maxlen=500))

    def due(self, key: str, every_s: float) -> bool:
        return time.time() - self.last_enriched.get(key, 0.0) >= every_s

    def mark(self, key: str) -> None:
        self.last_enriched[key] = time.time()


class Scanner:
    def __init__(
        self,
        settings: Settings,
        dex: DexScreenerCollector,
        gecko: GeckoTerminalCollector,
        rug: RugCheckCollector,
        jup: JupiterCollector,
        fx: SolPriceFeed,
        reddit: RedditCollector | None = None,
    ):
        self.s = settings
        self.dex, self.gecko, self.rug, self.jup, self.fx = dex, gecko, rug, jup, fx
        self.reddit = reddit
        self.tokens: dict[str, TrackedToken] = {}
        self.realtime_queue: asyncio.Queue[TokenSnapshot] = asyncio.Queue(maxsize=5000)
        self.source_status: dict[str, dict[str, Any]] = {}
        self.cycle = 0
        self.last_cycle_at: datetime | None = None
        self.sol_usd_hist: deque = deque(maxlen=120)
        self._gecko_paused_until = 0.0
        self._gecko_strikes = 0
        self._gecko_ok_streak = 0
        lim = self._gecko_limiter()
        self._gecko_max_rate = lim.rate if lim else 0.0

    # ------------------------------------------------------------------ helpers
    def _ok(self, name: str) -> None:
        self.source_status[name] = {"ok": True, "at": utcnow().isoformat()}
        if name == "geckoterminal":
            self._gecko_success()

    def _fail(self, name: str, err: Exception) -> None:
        self.source_status[name] = {"ok": False, "at": utcnow().isoformat(), "error": str(err)[:200]}
        log.info("source %s failed: %s", name, err)

    async def on_pumpportal_event(self, ev: dict[str, Any]) -> None:
        """Called by PumpPortalListener for new tokens, migrations and subscribed trades."""
        snap = event_to_snapshot(ev)
        if snap is None:
            return
        tx = ev.get("txType")
        if tx in ("buy", "sell") and snap.token_address in self.tokens:
            self.tokens[snap.token_address].pump_trades.append(
                {"ts": utcnow(), "wallet": ev.get("traderPublicKey"), "side": tx,
                 "usd": (float(ev.get("solAmount") or 0) * (self.fx.last.usd if self.fx.last and self.fx.last.usd else 0)),
                 "token_amount": ev.get("tokenAmount")}
            )
            return
        if tx == "migrate" or ev.get("pool") == "pump-amm":
            snap.bonding_curve = False
            snap.migrated_at = utcnow()
        try:
            self.realtime_queue.put_nowait(snap)
        except asyncio.QueueFull:
            pass

    def gecko_paused(self) -> bool:
        return time.time() < self._gecko_paused_until

    def _gecko_limiter(self):
        return getattr(getattr(self.gecko, "api", None), "limiter", None)

    def pause_gecko(self, err: Exception, seconds: float = 90.0) -> None:
        """GeckoTerminal does not publish its public limit and enforces it per IP. On every 429: pause with
        exponential backoff (90 s, 3, 6, ... up to 15 min) and halve our request rate (no bursts), so the rate
        settles below the real limit; successes then raise it slowly again (see ``_gecko_success``)."""
        if "429" in str(err) or "circuit open" in str(err):
            self._gecko_strikes += 1
            self._gecko_ok_streak = 0
            pause = min(seconds * 2 ** (self._gecko_strikes - 1), 900.0)
            self._gecko_paused_until = time.time() + pause
            lim = self._gecko_limiter()
            if lim:
                lim.rate = max(lim.rate / 2, 2 / 60)
                lim.capacity = 1.0
                lim._tokens = min(lim._tokens, 1.0)
            log.info("geckoterminal 429: pausa %.0f s, nuovo ritmo %.1f chiamate/min", pause,
                     (lim.rate * 60) if lim else 0)

    def _gecko_success(self) -> None:
        self._gecko_strikes = 0
        self._gecko_ok_streak += 1
        lim = self._gecko_limiter()
        if lim and self._gecko_ok_streak >= 10 and lim.rate < self._gecko_max_rate:
            lim.rate = min(lim.rate + 1 / 60, self._gecko_max_rate)  # +1 call/min after 10 clean rounds
            self._gecko_ok_streak = 0

    def sol_anomaly(self) -> str | None:
        """Market anomaly: SOL down > 8% within the last hour of samples."""
        if len(self.sol_usd_hist) < 2:
            return None
        now_t, now_p = self.sol_usd_hist[-1]
        past = [p for t, p in self.sol_usd_hist if now_t - t <= 3600]
        if past and now_p < max(past) * 0.92:
            return f"SOL in calo del {1 - now_p / max(past):.0%} nell'ultima ora"
        return None

    def data_outage(self) -> str | None:
        down = [k for k in ("dexscreener",) if self.source_status.get(k, {}).get("ok") is False]
        return f"fonti dati principali non disponibili: {', '.join(down)}" if down else None

    # ------------------------------------------------------------------ discovery
    async def discover(self) -> dict[str, tuple[TokenSnapshot | None, str]]:
        found: dict[str, tuple[TokenSnapshot | None, str]] = {}
        chain = self.s.chain
        try:
            for item in (await self.dex.latest_profiles())[:60]:
                if item.get("chainId") == chain and item.get("tokenAddress"):
                    found.setdefault(item["tokenAddress"], (None, "dexscreener_profile"))
            for item in (await self.dex.latest_boosts())[:60]:
                if item.get("chainId") == chain and item.get("tokenAddress"):
                    found.setdefault(item["tokenAddress"], (None, "dexscreener_boost"))
            self._ok("dexscreener_discovery")
        except SourceUnavailable as e:
            self._fail("dexscreener_discovery", e)
        if self.cycle % 2 == 0 and not self.gecko_paused():
            try:
                for pool in await self.gecko.new_pools(chain):
                    snap = GeckoTerminalCollector.pool_to_snapshot(pool)
                    if snap.token_address:
                        found.setdefault(snap.token_address, (snap, "gecko_new_pools"))
                for pool in await self.gecko.trending_pools(chain):
                    snap = GeckoTerminalCollector.pool_to_snapshot(pool)
                    if snap.token_address:
                        found.setdefault(snap.token_address, (snap, "gecko_trending"))
                self._ok("geckoterminal")
            except SourceUnavailable as e:
                self._fail("geckoterminal", e)
                self.pause_gecko(e)
        while not self.realtime_queue.empty():
            snap = self.realtime_queue.get_nowait()
            found.setdefault(snap.token_address, (snap, "pumpportal"))
        return found

    # ------------------------------------------------------------------ cycle
    async def run_cycle(self) -> list[TrackedToken]:
        self.cycle += 1
        now = utcnow()
        price = await self.fx.get()
        sol_usd = price.usd if price else None
        if sol_usd:
            self.sol_usd_hist.append((time.time(), sol_usd))

        found = await self.discover()
        for addr, (snap, src) in found.items():
            if addr not in self.tokens and len(self.tokens) < self.s.max_tracked_tokens:
                base = snap or TokenSnapshot(chain=self.s.chain, token_address=addr, observed_at=now)
                self.tokens[addr] = TrackedToken(addr, base, now, src)
            elif addr in self.tokens and snap is not None:
                self.tokens[addr].snapshot = snap.merge(self.tokens[addr].snapshot)

        # market update via DexScreener (batches of 30)
        addrs = list(self.tokens)
        try:
            pairs = await self.dex.pairs_for_tokens(self.s.chain, addrs)
            best = DexScreenerCollector.best_pair_per_token(pairs, self.s.chain)
            self._ok("dexscreener")
        except SourceUnavailable as e:
            best = {}
            self._fail("dexscreener", e)
        for addr, tt in self.tokens.items():
            p = best.get(addr)
            if p:
                fresh = DexScreenerCollector.pair_to_snapshot(p, now)
                prev = tt.snapshot
                # keep slow-changing enrichment from the previous snapshot
                for f in ("holders_count", "top1_pct", "top10_pct", "dev_pct", "insider_cluster_pct",
                          "early_buyer_cluster_pct", "mint_authority_revoked", "freeze_authority_revoked",
                          "token_program", "lp_locked_pct", "rugcheck_score_norm", "rugged_flag", "deployer",
                          "sell_route_ok", "sell_impact_pct", "quote_probe_sol", "wash_score", "trades_per_trader",
                          "bonding_curve", "migrated_at"):
                    if getattr(fresh, f) is None and getattr(prev, f) is not None:
                        setattr(fresh, f, getattr(prev, f))
                for f in ("rugcheck_risks", "dangerous_extensions"):
                    if not getattr(fresh, f) and getattr(prev, f):
                        setattr(fresh, f, getattr(prev, f))
                fresh.buyers = {**prev.buyers, **{k: v for k, v in fresh.buyers.items() if v is not None}}
                fresh.sellers = {**prev.sellers, **{k: v for k, v in fresh.sellers.items() if v is not None}}
                if prev.volume_usd.get("m15") is not None and fresh.volume_usd.get("m15") is None:
                    fresh.volume_usd["m15"] = prev.volume_usd["m15"]
                fresh.social_metrics = {**prev.social_metrics, **fresh.social_metrics}
                fresh.sources = {**prev.sources, **fresh.sources}
                if fresh.dex_id and fresh.dex_id not in ("pumpfun", "pump"):
                    fresh.bonding_curve = False
                tt.snapshot = fresh
            else:
                tt.snapshot.observed_at = now
            snap = tt.snapshot
            if snap.liquidity_usd is None and snap.liquidity_quote and sol_usd:
                snap.liquidity_usd = 2 * snap.liquidity_quote * sol_usd
            if snap.liquidity_quote is None and snap.liquidity_usd and sol_usd:
                snap.liquidity_quote = snap.liquidity_usd / 2 / sol_usd
            if snap.price_native is None and snap.price_usd and sol_usd:
                snap.price_native = snap.price_usd / sol_usd

        # preliminary score (market-only) to choose candidates
        for tt in self.tokens.values():
            tt.score = score_token(tt.snapshot, tt.candles.get("1m"))
        candidates = sorted(
            (t for t in self.tokens.values() if not t.score.excluded and (t.snapshot.liquidity_usd or 0) >= self.s.min_liquidity_usd_track),
            key=lambda t: (t.score.total, t.snapshot.liquidity_usd or 0),
            reverse=True,
        )[: self.s.candidate_pool_size]

        await self._enrich(candidates, sol_usd)

        for tt in self.tokens.values():
            tt.score = score_token(tt.snapshot, tt.candles.get("1m"))
            tt.trade_score = score_token(tt.snapshot, tt.candles.get("1m"), for_trading=True)

        self._record(candidates)
        self._prune()
        self.last_cycle_at = utcnow()
        return candidates

    # ------------------------------------------------------------------ enrichment
    async def _enrich(self, candidates: list[TrackedToken], sol_usd: float | None) -> None:
        # Jupiter batch prices for divergence check
        try:
            prices = await self.jup.prices([c.address for c in candidates])
            self._ok("jupiter")
        except SourceUnavailable as e:
            prices = {}
            self._fail("jupiter", e)
        for c in candidates:
            jp = (prices.get(c.address) or {}).get("usd")
            if jp and c.snapshot.price_usd:
                c.snapshot.price_divergence_pct = abs(c.snapshot.price_usd - jp) / jp * 100

        gecko_budget = 6
        for c in candidates:
            snap = c.snapshot
            # security (RugCheck), cached 15 min
            if c.due("rugcheck", 900):
                try:
                    rep = await self.rug.report(c.address)
                    RugCheckCollector.apply_report(snap, rep)
                    c.mark("rugcheck")
                    self._ok("rugcheck")
                except SourceUnavailable as e:
                    self._fail("rugcheck", e)
            # sell probe (honeypot / exit impact), cached 5 min
            if c.due("sell_probe", 300) and snap.price_native:
                probe_sol = 0.1
                tokens_raw = None
                dec = self.jup.known_decimals(c.address)
                if dec is None and (snap.bonding_curve or (snap.dex_id or "") in ("pumpfun", "pumpswap")
                                    or c.address.endswith("pump")):
                    dec = 6  # pump.fun tokens are created with 6 decimals
                if dec is not None:
                    tokens_raw = int(probe_sol / snap.price_native * 10**dec)
                if tokens_raw:
                    try:
                        q = await self.jup.sell_quote(c.address, tokens_raw)
                        snap.sell_route_ok = q is not None and q.out_amount > 0
                        snap.sell_impact_pct = q.price_impact_pct * 100 if q else None
                        snap.quote_probe_sol = probe_sol
                        c.mark("sell_probe")
                    except SourceUnavailable as e:
                        self._fail("jupiter_quote", e)
            # GeckoTerminal rotation. Candles first (strategies need them), then pool windows
            # (unique buyers, m15) and trades (wash metrics). The public API is rate limited per IP
            # (shared IPs on GitHub runners): on the first 429 we stop calling it for a while.
            if gecko_budget > 0 and snap.pair_address and c.due("gecko", 300) and not self.gecko_paused():
                try:
                    candles = await self.gecko.ohlcv(snap.pair_address, "1m", limit=1000, currency="token")
                    gecko_budget -= 1
                    if candles:
                        c.candles["1m"] = candles
                    age = snap.age_minutes or 0
                    if age > 7 * 1440 and c.due("gecko_1h", 1800):
                        # old tokens (Revival strategy) need hourly history
                        hourly = await self.gecko.ohlcv(snap.pair_address, "1h", limit=500, currency="token")
                        gecko_budget -= 1
                        if hourly:
                            c.candles["1h"] = hourly
                        c.mark("gecko_1h")
                    pool = await self.gecko.pool(snap.pair_address)
                    gecko_budget -= 1
                    if pool:
                        g = GeckoTerminalCollector.pool_to_snapshot(pool)
                        snap.buyers.update({k: v for k, v in g.buyers.items() if v is not None})
                        snap.sellers.update({k: v for k, v in g.sellers.items() if v is not None})
                        if g.volume_usd.get("m15") is not None:
                            snap.volume_usd["m15"] = g.volume_usd["m15"]
                    trades = GeckoTerminalCollector.parse_trades(await self.gecko.trades(snap.pair_address))
                    gecko_budget -= 1
                    wm = wash_metrics(trades)
                    if wm.sufficient:
                        snap.wash_score = wm.wash_score
                        snap.trades_per_trader = wm.trades_per_trader
                        snap.social_metrics["wash"] = wm.to_dict()
                    c.mark("gecko")
                    self._ok("geckoterminal")
                except SourceUnavailable as e:
                    self._fail("geckoterminal", e)
                    self.pause_gecko(e)
                    gecko_budget = 0
            # optional Reddit mentions (30 min cache)
            if self.reddit and self.reddit.available and snap.symbol and c.due("reddit", 1800):
                try:
                    m = await self.reddit.mentions(f'"${snap.symbol}" OR "{snap.symbol} solana"')
                    if m is not None:
                        snap.social_metrics["reddit"] = m
                    c.mark("reddit")
                except Exception as e:  # social is optional, never fatal
                    self._fail("reddit", e)
            # PumpPortal early trades -> wash metrics for bonding-curve tokens
            if snap.bonding_curve and len(c.pump_trades) >= 20 and snap.wash_score is None:
                wm = wash_metrics(list(c.pump_trades))
                if wm.sufficient:
                    snap.wash_score = wm.wash_score
                    snap.trades_per_trader = wm.trades_per_trader

    # ------------------------------------------------------------------ persistence
    def _record(self, candidates: list[TrackedToken]) -> None:
        """Persist every tracked token. Each token is written in its own savepoint, so one bad
        record cannot roll back the whole cycle; failures are logged as events (published)."""
        cand_ids = {c.address for c in candidates}
        now = time.time()
        failures: list[str] = []
        try:
            with session_scope() as s:
                for tt in self.tokens.values():
                    try:
                        with s.begin_nested():
                            self._record_one(s, tt, cand_ids, now)
                    except Exception as e:  # isolate the faulty token
                        failures.append(f"{tt.snapshot.symbol or tt.address[:8]}: {type(e).__name__}: {str(e)[:160]}")
        except Exception as e:
            failures.append(f"sessione: {type(e).__name__}: {str(e)[:200]}")
            log.exception("failed to record scan results")
        if failures:
            log.warning("recording failed for %s tokens: %s", len(failures), failures[:3])
            try:
                with session_scope() as s:
                    repo.log_event(s, "error", f"salvataggio fallito per {len(failures)} token: " + " | ".join(failures[:3]),
                                   level="error")
            except Exception:
                log.exception("could not log recording failure")

    def _record_one(self, s, tt: TrackedToken, cand_ids: set[str], now: float) -> None:
        every = SNAPSHOT_EVERY_CANDIDATE_S if tt.address in cand_ids else SNAPSHOT_EVERY_OTHER_S
        tok = repo.upsert_token(s, tt.snapshot, tt.source, tt.score)
        if now - tt.last_recorded >= every:
            repo.add_snapshot(s, tok, tt.snapshot, tt.score)
            tt.history.append(TokenSnapshot.from_dict(tt.snapshot.to_dict()))
            tt.last_recorded = now
        for tf, cs in tt.candles.items():
            if tt.snapshot.pair_address and cs:
                repo.upsert_candles(s, tt.address, tt.snapshot.pair_address, tf, cs)
        if tt.snapshot.liquidity_usd is not None and tt.snapshot.liquidity_usd < DEAD_LIQUIDITY_USD:
            tt.low_liq_since = tt.low_liq_since or now
            if now - tt.low_liq_since > 6 * 3600:
                tok.status = "dead"
        else:
            tt.low_liq_since = None
        s.flush()

    def load_from_db(self, max_tokens: int | None = None, history: int = 24, candle_hours: int = 18) -> int:
        """Resume tracking after a restart (or between GitHub Actions windows): reload recently seen
        tokens with their last snapshot, recent point-in-time history and recorded candles, so that
        tokens are re-evaluated and candles survive a window in which GeckoTerminal is rate limited."""
        from sqlalchemy import or_, select

        from mci.database.models import Position, Token, TokenSnapshotRow

        limit = max_tokens or max(50, self.s.max_tracked_tokens // 2)
        since = utcnow() - timedelta(hours=24)
        loaded = 0
        with session_scope() as s:
            held = set(s.scalars(select(Position.token_address).where(Position.status == "open")).all())
            rows = s.scalars(
                select(Token)
                .where(or_(Token.address.in_(held), (Token.last_seen_at >= since) & (Token.status != "dead")))
                .order_by(Token.last_score.desc().nulls_last(), Token.last_liquidity_usd.desc().nulls_last())
                .limit(limit + len(held))
            ).all()
            for i, tok in enumerate(rows):
                if tok.address in self.tokens or not tok.last_snapshot:
                    continue
                try:
                    snap = TokenSnapshot.from_dict(tok.last_snapshot)
                except Exception:
                    continue
                tt = TrackedToken(tok.address, snap, to_utc(tok.first_seen_at) or utcnow(), "db")
                tt.last_recorded = time.time()  # avoid re-recording an identical snapshot immediately
                if i < self.s.candidate_pool_size * 2 or tok.address in held:
                    hist = s.scalars(select(TokenSnapshotRow).where(TokenSnapshotRow.token_id == tok.id)
                                     .order_by(TokenSnapshotRow.observed_at.desc()).limit(history)).all()
                    for h in reversed(hist):
                        try:
                            tt.history.append(TokenSnapshot.from_dict(h.data))
                        except Exception:
                            pass
                    if tok.pair_address:
                        since_ts = int((utcnow() - timedelta(hours=candle_hours)).timestamp())
                        for tf in ("1m", "1h"):
                            cs = repo.load_candles(s, tok.pair_address, tf, since_ts=since_ts if tf == "1m" else 0)
                            if cs:
                                tt.candles[tf] = cs[-1000:]
                self.tokens[tok.address] = tt
                loaded += 1
        return loaded

    def _prune(self) -> None:
        """Stop tracking tokens that are dead or stale (they remain in the database)."""
        cutoff = utcnow() - timedelta(hours=24)
        for addr in list(self.tokens):
            tt = self.tokens[addr]
            dead = tt.low_liq_since is not None and time.time() - tt.low_liq_since > 6 * 3600
            stale = tt.first_seen < cutoff and (tt.score is None or tt.score.total < 40)
            if dead or stale:
                del self.tokens[addr]
