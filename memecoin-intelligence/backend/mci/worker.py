"""24/7 worker process: scanner + trading engine + position monitor + Telegram.

State lives in the database, so a restart (crash, deploy, VM reboot) resumes with the
same capital, positions and kill-switch status. Each loop is isolated: an exception in
one loop is logged and the loop continues after a pause.
"""

from __future__ import annotations

import asyncio
import logging
import signal
import time
from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import Any

from sqlalchemy import delete, func, select

from mci.chain.rpc_pool import RpcPool
from mci.chain.stream import PumpStream
from mci.collectors.dexscreener import DexScreenerCollector
from mci.collectors.fx import SolPriceFeed
from mci.collectors.geckoterminal import GeckoTerminalCollector
from mci.collectors.jupiter import KEYED_BASE_URL, JupiterCollector
from mci.collectors.pumpportal import PumpPortalListener
from mci.collectors.rugcheck import RugCheckCollector
from mci.collectors.social import RedditCollector
from mci.collectors.solana_rpc import SolanaRpc
from mci.config import Settings, get_settings
from mci.database import repo
from mci.database.models import TokenSnapshotRow
from mci.database.session import init_engine, session_scope
from mci.domain import utcnow
from mci.execution import network_costs
from mci.execution.costs import CostModel
from mci.execution.paper import PaperExecutor
from mci.paper_trading.engine import TradingEngine
from mci.onchain.launches import LaunchTracker
from mci.onchain.service import OnchainService
from mci.paper_trading.experiments import CurveExperiment, SafeRulesExperiment
from mci.paper_trading.lab import LabEngine
from mci.onchain.journal import Journal
from mci.research import feature_store as fs
from mci.risk_management.profiles import get_profile
from mci.scanner.service import Scanner
from mci.secrets_store import JUPITER_KEY, jupiter_key, read_secret, write_secret
from mci.telegram.bot import TelegramBot, TelegramNotifier, build_daily_report, next_daily_report_time
from mci.telegram.client import TelegramClient
from mci.utils.http import SourceUnavailable

log = logging.getLogger("mci.worker")


