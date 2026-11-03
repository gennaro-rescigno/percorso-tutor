"""Trend portfolio BTC/ETH/SOL: signals, trades, benchmark, data parsing and the daily service."""

from __future__ import annotations

import json

import httpx
import pytest

from mci.trend.service import DailyCloses, TrendService, parse_binance, parse_kraken
from mci.trend.strategy import COST, N_DAYS, Book, new_book, signal, step, summary

DAY = 86400
T0 = 1_790_000_000 // DAY * DAY  # a UTC midnight


def days(n: int, start: int = T0) -> list[str]:
    from datetime import datetime, timezone

    return [datetime.fromtimestamp(start + i * DAY, tz=timezone.utc).strftime("%Y-%m-%d") for i in range(n)]


def test_signal_needs_history_and_compares_with_the_average():
    assert signal([1.0] * (N_DAYS - 1)) is None
    up = [1.0] * (N_DAYS - 1) + [2.0]
    assert signal(up) is True and signal([2.0] * (N_DAYS - 1) + [1.0]) is False


def test_book_buys_above_sells_below_and_rebalances_monthly():
    b = new_book(300.0)
    rise = [100 + i for i in range(N_DAYS + 5)]
    fall = [200 - i for i in range(N_DAYS + 5)]
    closes = {"BTC": rise, "ETH": rise, "SOL": fall}
    t = step(b, "2026-11-01", closes)
    assert {x["asset"] for x in t} == {"BTC", "ETH"}
    assert b.units.get("SOL", 0) == 0 and abs(b.cash - (300 - 200 - 200 * COST)) < 1e-6
    assert step(b, "2026-11-01", closes) == []  # same day twice: nothing
    # SOL turns up mid-month: it is bought; BTC turns down: sold
    closes2 = {"BTC": rise[:-1] + [50.0], "ETH": rise + [rise[-1] + 1], "SOL": fall + [500.0]}
    t2 = step(b, "2026-11-02", closes2)
    sides = {(x["asset"], x["side"]) for x in t2}
    assert ("BTC", "vendita") in sides and ("SOL", "acquisto") in sides and not any(x["asset"] == "ETH" for x in t2)
    # a new month re-sets the thirds of the coins that stay invested
    t3 = step(b, "2026-12-01", closes2)
    assert all(x["reason"] == "ribilanciamento mensile a un terzo" for x in t3)
    s = summary(b)
    assert s["days"] == 3 and s["trades"] == len(b.trades) and s["costs_usd"] > 0
    assert Book.from_dict(json.loads(json.dumps(b.to_dict()))).units == b.units


def test_benchmark_is_always_invested_with_the_same_costs():
    b = new_book(300.0)
    flat = [100.0] * (N_DAYS + 1)
    step(b, "2026-11-01", {"BTC": flat, "ETH": flat, "SOL": flat})
    assert b.units.get("BTC", 0) == 0  # not above the average: cash
    assert b.bh_units["BTC"] > 0 and abs(b.bh_equity({"BTC": 100, "ETH": 100, "SOL": 100}) - 300 * (1 - COST)) < 1e-6


def test_parsers_drop_the_open_day():
    now = T0 + 10 * DAY + 3600
    rows = [[(T0 + i * DAY) * 1000, "1", "1", "1", str(100 + i), "1", (T0 + (i + 1) * DAY) * 1000 - 1] for i in range(11)]
    out = parse_binance(rows, now)
    assert len(out) == 10 and out[-1] == (days(10)[-1], 109.0)
    kr = {"result": {"XXBTZUSD": [[T0 + i * DAY, "1", "1", "1", str(100 + i), "1", "1", 1] for i in range(11)],
                     "last": 0}}
    assert parse_kraken(kr, now) == out


async def test_service_starts_today_then_processes_each_new_close_once(db):
    calls = {"binance": 0, "kraken": 0}
    state = {"n": N_DAYS + 5, "binance_down": False}

    def handler(req: httpx.Request) -> httpx.Response:
        n = state["n"]
        if "binance" in str(req.url):
            calls["binance"] += 1
            if state["binance_down"]:
                return httpx.Response(451, json={"msg": "restricted"})
            rows = [[(T0 + i * DAY) * 1000, "1", "1", "1", str(100 + i), "1", (T0 + (i + 1) * DAY) * 1000 - 1]
                    for i in range(n + 1)]
            return httpx.Response(200, json=rows)
        calls["kraken"] += 1
        return httpx.Response(200, json={"result": {"X": [[T0 + i * DAY, "1", "1", "1", str(100 + i), "1", "1", 1]
                                                         for i in range(n + 1)], "last": 0}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    async def start():
        return 300.0

    svc = TrendService(DailyCloses(client=client), start)
    now = T0 + state["n"] * DAY + 600
    first = await svc.run_once(now)
    assert len(first) == 3  # everything rising: one third each
    assert await svc.run_once(now + 1200) == []  # same day: no new fetch result
    state["n"] += 1
    state["binance_down"] = True  # fallback to Kraken
    await svc.run_once(now + DAY)
    rep = TrendService.report()
    assert rep["book"]["last_day"] == days(state["n"])[-1] and rep["summary"]["days"] == 2 and calls["kraken"] >= 3
    assert rep["backtest"]["portafoglio_filtro"]["cagr_pct"] == pytest.approx(31.2)
    await client.aclose()
