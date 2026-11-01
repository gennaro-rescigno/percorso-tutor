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
from mci.execution.costs import CostModel
from mci.execution.paper import PaperExecutor
from mci.paper_trading.engine import TradingEngine
from mci.risk_management.profiles import get_profile
from mci.scanner.service import Scanner
from mci.secrets_store import JUPITER_KEY, jupiter_key, write_secret
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
        self.scanner = Scanner(s, self.dex, self.gecko, self.rug, self.jup, self.fx, reddit if reddit.available else None)
        self.costs = CostModel(priority_fee_sol=s.priority_fee_sol, jito_tip_sol=s.jito_tip_sol)
        self.executor = self._build_executor()
        self.mode = self.executor.mode
        self.tg = TelegramClient(s.telegram_bot_token.get_secret_value(), s.allowed_chat_ids)
        self.notifier = TelegramNotifier(self.tg, s, self.mode)
        self.engine = TradingEngine(s, self.scanner, self.executor, get_profile(s.risk_profile), self.costs, self.notifier)
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

    async def scan_once(self) -> None:
        candidates = await self.scanner.run_cycle()
        if self.pump:
            curve = [c.address for c in candidates if c.snapshot.bonding_curve]
            await self.pump.subscribe_trades(curve[:20])
        await self.engine.on_scan(candidates)
        await self.engine.flush_alerts()
        self._heartbeat()

    async def monitor_once(self) -> None:
        await self.engine.monitor_positions()
        await self.engine.flush_alerts()

    async def equity_once(self) -> None:
        fxp = await self.fx.get()
        eq = self.engine.mark_to_market(fxp.eur if fxp else None, fxp.usd if fxp else None, record=True)
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
        ]
        if self.pump:
            tasks.append(asyncio.create_task(self.pump.run()))
        await self._stop.wait()
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        for c in (self.dex, self.gecko, self.rug, self.jup, self.rpc, self.fx, self.tg):
            try:
                await c.close()
            except Exception:
                pass
        log.info("worker stopped")