class Worker:
    def __init__(self, settings: Settings | None = None):
        self.s = settings or get_settings()
        init_engine(self.s.database_url)
        s = self.s
        self.dex = DexScreenerCollector(s.dexscreener_base_url)
        self.gecko = GeckoTerminalCollector(s.geckoterminal_base_url, s.geckoterminal_calls_per_minute)
        self.rug = RugCheckCollector(s.rugcheck_base_url)
        jkey = jupiter_key(s)
        self.jup = JupiterCollector(KEYED_BASE_URL if jkey else s.jupiter_base_url, jkey,
                                    max(s.jupiter_requests_per_second, 1.0) if jkey else s.jupiter_requests_per_second)
        self.rpc = SolanaRpc(s.solana_rpc_url)
        self.fx = SolPriceFeed(s.coingecko_base_url, s.kraken_base_url)
        reddit = RedditCollector(s.reddit_client_id, s.reddit_client_secret.get_secret_value(), s.reddit_user_agent)
        # free on-chain layer: launch tracker fed by the public chain stream, RPC pool with budgets
        self.tracker = LaunchTracker()
        self.journal = Journal()
        self.tracker.journal = self.journal
        try:  # names of recent launches, so the 'copy' fact also works right after a restart
            self.journal.seed_names(fs.recent_launch_names(days=7))
        except Exception as e:  # never block the start for this
            log.warning("nomi dei lanci recenti non caricati: %s", e)
        extra = [u for u in read_secret(s, "rpc_urls").splitlines() if u.strip().startswith("http")]
        self.rpc_pool = RpcPool([s.solana_rpc_url] + extra, rps=s.solana_rpc_rps)
        self.onchain = OnchainService(self.rpc_pool, self.tracker) if s.onchain_enabled else None
        self.scanner = Scanner(s, self.dex, self.gecko, self.rug, self.jup, self.fx, reddit if reddit.available else None,
                               onchain=self.onchain)
        self.stream = (PumpStream(s.solana_ws_url, self.tracker.on_events, on_state=self._stream_state,
                                  connections=s.chain_stream_connections)
                       if s.chain_stream_enabled else None)
        with session_scope() as db:
            last_alive = repo.get_state(db, "stream_last_alive")
            for a, b in repo.get_state(db, "stream_gaps") or []:
                self.tracker.gaps.append((a, b))
        if last_alive:  # the worker was down: no data between the last heartbeat and now
            self.tracker.gaps.append((float(last_alive), time.time()))
        self._chain_ticks = 0
        # GeckoTerminal pace learned before a restart (otherwise every update starts too fast and gets 429s)
        with session_scope() as db:
            saved_pace = repo.get_state(db, "gecko_calls_per_minute")
        if saved_pace:
            self.scanner.set_gecko_rate(float(saved_pace))
        self.scanner.on_gecko_rate_change = self._save_gecko_pace
        self.costs = CostModel(priority_fee_sol=s.priority_fee_sol, jito_tip_sol=s.jito_tip_sol)
        self.executor = self._build_executor()
        self.mode = self.executor.mode
        self.tg = TelegramClient(s.telegram_bot_token.get_secret_value(), s.allowed_chat_ids)
        self.notifier = TelegramNotifier(self.tg, s, self.mode)
        self.engine = TradingEngine(s, self.scanner, self.executor, get_profile(s.risk_profile), self.costs, self.notifier)
        self.lab = LabEngine(s, self.scanner, self.costs) if s.lab_enabled else None
        self.experiments = ([SafeRulesExperiment(s, self.scanner, self.costs), CurveExperiment(s, self.scanner, self.costs)]
                            if s.experiments_enabled and s.lab_enabled else [])
        self.bot = TelegramBot(self.tg, s, self.mode, status_provider=self.status)
        self.bot.on_jupiter_key = self.set_jupiter_key
        self.pump = PumpPortalListener(s.pumpportal_ws_url, self.scanner.on_pumpportal_event) if s.pumpportal_enabled else None
        self._stop = asyncio.Event()
        self.started_at = utcnow()

    def _build_executor(self):
        if self.s.trading_mode == "live":
            failures = self.s.live_gate_failures()
            if failures:
                log.error("LIVE richiesto ma bloccato: %s -> uso PAPER", "; ".join(failures))
            else:
                from mci.execution.live import LiveExecutor

                log.warning("TRADING REALE ATTIVO con wallet dedicato")
                return LiveExecutor(self.s, self.costs, self.jup, self.rpc)
        return PaperExecutor(self.costs, self.jup, self.rpc)

    # ------------------------------------------------------------------ status
    def status(self) -> dict[str, Any]:
        fxp = self.fx.last
        anomaly = self.scanner.sol_anomaly() or self.scanner.data_outage()
        return {
            "mode": self.mode,
            "run_mode": self.s.run_mode,
            "started_at": self.started_at.isoformat(),
            "last_cycle": self.scanner.last_cycle_at.isoformat() if self.scanner.last_cycle_at else None,
            "cycle": self.scanner.cycle,
            "tracked": len(self.scanner.tokens),
            "sources": self.scanner.source_status,
            "jupiter_key": self.jup.has_key,
            "sol_eur": fxp.eur if fxp else None,
            "sol_usd": fxp.usd if fxp else None,
            "pumpportal_connected": bool(self.pump and self.pump.connected),
            "chain_stream": self.stream.health() if self.stream else {"enabled": False},
            "onchain": self.onchain.health() if self.onchain else {"enabled": False},
            "journal": self.journal.health(),
            "experiments": [{"mode": e.mode, "candidates": getattr(e, "last_candidates", None)} for e in self.experiments],
            "network_costs": {"priority_fee_sol": self.costs.priority_fee_sol, "jito_tip_sol": self.costs.jito_tip_sol},
            "telegram_enabled": self.tg.enabled,
            "telegram_sent": self.tg.sent,
            "telegram_failed": self.tg.failed,
            "telegram_last_error": self.tg.last_error,
            "market_state": anomaly or "nessuna anomalia rilevata",
        }

    # ------------------------------------------------------------------ loops
    async def _loop(self, name: str, interval: float, fn: Callable[[], Awaitable[None]]) -> None:
        while not self._stop.is_set():
            t0 = time.monotonic()
            try:
                await fn()
            except Exception as e:
                log.exception("loop %s failed", name)
                try:
                    with session_scope() as s:
                        repo.log_event(s, "error", f"errore nel ciclo {name}: {type(e).__name__}: {e}", level="error")
                except Exception:
                    pass
            elapsed = time.monotonic() - t0
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=max(1.0, interval - elapsed))
            except asyncio.TimeoutError:
                pass

    async def _lab_step(self, name: str, fn: Callable[[], Awaitable[Any]]) -> None:
        """Run a Laboratorio step in isolation: its errors never affect the main portfolio."""
        if self.lab is None:
            return
        try:
            await fn()
        except Exception:
            log.exception("laboratorio: %s non riuscito (portafoglio principale non coinvolto)", name)

    async def _experiment_step(self, name: str, fn: Callable[[Any], Awaitable[Any]]) -> None:
        """Run one step of every shadow experiment in isolation (never affects the main portfolio)."""
        for e in self.experiments:
            try:
                await fn(e)
            except Exception:
                log.exception("esperimento %s: %s non riuscito (portafoglio principale non coinvolto)", e.mode, name)

    async def scan_once(self) -> None:
        candidates = await self.scanner.run_cycle()
        if self.pump and self.s.pumpportal_trades_enabled:
            curve = [c.address for c in candidates if c.snapshot.bonding_curve]
            await self.pump.subscribe_trades(curve[:20])
        await self.engine.on_scan(candidates)
        await self.engine.flush_alerts()
        await self._lab_step("scan", lambda: self.lab.on_scan(candidates))
        await self._experiment_step("scan", lambda e: e.on_scan(candidates))
        self._heartbeat()

    async def monitor_once(self) -> None:
        await self.engine.monitor_positions()
        await self.engine.flush_alerts()
        await self._lab_step("monitor", lambda: self.lab.monitor_positions())
        await self._experiment_step("monitor", lambda e: e.monitor_positions())

    # ------------------------------------------------------------------ free chain data
    def _stream_state(self, up: bool) -> None:
        (self.tracker.stream_up if up else self.tracker.stream_down)()

    async def chaindata_once(self) -> None:
        """Persist launches / early trades / stream candles and write the point-in-time feature snapshots."""
        rows = self.tracker.drain()
        fs.persist_stream(rows)
        fs.write_feature_snapshots(self.tracker.due_horizons(), self.tracker)
        self._chain_ticks += 1
        if self._chain_ticks % 40 == 0:
            self.tracker.evict()
            counts = await asyncio.to_thread(fs.dataset_counts)
            with session_scope() as s:
                repo.set_state(s, "dataset_counts", counts)
        cutoff = time.time() - 8 * 86400
        with session_scope() as s:
            repo.set_state(s, "stream_last_alive", time.time())
            if self._chain_ticks % 4 == 1:
                repo.set_state(s, "stream_gaps", self._persisted_gaps())

    def _gaps(self) -> list[tuple[float, float]]:
        gaps = list(self.tracker.gaps)
        if self.tracker._gap_open is not None:
            gaps.append((self.tracker._gap_open, time.time()))
        return gaps

    def _persisted_gaps(self) -> list[list[float]]:
        """Gaps of the last 8 days, merged (with frequent drops the raw list would be long)."""
        cutoff = time.time() - 8 * 86400
        merged: list[list[float]] = []
        for a, b in sorted(g for g in self.tracker.gaps if g[1] >= cutoff):
            if merged and a <= merged[-1][1] + 0.5:
                merged[-1][1] = max(merged[-1][1], b)
            else:
                merged.append([a, b])
        return merged

    async def labels_once(self) -> None:
        n = fs.label_due(self._gaps())
        if n:
            log.info("etichettati %s snapshot del feature store", n)

    async def research_once(self) -> None:
        from mci.research.evaluate import run_research
        from mci.research.promotion import experiment_report

        from mci.research.events import event_study

        rep = await asyncio.to_thread(run_research)  # CPU-heavy: never block the stream and the monitors
        try:
            ev = await asyncio.to_thread(event_study, 7, self._gaps())
        except Exception as e:  # the journal study must never stop the main research report
            log.warning("studio degli eventi non riuscito: %s", e)
            ev = None
        with session_scope() as s:
            repo.set_state(s, "research_report", rep)
            if ev is not None:
                repo.set_state(s, "event_study", ev)
            repo.set_state(s, "experiments_report", {e.mode: experiment_report(s, e.mode) for e in self.experiments})

    async def netcosts_once(self) -> None:
        m = await network_costs.measure(self.rpc_pool)
        eff = network_costs.effective_priority_fee(self.s.priority_fee_sol, m)
        m["effective_priority_fee_sol"] = eff
        self.costs.priority_fee_sol = eff  # shared by every engine: only ever >= the configured fee
        with session_scope() as s:
            repo.set_state(s, "network_costs", m)

    async def equity_once(self) -> None:
        fxp = await self.fx.get()
        eq = self.engine.mark_to_market(fxp.eur if fxp else None, fxp.usd if fxp else None, record=True)

        async def lab_equity() -> None:
            self.lab.mark_to_market(fxp.eur if fxp else None, fxp.usd if fxp else None, record=True)

        await self._lab_step("equity", lab_equity)

        async def exp_equity(e) -> None:
            e.mark_to_market(fxp.eur if fxp else None, fxp.usd if fxp else None, record=True)

        await self._experiment_step("equity", exp_equity)
        prev = self.engine.last_equity_notified
        if prev and abs(eq / prev - 1) >= 0.03:
            await self.notifier.notify("capital", {"equity": eq, "prev": prev, "sol_eur": fxp.eur if fxp else None})
            self.engine.last_equity_notified = eq
        await self.engine.flush_alerts()

    async def outcomes_once(self) -> None:
        self.engine.track_signal_outcomes()

    async def daily_loop(self) -> None:
        while not self._stop.is_set():
            nxt = next_daily_report_time(utcnow(), self.s.daily_report_hour_utc)
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=(nxt - utcnow()).total_seconds())
                return
            except asyncio.TimeoutError:
                pass
            try:
                fxp = await self.fx.get()
                p = build_daily_report(self.s, self.mode, fxp.eur if fxp else None, self.status()["market_state"])
                await self.notifier.notify("daily", p)
                self.retention()
                kept = fs.retention()
                with session_scope() as s:
                    repo.log_event(s, "system", f"retention dati on-chain: {kept}")
            except Exception:
                log.exception("daily report failed")

    async def telegram_loop(self, announce: bool = True) -> None:
        if not self.tg.enabled:
            log.info("telegram non configurato: comandi disattivati")
            return
        from mci.telegram.formatters import MODE_TAG

        if announce:
            await self.notifier.notify("text", {"text": f"🤖 Worker avviato – {MODE_TAG[self.mode]}"})
        while not self._stop.is_set():
            try:
                await self.bot.poll_once()
            except Exception:
                log.exception("telegram polling error")
                await asyncio.sleep(5)

    @staticmethod
    def _save_gecko_pace(calls_per_minute: float) -> None:
        with session_scope() as s:
            repo.set_state(s, "gecko_calls_per_minute", round(calls_per_minute, 3))

    async def set_jupiter_key(self, key: str) -> str:
        """/jupiterkey from the owner's chat: verify with Jupiter, switch at once, keep it only on this server."""
        try:
            await self.jup.use_key(key, rps=max(self.s.jupiter_requests_per_second, 1.0))
        except SourceUnavailable as e:
            return f"❌ Jupiter non ha accettato la chiave ({e.detail}): nessuna modifica, resto senza chiave."
        write_secret(self.s, JUPITER_KEY, key)
        with session_scope() as s:
            repo.log_event(s, "system", "chiave Jupiter verificata e attivata (1 richiesta/s su api.jup.ag)")
        return ("✅ Chiave Jupiter verificata e attiva: le richieste a Jupiter passano da 0,5 a 1 al secondo. "
                "È salvata solo sul server; il tuo messaggio con la chiave è stato cancellato.")

    def _heartbeat(self) -> None:
        with session_scope() as s:
            repo.set_state(s, "worker_status", {**self.status(), "heartbeat": utcnow().isoformat()})

    def retention(self, keep_days: int = 14) -> int:
        """Thin out old snapshots to one per token per hour (database stays small on free tiers)."""
        cutoff = utcnow() - timedelta(days=keep_days)
        with session_scope() as s:
            rows = s.execute(
                select(TokenSnapshotRow.id, TokenSnapshotRow.token_id, TokenSnapshotRow.observed_at)
                .where(TokenSnapshotRow.observed_at < cutoff)
            ).all()
            keep: set[tuple[int, str]] = set()
            drop: list[int] = []
            for rid, tid, ts in rows:
                key = (tid, ts.strftime("%Y%m%d%H"))
                if key in keep:
                    drop.append(rid)
                else:
                    keep.add(key)
            for i in range(0, len(drop), 500):
                s.execute(delete(TokenSnapshotRow).where(TokenSnapshotRow.id.in_(drop[i:i + 500])))
            repo.log_event(s, "system", f"retention: rimossi {len(drop)} snapshot oltre {keep_days} giorni")
            return len(drop)

    async def maybe_daily_report(self) -> bool:
        """Send the daily report once per day after the configured hour (used by windowed runs)."""
        now = utcnow()
        today = now.date().isoformat()
        with session_scope() as s:
            last = repo.get_state(s, "last_daily_report")
        if now.hour < self.s.daily_report_hour_utc or last == today:
            return False
        fxp = await self.fx.get()
        p = build_daily_report(self.s, self.mode, fxp.eur if fxp else None, self.status()["market_state"])
        await self.notifier.notify("daily", p)
        with session_scope() as s:
            repo.set_state(s, "last_daily_report", today)
        self.retention(keep_days=7)
        return True

    async def run_window(self, window_s: int) -> None:
        """Run every loop for ``window_s`` seconds, then persist and exit.

        Used where no always-on server is available (e.g. a scheduled GitHub Actions job every
        ~15 minutes): state lives in the database between windows, Telegram commands received in
        the meantime are processed at the start of the next window.
        """
        log.info("ripresi %s token dal database", self.scanner.load_from_db())
        with session_scope() as s:
            self.bot.offset = repo.get_state(s, "telegram_offset")
            self.engine.last_equity_notified = repo.get_state(s, "last_equity_notified") or self.engine.port.equity
            repo.log_event(s, "system", f"esecuzione a finestra di {window_s}s in modalità {self.mode}")
        tasks = [
            asyncio.create_task(self._loop("scanner", self.s.scan_interval_seconds, self.scan_once)),
            asyncio.create_task(self._loop("monitor", self.s.position_monitor_interval_seconds, self.monitor_once)),
            asyncio.create_task(self.telegram_loop(announce=False)),
        ]
        if self.pump:
            tasks.append(asyncio.create_task(self.pump.run()))
        try:
            await asyncio.wait_for(self._stop.wait(), timeout=window_s)
        except asyncio.TimeoutError:
            pass
        self.stop()
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._stop.clear()
        for name, fn in (("equity", self.equity_once), ("outcomes", self.outcomes_once),
                         ("daily", self.maybe_daily_report)):
            try:
                await fn()
            except Exception:
                log.exception("final step %s failed", name)
        if self.tg.enabled and self.bot.offset is not None:
            await self.tg.get_updates(self.bot.offset, timeout=0)  # confirm processed commands
        if self.tg.failed:
            hint = ""
            if self.tg.last_error and ("401" in self.tg.last_error or "Unauthorized" in self.tg.last_error):
                hint = " (token non valido o revocato: aggiorna il secret MCI_TELEGRAM_BOT_TOKEN)"
            elif self.tg.last_error and "chat not found" in self.tg.last_error.lower():
                hint = " (chat id errato o bot mai avviato: premi Avvia sul bot e controlla MCI_TELEGRAM_CHAT_IDS)"
            with session_scope() as s:
                repo.log_event(s, "error", f"Telegram: {self.tg.failed} messaggi non consegnati: {self.tg.last_error}{hint}",
                               level="error")
        with session_scope() as s:
            repo.set_state(s, "telegram_offset", self.bot.offset)
            repo.set_state(s, "last_equity_notified", self.engine.last_equity_notified)
        self._heartbeat()
        for c in (self.dex, self.gecko, self.rug, self.jup, self.rpc, self.fx, self.tg):
            try:
                await c.close()
            except Exception:
                pass

    def stop(self) -> None:
        self._stop.set()
        if self.pump:
            self.pump.stop()
        if self.stream:
            self.stream.stop()

    async def run(self) -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, self.stop)
            except NotImplementedError:  # pragma: no cover - windows
                pass
        with session_scope() as s:
            repo.log_event(s, "system", f"worker avviato in modalità {self.mode}",
                           data={"profile": self.s.risk_profile, "strategies": self.s.strategies})
            n_open = len(repo.open_positions(s, self.mode))
            n_tok = s.scalar(select(func.count()).select_from(TokenSnapshotRow)) or 0
        log.info("worker started: mode=%s open_positions=%s snapshots=%s resumed_tokens=%s",
                 self.mode, n_open, n_tok, self.scanner.load_from_db())
        tasks = [
            asyncio.create_task(self._loop("scanner", self.s.scan_interval_seconds, self.scan_once)),
            asyncio.create_task(self._loop("monitor", self.s.position_monitor_interval_seconds, self.monitor_once)),
            asyncio.create_task(self._loop("equity", 300, self.equity_once)),
            asyncio.create_task(self._loop("outcomes", 600, self.outcomes_once)),
            asyncio.create_task(self.daily_loop()),
            asyncio.create_task(self.telegram_loop()),
            asyncio.create_task(self._loop("chaindata", 15, self.chaindata_once)),
            asyncio.create_task(self._loop("labels", 600, self.labels_once)),
            # hourly: ~10 s of CPU in a thread; the first outcomes arrive 4 h after the first launches
            asyncio.create_task(self._loop("research", 3600, self.research_once)),
            asyncio.create_task(self._loop("netcosts", 600, self.netcosts_once)),
        ]
        if self.pump:
            tasks.append(asyncio.create_task(self.pump.run()))
        if self.stream:
            tasks.append(asyncio.create_task(self.stream.run()))
        await self._stop.wait()
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        try:
            fs.persist_stream(self.tracker.drain())  # do not lose the last seconds of chain data
        except Exception:
            log.exception("final chain data flush failed")
        for c in (self.dex, self.gecko, self.rug, self.jup, self.rpc, self.fx, self.tg, self.rpc_pool):
            try:
                await c.close()
            except Exception:
                pass
        log.info("worker stopped")
