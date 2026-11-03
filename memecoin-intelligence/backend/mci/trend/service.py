"""Daily closes from free public APIs (Binance, Kraken as fallback) and the virtual trend portfolio's bookkeeping."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from mci.database import repo
from mci.database.session import session_scope
from mci.trend.strategy import ASSETS, Book, new_book, step, summary
from mci.utils.http import ApiClient, SourceUnavailable, fnum

log = logging.getLogger(__name__)

BINANCE = {"BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT"}
KRAKEN = {"BTC": "XBTUSD", "ETH": "ETHUSD", "SOL": "SOLUSD"}
STATE_KEY = "trend_book"
BACKTEST = {
    "periodo_fuori_campione": "2022-01-01 / 2026-10-31",
    "portafoglio_filtro": {"cagr_pct": 31.2, "max_drawdown_pct": -42.4, "sharpe": 0.89, "sharpe_ic95": [-0.09, 1.83]},
    "compra_e_tieni": {"cagr_pct": 1.4, "max_drawdown_pct": -80.4, "sharpe": 0.35},
    "con_un_giorno_di_ritardo": {"cagr_pct": 18.6, "max_drawdown_pct": -50.6},
    "monete_dove_il_filtro_vince": "6 su 7 (BTC, ETH, SOL, BNB, ADA, DOGE; non XRP)",
    "anni": {"2022": [-36.2, -79.5], "2023": [206.2, 294.3], "2024": [37.9, 90.3], "2025": [29.5, -14.3],
             "2026": [6.4, -18.9]},
}


def day_of(ts_s: float) -> str:
    return datetime.fromtimestamp(ts_s, tz=timezone.utc).strftime("%Y-%m-%d")


def parse_binance(rows: list, now_s: float) -> list[tuple[str, float]]:
    """Completed daily candles only: (UTC day, close)."""
    out = []
    for r in rows or []:
        close_time_s = int(r[6]) / 1000
        if close_time_s > now_s:
            continue  # the current day is still open
        c = fnum(r[4])
        if c:
            out.append((day_of(int(r[0]) / 1000), c))
    return out


def parse_kraken(data: dict, now_s: float) -> list[tuple[str, float]]:
    res = (data or {}).get("result") or {}
    rows = next((v for k, v in res.items() if k != "last"), [])
    out = []
    for r in rows:
        start = int(r[0])
        if start + 86400 > now_s:
            continue
        c = fnum(r[4])
        if c:
            out.append((day_of(start), c))
    return out


class DailyCloses:
    def __init__(self, binance_url: str = "https://api.binance.com", kraken_url: str = "https://api.kraken.com",
                 client: httpx.AsyncClient | None = None):
        self.bn = ApiClient("binance", binance_url, rate_per_s=2, burst=2, max_retries=1, client=client)
        self.kr = ApiClient("kraken-ohlc", kraken_url, rate_per_s=0.5, burst=1, max_retries=1, client=client)
        self.last_source: str | None = None

    async def close(self) -> None:
        await self.bn.close()
        await self.kr.close()

    async def get(self, asset: str, now_s: float | None = None) -> list[tuple[str, float]]:
        now_s = now_s or time.time()
        try:
            rows = await self.bn.get("/api/v3/klines", params={"symbol": BINANCE[asset], "interval": "1d", "limit": 120})
            out = parse_binance(rows, now_s)
            if out:
                self.last_source = "binance"
                return out
        except SourceUnavailable as e:
            log.info("binance klines unavailable for %s: %s", asset, e)
        data = await self.kr.get("/0/public/OHLC", params={"pair": KRAKEN[asset], "interval": 1440})
        self.last_source = "kraken"
        return parse_kraken(data, now_s)


class TrendService:
    """Runs the virtual trend portfolio once per UTC day (shadow: never trades for real, never messages)."""

    def __init__(self, closes: DailyCloses, start_usd_provider):
        self.closes = closes
        self.start_usd_provider = start_usd_provider  # async () -> starting capital in USD (2 SOL at start)
        self.last_error: str | None = None

    async def run_once(self, now_s: float | None = None) -> list[dict[str, Any]]:
        now_s = now_s or time.time()
        with session_scope() as s:
            raw = repo.get_state(s, STATE_KEY)
        book = Book.from_dict(raw) if raw else None
        yesterday = day_of(now_s - 86400)
        if book is not None and book.last_day is not None and book.last_day >= yesterday:
            return []  # today's close is not there yet
        series: dict[str, list[tuple[str, float]]] = {}
        try:
            for a in ASSETS:
                series[a] = await self.closes.get(a, now_s)
        except SourceUnavailable as e:
            self.last_error = str(e)
            return []
        days = sorted(set.intersection(*(set(d for d, _ in series[a]) for a in ASSETS)))
        if not days:
            return []
        if book is None:
            start = await self.start_usd_provider()
            if not start:
                return []
            book = new_book(float(start))
        todo = [d for d in days if book.last_day is None or d > book.last_day]
        if book.last_day is None:
            todo = todo[-1:]  # start today: no back-filled history (the backtest covers the past)
        done: list[dict[str, Any]] = []
        for d in todo:
            closes = {a: [c for dd, c in series[a] if dd <= d] for a in ASSETS}
            done += step(book, d, closes)
        with session_scope() as s:
            repo.set_state(s, STATE_KEY, book.to_dict())
        self.last_error = None
        return done

    @staticmethod
    def report() -> dict[str, Any]:
        with session_scope() as s:
            raw = repo.get_state(s, STATE_KEY)
        book = Book.from_dict(raw) if raw else None
        return {"enabled": True, "book": raw, "summary": summary(book) if book else {"days": 0},
                "backtest": BACKTEST, "rules": {"assets": list(ASSETS), "average_days": 50, "cost_per_side": 0.0015},
                "note": ("Portafoglio virtuale: BTC, ETH e SOL, un terzo ciascuno, tenuti solo quando il prezzo è sopra "
                         "la media degli ultimi 50 giorni, altrimenti liquidità. Nessuna operazione reale, nessun "
                         "messaggio Telegram. Strategia giornaliera: servono mesi per giudicarla dal vivo.")}
