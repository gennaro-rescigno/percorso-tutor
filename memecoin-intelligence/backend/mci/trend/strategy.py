"""Trend portfolio BTC / ETH / SOL: hold each coin only while it is above its 50-day average, otherwise cash.

Why this and not the memecoin strategies: research/historical/crypto_trend*.py (docs/RICERCA_MERCATO_MEMECOIN.md
section 10) tested it on Binance 2018-2026 with the average length chosen on 2018-2021 only. Out of sample
(2022 - Oct 2026) the filter beat buy & hold on 6 of 7 major coins (return AND drawdown), also with doubled costs
and one day of delay; the BTC+ETH+SOL portfolio made +31%/yr with a -42% worst drawdown against +1.4%/yr and
-80% for buy & hold. The confidence interval of its Sharpe ratio still touches zero: it is evidence, not a
guarantee, and it lags in strong bull markets.

Rules (same as the study):
  * one third of the portfolio per coin, re-set at the first daily close of each month;
  * a coin is held while its daily close is above the average of its last 50 daily closes (UTC days);
  * decisions on the close of each UTC day, executed right after it; 0.15% cost per side (fee + slippage);
  * the cash is USD (USDC on Solana) and earns nothing.
This module is pure (no I/O): the service feeds it the daily closes and stores the book.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

ASSETS = ("BTC", "ETH", "SOL")
N_DAYS = 50
COST = 0.0015
MAX_TRADES = 500
MAX_HISTORY = 2000


def signal(closes: list[float], n: int = N_DAYS) -> bool | None:
    """True above the n-day average of the closes (the last close included), None without enough history."""
    if len(closes) < n:
        return None
    return closes[-1] > sum(closes[-n:]) / n


@dataclass
class Book:
    cash: float
    units: dict[str, float] = field(default_factory=dict)
    start_usd: float = 0.0
    started: str | None = None
    last_day: str | None = None
    month: str | None = None
    # buy & hold benchmark with the same thirds, same monthly reset and the same costs
    bh_cash: float = 0.0
    bh_units: dict[str, float] = field(default_factory=dict)
    signals: dict[str, bool | None] = field(default_factory=dict)
    history: list[dict[str, Any]] = field(default_factory=list)
    trades: list[dict[str, Any]] = field(default_factory=list)
    costs_usd: float = 0.0

    def equity(self, prices: dict[str, float]) -> float:
        return self.cash + sum(u * prices.get(a, 0.0) for a, u in self.units.items())

    def bh_equity(self, prices: dict[str, float]) -> float:
        return self.bh_cash + sum(u * prices.get(a, 0.0) for a, u in self.bh_units.items())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Book":
        return cls(**d)


def new_book(start_usd: float) -> Book:
    return Book(cash=start_usd, start_usd=start_usd, bh_cash=start_usd)


def _trade_to(units: dict[str, float], cash: float, asset: str, target_value: float, price: float) -> tuple[float, float, float]:
    """Move one asset to a target value; returns (new cash, signed trade value, cost)."""
    cur = units.get(asset, 0.0) * price
    delta = target_value - cur
    if abs(delta) < 1e-9:
        return cash, 0.0, 0.0
    cost = abs(delta) * COST
    units[asset] = units.get(asset, 0.0) + delta / price
    if abs(units[asset]) < 1e-12:
        units[asset] = 0.0
    return cash - delta - cost, delta, cost


def step(book: Book, day: str, closes: dict[str, list[float]]) -> list[dict[str, Any]]:
    """Process the close of UTC day ``day`` (YYYY-MM-DD); ``closes`` = daily closes up to that day per asset."""
    if book.last_day is not None and day <= book.last_day:
        return []
    prices = {a: c[-1] for a, c in closes.items() if c}
    if any(a not in prices for a in ASSETS):
        return []
    sig = {a: signal(closes[a]) for a in ASSETS}
    month = day[:7]
    new_month = book.month != month
    trades: list[dict[str, Any]] = []
    eq = book.equity(prices)
    for a in ASSETS:
        on = bool(sig[a])
        was_on = book.units.get(a, 0.0) > 0
        if new_month or on != was_on:
            target = eq / len(ASSETS) if on else 0.0
            book.cash, delta, cost = _trade_to(book.units, book.cash, a, target, prices[a])
            book.costs_usd += cost
            if abs(delta) > 1e-6:
                reason = ("sopra la media di 50 giorni" if on else "sotto la media di 50 giorni") if on != was_on \
                    else "ribilanciamento mensile a un terzo"
                trades.append({"day": day, "asset": a, "side": "acquisto" if delta > 0 else "vendita",
                               "usd": round(abs(delta), 2), "price": prices[a], "cost_usd": round(cost, 4),
                               "reason": reason})
    if new_month:  # benchmark: thirds re-set monthly, always invested
        beq = book.bh_equity(prices)
        for a in ASSETS:
            book.bh_cash, _, _ = _trade_to(book.bh_units, book.bh_cash, a, beq / len(ASSETS), prices[a])
    book.month, book.last_day, book.signals = month, day, sig
    if book.started is None:
        book.started = day
    book.history.append({"day": day, "equity": round(book.equity(prices), 4), "bh": round(book.bh_equity(prices), 4),
                         "invested": sum(1 for a in ASSETS if book.units.get(a, 0) > 0)})
    book.history = book.history[-MAX_HISTORY:]
    book.trades = (book.trades + trades)[-MAX_TRADES:]
    return trades


def summary(book: Book) -> dict[str, Any]:
    h = book.history
    if not h:
        return {"days": 0}
    eq = [x["equity"] for x in h]
    peak, dd = eq[0], 0.0
    for v in eq:
        peak = max(peak, v)
        dd = min(dd, v / peak - 1)
    return {"days": len(h), "equity_usd": eq[-1], "return_pct": round((eq[-1] / book.start_usd - 1) * 100, 2),
            "bh_return_pct": round((h[-1]["bh"] / book.start_usd - 1) * 100, 2), "max_drawdown_pct": round(dd * 100, 2),
            "trades": len(book.trades), "costs_usd": round(book.costs_usd, 2)}
