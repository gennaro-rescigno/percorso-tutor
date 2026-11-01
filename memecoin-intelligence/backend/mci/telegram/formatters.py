"""Telegram message templates (Italian). PAPER and REAL modes are always distinguishable."""

from __future__ import annotations

import html
from datetime import datetime
from typing import Any

MODE_TAG = {"paper": "🧪 PAPER TRADING", "live": "💰 TRADING REALE"}


def _e(x: Any) -> str:
    return html.escape(str(x)) if x is not None else "n/d"


def sol(x: float | None, digits: int = 4) -> str:
    return "n/d" if x is None else f"{x:,.{digits}f} SOL".replace(",", "X").replace(".", ",").replace("X", ".")


def eur(x: float | None) -> str:
    return "n/d" if x is None else f"{x:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def usd(x: float | None) -> str:
    if x is None:
        return "n/d"
    if x >= 1e6:
        return f"{x / 1e6:,.2f} M$"
    if x >= 1e3:
        return f"{x / 1e3:,.1f} k$"
    return f"{x:,.0f} $"


def price(x: float | None) -> str:
    if x is None:
        return "n/d"
    return f"{x:.10f}".rstrip("0") + " SOL" if x < 0.001 else f"{x:.6f} SOL"


def pct(x: float | None, digits: int = 1) -> str:
    return "n/d" if x is None else f"{x * 100:+.{digits}f}%".replace(".", ",")


def _sol_eur(amount: float | None, sol_eur: float | None) -> str:
    if amount is None:
        return "n/d"
    return sol(amount) + (f" (≈ {eur(amount * sol_eur)})" if sol_eur else "")


def _bullets(items: list[str], limit: int = 6) -> str:
    return "\n".join(f"• {_e(i)}" for i in items[:limit]) or "• n/d"


def buy_message(mode: str, p: dict[str, Any]) -> str:
    return (
        f"🚀 <b>NUOVO ACQUISTO – {MODE_TAG[mode]}</b>\n\n"
        f"Token: <b>{_e(p.get('symbol'))}</b> (<code>{_e(p.get('token'))}</code>)\n"
        f"Network: Solana\n"
        f"Strategia: {_e(p.get('strategy_name'))}\n"
        f"Prezzo ingresso: {price(p.get('entry_price'))}\n"
        f"Market Cap: {usd(p.get('mcap_usd'))}\n"
        f"Liquidità: {usd(p.get('liquidity_usd'))}\n"
        f"Score: <b>{p.get('score', 0):.0f}/100</b>\n\n"
        f"Stake: {_sol_eur(p.get('stake_sol'), p.get('sol_eur'))}\n"
        f"Capitale allocato: {pct(p.get('allocation_pct'))} del capitale\n"
        f"Rischio stimato: {_sol_eur(p.get('risk_sol'), p.get('sol_eur'))}\n"
        f"Stop loss: {price(p.get('stop_price'))} ({pct(p.get('stop_pct'))})\n"
        f"Take profit: {_e(p.get('tp_text'))}\n"
        f"Impatto di prezzo: {pct(p.get('impact'), 2)} — fonte prezzo: {_e(p.get('quote_source'))}\n\n"
        f"<b>Motivo dell'ingresso:</b>\n{_bullets(p.get('reasons') or [])}\n\n"
        f"<b>Rischi:</b>\n{_bullets(p.get('risks') or ['nessun rischio specifico oltre alla volatilità tipica'])}"
    )


def close_message(mode: str, p: dict[str, Any]) -> str:
    r = p.get("return_pct")
    head = "🟢" if (r or 0) > 0 else "🔴"
    return (
        f"{head} <b>POSIZIONE CHIUSA – {MODE_TAG[mode]}</b>\n\n"
        f"Token: <b>{_e(p.get('symbol'))}</b>\n\n"
        f"Prezzo ingresso: {price(p.get('entry_price'))}\n"
        f"Prezzo uscita: {price(p.get('exit_price'))}\n"
        f"Stake iniziale: {_sol_eur(p.get('stake_sol'), p.get('sol_eur'))}\n"
        f"Ricavo: {_sol_eur(p.get('proceeds_sol'), p.get('sol_eur'))}\n\n"
        f"Profitto/perdita lordo: {sol(p.get('gross_pnl_sol'))}\n"
        f"Commissioni: {sol(p.get('fees_sol'))}\n"
        f"Slippage: {sol(p.get('slippage_sol'))}\n"
        f"Profitto/perdita netto: <b>{_sol_eur(p.get('net_pnl_sol'), p.get('sol_eur'))}</b>\n\n"
        f"Risultato: <b>{pct(r)}</b>\n"
        f"Durata: {p.get('hold_minutes', 0):.0f} min\n\n"
        f"Capitale aggiornato: {_sol_eur(p.get('equity_sol'), p.get('sol_eur'))}\n\n"
        f"<b>Motivo della vendita:</b>\n{_bullets(p.get('exit_reasons') or [])}"
    )


