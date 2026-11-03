"""Telegram notifier + command bot.

Security: only chat ids listed in MCI_TELEGRAM_CHAT_IDS can run commands. Live trading
can NOT be enabled from Telegram (only on the server, see docs/SECURITY.md); /pause and
/resume only control whether new trades are opened, /kill activates the kill switch.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select

from mci.analytics import performance as perf
from mci.config import Settings
from mci.database import repo
from mci.database.models import Position, SignalRow
from mci.database.session import session_scope
from mci.domain import to_utc, utcnow
from mci.telegram import formatters as fm
from mci.telegram.client import TelegramClient

log = logging.getLogger(__name__)

HELP = (
    "<b>Comandi disponibili</b>\n"
    "/status – stato del sistema\n/balance – capitale e saldo\n/positions – posizioni aperte\n"
    "/signals – ultimi segnali\n/history – ultime operazioni chiuse\n/performance – metriche complessive\n"
    "/daily – report giornaliero\n/risk – stato del risk management\n/pause – sospende nuovi ingressi\n"
    "/resume – riprende (disattiva anche il kill switch)\n/kill – attiva il kill switch\n"
    "/paper – modalità di trading\n/jupiterkey CHIAVE – attiva la chiave gratuita di Jupiter (il messaggio viene cancellato)\n/help – questo messaggio"
)


TRADE_KINDS = frozenset({"buy", "partial", "close"})


class TelegramNotifier:
    """Implements the engine's ``Notifier`` protocol.

    With ``telegram_notify=trades`` (default) only buys and sells reach Telegram; everything else stays in the
    activity log and is available on demand (/signals, /daily, /status, /risk)."""

    def __init__(self, client: TelegramClient, settings: Settings, mode: str):
        self.client = client
        self.s = settings
        self.mode = mode

    async def notify(self, kind: str, payload: dict[str, Any]) -> None:
        if self.s.telegram_notify == "trades" and kind not in TRADE_KINDS:
            return
        try:
            text = self._render(kind, payload)
        except Exception:
            log.exception("failed to render %s", kind)
            return
        if text:
            with session_scope() as s:
                repo.log_event(s, "alert", f"telegram:{kind}", data={"preview": text[:300]})
            await self.client.send(text)

    def _render(self, kind: str, p: dict[str, Any]) -> str | None:
        m = self.mode
        if kind == "buy":
            return fm.buy_message(m, p)
        if kind == "close":
            return fm.close_message(m, p)
        if kind == "partial":
            return fm.partial_message(m, p)
        if kind == "stop_hit":
            return f"🛑 <b>STOP LOSS RAGGIUNTO – {fm.MODE_TAG[m]}</b>\nToken: <b>{fm._e(p.get('symbol'))}</b>"
        if kind == "signal":
            return fm.signal_message(m, p)
        if kind == "token_alert":
            return fm.token_alert_message(p)
        if kind == "rug":
            return fm.rug_alert_message(m, p)
        if kind == "anomaly":
            return fm.anomaly_message(p.get("text", ""))
        if kind == "capital":
            return fm.capital_message(m, p["equity"], p["prev"], p.get("sol_eur"))
        if kind == "daily":
            return fm.daily_report(m, p)
        if kind == "text":
            return p.get("text")
        return None


def build_daily_report(settings: Settings, mode: str, sol_eur: float | None, market_state: str,
                       day: datetime | None = None) -> dict[str, Any]:
    day_start = (day or utcnow()).astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    with session_scope() as s:
        summ = perf.summary(s, mode, settings.initial_capital_sol, sol_eur)
        ds = perf.day_stats(s, mode, day_start)
        state = repo.get_state(s, f"portfolio_{mode}") or {}
    day_start_equity = state.get("day_start_equity") or summ["equity_sol"]
    assessment = []
    if summ["total_trades"] < 30:
        assessment.append(f"campione ancora piccolo ({summ['total_trades']} trade chiusi): nessuna conclusione statistica")
    if summ["kill_switch"]:
        assessment.append("kill switch ATTIVO")
    if summ["drawdown"] > 0.15:
        assessment.append(f"drawdown elevato ({summ['drawdown']:.0%}): rischio ridotto automaticamente")
    if not assessment:
        assessment.append("funzionamento regolare")
    return {
        "date": day_start, "initial_sol": settings.initial_capital_sol, "equity_sol": summ["equity_sol"],
        "daily_pnl_sol": summ["equity_sol"] - day_start_equity, "total_pnl_sol": summ["net_profit_sol"],
        "total_return": summ["roi"], "buys": ds["buys"], "sells": ds["sells"], "wins": ds["wins"],
        "losses": ds["losses"], "win_rate": summ["win_rate"],
        "profit_factor": f"{summ['profit_factor']:.2f}" if summ["profit_factor"] else None,
        "drawdown": summ["drawdown"], "best": ds["best"], "worst": ds["worst"], "fees_sol": ds["fees_sol"],
        "open_positions": summ["open_positions"], "market_state": market_state, "assessment": "; ".join(assessment),
        "sol_eur": sol_eur,
    }


class TelegramBot:
    def __init__(self, client: TelegramClient, settings: Settings, mode: str, status_provider=None):
        self.client = client
        self.s = settings
        self.mode = mode
        self.status_provider = status_provider  # callable -> dict with live worker status
        self.offset: int | None = None
        self._told: set[int] = set()
        self.on_jupiter_key = None  # async (key) -> reply text, set by the worker

    async def poll_once(self) -> int:
        updates = await self.client.get_updates(self.offset)
        for u in updates:
            self.offset = u["update_id"] + 1
            msg = u.get("message") or {}
            chat = (msg.get("chat") or {}).get("id")
            text = (msg.get("text") or "").strip()
            if not text.startswith("/"):
                continue
            cmd = text.split()[0].split("@")[0].lower()
            if chat not in self.client.chat_ids:
                log.warning("telegram command from unauthorized chat ignored")
                if cmd in ("/start", "/help", "/id") and chat is not None and chat not in self._told:
                    # setup helper: tell people their own chat id (commands stay restricted)
                    self._told.add(chat)
                    await self.client.send(
                        f"👋 Il tuo chat id è <code>{chat}</code>.\nQuesta chat non è ancora autorizzata: inserisci "
                        "questo numero nel secret <b>MCI_TELEGRAM_CHAT_IDS</b> del repository GitHub "
                        "(Settings → Secrets and variables → Actions) per ricevere notifiche e usare i comandi.",
                        chat_id=chat,
                    )
                continue
            try:
                if cmd == "/jupiterkey":
                    reply = await self._jupiter_key(chat, msg, text)
                else:
                    reply = self.handle(cmd)
            except Exception:
                log.exception("command %s failed", cmd)
                reply = "Errore nell'elaborazione del comando."
            await self.client.send(reply, chat_id=chat)
        return len(updates)

    @staticmethod
    def _chain_line(st: dict[str, Any]) -> str:
        cs = st.get("chain_stream") or {}
        if cs.get("enabled") is False:
            return ""
        launches = ((st.get("onchain") or {}).get("launches") or {})
        state = "connesso" if cs.get("connected") else "NON connesso"
        return (f"Stream blockchain (gratuito): {state}, {cs.get('trades', 0)} operazioni decodificate, "
                f"lanci ultima ora: {launches.get('launches_1h', 'n/d')}\n")

    async def _jupiter_key(self, chat: int, msg: dict[str, Any], text: str) -> str:
        from mci.secrets_store import JUPITER_KEY_RE

        if msg.get("message_id") is not None:  # the key must not stay in the chat history
            await self.client.delete_message(chat, msg["message_id"])
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            return ("Uso: <code>/jupiterkey LA_TUA_CHIAVE</code> (chiave gratuita da portal.jup.ag). "
                    "Il messaggio con la chiave viene cancellato subito.")
        key = parts[1].strip()
        if not JUPITER_KEY_RE.fullmatch(key):
            return "❌ Formato della chiave non valido: nessuna modifica."
        if self.on_jupiter_key is None:
            return "Comando non disponibile in questa modalità."
        return await self.on_jupiter_key(key)

    # ------------------------------------------------------------------ commands
    def _sol_eur(self) -> float | None:
        st = self.status_provider() if self.status_provider else {}
        return st.get("sol_eur")

    def handle(self, cmd: str) -> str:
        tag = fm.MODE_TAG[self.mode]
        sol_eur = self._sol_eur()
        if cmd in ("/start", "/help"):
            intro = "🤖 <b>Memecoin Intelligence</b> attivo – " + tag + "\n\n" if cmd == "/start" else ""
            return intro + HELP
        if cmd == "/paper":
            return (f"Modalità attuale: <b>{tag}</b>.\nIl paper trading è la modalità predefinita. "
                    "Il trading reale NON può essere attivato da Telegram: richiede la procedura di consenso "
                    "esplicito sul server (docs/SECURITY.md).")
        if cmd == "/pause":
            with session_scope() as s:
                repo.set_state(s, "control_paused", True)
                repo.log_event(s, "system", "nuovi ingressi sospesi da Telegram")
            return f"⏸ Nuovi ingressi sospesi ({tag}). Le posizioni aperte continuano a essere gestite."
        if cmd == "/resume":
            with session_scope() as s:
                repo.set_state(s, "control_paused", False)
                repo.set_state(s, "control_resume_request", True)
                repo.log_event(s, "system", "trading ripreso da Telegram")
            return f"▶️ Trading ripreso ({tag}). Kill switch disattivato e riferimento del drawdown azzerato."
        if cmd == "/kill":
            with session_scope() as s:
                repo.set_state(s, "control_kill", "attivato manualmente da Telegram")
                repo.log_event(s, "risk", "kill switch richiesto da Telegram", level="warn")
            return "🛑 Kill switch richiesto: nessun nuovo ingresso finché non usi /resume."
        with session_scope() as s:
            summ = perf.summary(s, self.mode, self.s.initial_capital_sol, sol_eur)
            if cmd == "/status":
                st = self.status_provider() if self.status_provider else {}
                srcs = st.get("sources") or {}
                src_txt = ", ".join(
                    f"{k}:ok" if v.get("ok") else f"{k}:KO ({fm._e((v.get('error') or 'errore')[:80])})"
                    for k, v in srcs.items()) or "n/d"
                return (f"📟 <b>STATO – {tag}</b>\nUltimo ciclo scanner: {st.get('last_cycle') or 'n/d'}\n"
                        f"Token monitorati: {st.get('tracked', 'n/d')}\nFonti: {src_txt}\n"
                        f"Jupiter: {'chiave attiva (1 richiesta/s)' if st.get('jupiter_key') else 'senza chiave (0,5 richieste/s)'}\n"
                        f"{self._chain_line(st)}"
                        f"In pausa: {'sì' if summ['paused'] else 'no'} — kill switch: {'ATTIVO' if summ['kill_switch'] else 'no'}\n"
                        f"Capitale: {fm._sol_eur(summ['equity_sol'], sol_eur)}")
            if cmd == "/balance":
                return (f"💼 <b>SALDO – {tag}</b>\nCapitale iniziale: {fm.sol(summ['initial_capital_sol'])}\n"
                        f"Capitale attuale: <b>{fm._sol_eur(summ['equity_sol'], sol_eur)}</b>\n"
                        f"Liquido: {fm._sol_eur(summ['cash_sol'], sol_eur)}\nInvestito: {fm.sol(summ['invested_sol'])}\n"
                        f"ROI: {fm.pct(summ['roi'])}\n1 SOL = {fm.eur(sol_eur)}")
            if cmd == "/positions":
                rows = [perf.position_dict(p, sol_eur) for p in repo.open_positions(s, self.mode)]
                if not rows:
                    return f"Nessuna posizione aperta ({tag})."
                lines = [f"📂 <b>POSIZIONI APERTE – {tag}</b>"]
                for r in rows:
                    lines.append(f"\n<b>{fm._e(r['symbol'])}</b> [{r['strategy']}] stake {fm.sol(r['stake_sol'])}\n"
                                 f"ingresso {fm.price(r['entry_price'])} → ora {fm.price(r['current_price'])}\n"
                                 f"P/L {fm.sol(r['pnl_sol'])} ({fm.pct(r['return_pct'])}) — stop {fm.price(r['stop_price'])}")
                return "\n".join(lines)
            if cmd == "/signals":
                rows = s.scalars(select(SignalRow).order_by(SignalRow.created_at.desc()).limit(8)).all()
                if not rows:
                    return "Nessun segnale registrato."
                return "📡 <b>ULTIMI SEGNALI</b>\n" + "\n".join(
                    f"• {to_utc(r.created_at):%d/%m %H:%M} {fm._e(r.symbol)} [{r.strategy}] score {r.score:.0f} → {r.status}"
                    for r in rows)
            if cmd == "/history":
                rows = s.scalars(select(Position).where(Position.mode == self.mode, Position.status == "closed")
                                 .order_by(Position.closed_at.desc()).limit(10)).all()
                if not rows:
                    return "Nessuna operazione chiusa."
                return f"🧾 <b>STORICO – {tag}</b>\n" + "\n".join(
                    f"• {fm._e(p.symbol)} [{p.strategy}] {fm.pct((p.realized_pnl_sol or 0) / p.cost_sol if p.cost_sol else None)} "
                    f"({fm.sol(p.realized_pnl_sol)})" for p in rows)
            if cmd == "/performance":
                return (f"📈 <b>PERFORMANCE – {tag}</b>\nOperazioni chiuse: {summ['total_trades']}\n"
                        f"Win rate: {fm.pct(summ['win_rate'])}\nProfit factor: {summ['profit_factor'] or 'n/d'}\n"
                        f"Expectancy: {fm.sol(summ['expectancy_sol'])}\nMax drawdown: {fm.pct(summ['max_drawdown'])}\n"
                        f"Commissioni: {fm.sol(summ['fees_sol'])} — slippage: {fm.sol(summ['slippage_sol'])}\n"
                        + ("\n⚠️ Meno di 30 operazioni: metriche non ancora significative." if summ["total_trades"] < 30 else ""))
            if cmd == "/risk":
                state = repo.get_state(s, f"portfolio_{self.mode}") or {}
                return (f"🛡 <b>RISCHIO – {tag}</b>\nProfilo: {self.s.risk_profile}\n"
                        f"Drawdown corrente: {fm.pct(summ['drawdown'])}\n"
                        f"Esposizione: {fm.sol(sum((state.get('exposure') or {}).values()))}\n"
                        f"Posizioni: {summ['open_positions']}\nOperazioni oggi: {state.get('trades_today', 0)}\n"
                        f"Perdite consecutive: {state.get('consecutive_losses', 0)}\n"
                        f"Kill switch: {'ATTIVO – ' + summ['kill_reason'] if summ['kill_switch'] else 'non attivo'}")
        if cmd == "/daily":
            st = self.status_provider() if self.status_provider else {}
            p = build_daily_report(self.s, self.mode, sol_eur, st.get("market_state", "n/d"))
            return fm.daily_report(self.mode, p)
        return "Comando sconosciuto. " + HELP


def next_daily_report_time(now: datetime, hour_utc: int) -> datetime:
    t = now.replace(hour=hour_utc, minute=0, second=0, microsecond=0)
    return t if t > now else t + timedelta(days=1)