def partial_message(mode: str, p: dict[str, Any]) -> str:
    return (
        f"🎯 <b>{_e(p.get('title', 'VENDITA PARZIALE'))} – {MODE_TAG[mode]}</b>\n\n"
        f"Token: <b>{_e(p.get('symbol'))}</b>\n"
        f"Venduto: {p.get('fraction', 0) * 100:.0f}% della posizione a {price(p.get('price'))}\n"
        f"Ricavo: {sol(p.get('proceeds_sol'))}\n"
        f"Nuovo stop: {price(p.get('new_stop'))}\n"
        f"Motivo: {_e(p.get('reason'))}"
    )


def signal_message(mode: str, p: dict[str, Any]) -> str:
    status = p.get("status", "generato")
    return (
        f"📡 <b>SEGNALE DI ACQUISTO ({_e(status)}) – {MODE_TAG[mode]}</b>\n\n"
        f"Token: <b>{_e(p.get('symbol'))}</b> — strategia {_e(p.get('strategy_name'))}\n"
        f"Score: {p.get('score', 0):.0f}/100 — prezzo {price(p.get('price'))}\n"
        f"{_bullets(p.get('reasons') or [], 4)}"
        + (f"\n\n⛔ Non eseguito: {_e(p.get('rejection'))}" if p.get("rejection") else "")
    )


def token_alert_message(p: dict[str, Any]) -> str:
    return (
        f"🔎 <b>MEMECOIN INTERESSANTE</b> (nessun ordine)\n\n"
        f"Token: <b>{_e(p.get('symbol'))}</b> (<code>{_e(p.get('token'))}</code>)\n"
        f"Score: <b>{p.get('score', 0):.0f}/100</b> — {_e(p.get('label'))} — copertura dati {p.get('coverage', 0):.0%}\n"
        f"Liquidità: {usd(p.get('liquidity_usd'))} — MC: {usd(p.get('mcap_usd'))}\n"
        f"{_bullets(p.get('explanations') or [], 4)}\n\n"
        f"Rischi:\n{_bullets(p.get('risks') or ['n/d'], 4)}"
    )


def rug_alert_message(mode: str, p: dict[str, Any]) -> str:
    return (
        f"🚨 <b>RISCHIO RUG PULL – {MODE_TAG[mode]}</b>\n\n"
        f"Token: <b>{_e(p.get('symbol'))}</b>\n{_bullets(p.get('reasons') or [])}\n\n"
        f"Azione: {_e(p.get('action', 'uscita di emergenza'))}"
    )


def anomaly_message(text: str) -> str:
    return f"⚠️ <b>ANOMALIA</b>\n\n{_e(text)}"


def capital_message(mode: str, equity: float, prev: float, sol_eur: float | None) -> str:
    return (f"💼 <b>CAPITALE AGGIORNATO – {MODE_TAG[mode]}</b>\n"
            f"{_sol_eur(prev, sol_eur)} → <b>{_sol_eur(equity, sol_eur)}</b> ({pct(equity / prev - 1 if prev else None)})")


def daily_report(mode: str, p: dict[str, Any]) -> str:
    d: datetime = p["date"]
    return (
        f"📊 <b>DAILY TRADING REPORT – {MODE_TAG[mode]}</b>\n\n"
        f"Data: {d:%d/%m/%Y}\n\n"
        f"Capitale iniziale: {_sol_eur(p.get('initial_sol'), p.get('sol_eur'))}\n"
        f"Capitale attuale: <b>{_sol_eur(p.get('equity_sol'), p.get('sol_eur'))}</b>\n"
        f"Profitto giornaliero: {_sol_eur(p.get('daily_pnl_sol'), p.get('sol_eur'))}\n"
        f"Profitto cumulativo: {_sol_eur(p.get('total_pnl_sol'), p.get('sol_eur'))} ({pct(p.get('total_return'))})\n\n"
        f"<b>Operazioni (oggi):</b>\n"
        f"• Totale acquisti: {p.get('buys', 0)}\n• Totale vendite: {p.get('sells', 0)}\n"
        f"• Operazioni vincenti: {p.get('wins', 0)}\n• Operazioni perdenti: {p.get('losses', 0)}\n\n"
        f"Win rate (totale): {pct(p.get('win_rate'))}\n"
        f"Profit factor (totale): {p.get('profit_factor') if p.get('profit_factor') is not None else 'n/d'}\n"
        f"Drawdown: {pct(p.get('drawdown'))}\n\n"
        f"Migliore operazione: {_e(p.get('best'))}\nPeggiore operazione: {_e(p.get('worst'))}\n\n"
        f"Commissioni totali (oggi): {sol(p.get('fees_sol'))}\n\n"
        f"Posizioni ancora aperte: {p.get('open_positions', 0)}\n\n"
        f"Stato del mercato: {_e(p.get('market_state'))}\n"
        f"Valutazione del sistema: {_e(p.get('assessment'))}"
    )
