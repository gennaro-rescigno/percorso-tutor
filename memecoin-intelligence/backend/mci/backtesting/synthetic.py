"""SYNTHETIC scenario generator - FOR ENGINE TESTS AND RISK STRESS TESTS ONLY.

Synthetic data says nothing about real profitability. Datasets built here are
always labelled ``source="synthetic"`` and every report shows that label.

Scenarios: rug pull, pump & dump, slow grind, dead token (data stops), choppy noise,
illiquid pool.
"""

from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone

from mci.backtesting.data import Dataset, DatasetInfo, TokenSeries
from mci.domain import Candle


def _series(
    name: str, prices: list[float], vols: list[float], *, start: datetime, tf: int = 60, reserve: float = 300.0,
) -> TokenSeries:
    t0 = int(start.timestamp())
    candles = []
    prev = prices[0]
    for i, (p, v) in enumerate(zip(prices, vols)):
        o = prev
        c = p
        hi = max(o, c) * 1.01
        lo = min(o, c) * 0.99
        candles.append(Candle(t0 + i * tf, o, hi, lo, c, v))
        prev = c
    return TokenSeries(
        token=name, symbol=name.upper()[:6], pool=f"pool_{name}", dex_id="raydium", created_at=start,
        first_seen_at=start, candles=candles, timeframe_s=tf, reserve_sol0=reserve, sol_usd=150.0,
        meta={"synthetic": True},
    )


def rug_pull(start: datetime, n: int = 300, rug_at: int = 150, seed: int = 1) -> TokenSeries:
    rng = random.Random(seed)
    p, prices, vols = 1e-6, [], []
    for i in range(n):
        if i < rug_at:
            p *= 1 + 0.004 + rng.gauss(0, 0.01)
            v = 2000 * (1 + i / 50) * (1 + rng.random())
        elif i == rug_at:
            p *= 0.03  # liquidity pulled
            v = 50_000
        else:
            p *= 1 + rng.gauss(0, 0.005)
            v = 20 * rng.random()
        prices.append(p)
        vols.append(v)
    return _series(f"rug{seed}", prices, vols, start=start)


def pump_and_dump(start: datetime, n: int = 360, seed: int = 2) -> TokenSeries:
    rng = random.Random(seed)
    p, prices, vols = 1e-6, [], []
    for i in range(n):
        if i < 60:
            p *= 1 + rng.gauss(0, 0.004)
            v = 500 * (1 + rng.random())
        elif i < 120:
            p *= 1 + 0.02 + rng.gauss(0, 0.01)
            v = 8000 * (1 + rng.random())
        else:
            p *= 1 - 0.012 + rng.gauss(0, 0.01)
            v = 3000 * math.exp(-(i - 120) / 60) * (1 + rng.random())
        prices.append(p)
        vols.append(v)
    return _series(f"pnd{seed}", prices, vols, start=start)


def slow_grind(start: datetime, n: int = 600, seed: int = 3) -> TokenSeries:
    rng = random.Random(seed)
    p, prices, vols = 1e-6, [], []
    for i in range(n):
        p *= 1 + 0.002 + rng.gauss(0, 0.008)
        prices.append(p)
        vols.append(1500 * (1 + i / 200) * (1 + rng.random()))
    return _series(f"grind{seed}", prices, vols, start=start)


def dead_token(start: datetime, n: int = 200, seed: int = 4) -> TokenSeries:
    rng = random.Random(seed)
    p, prices, vols = 1e-6, [], []
    for i in range(n):
        p *= 1 + (0.01 if i < 80 else -0.01) + rng.gauss(0, 0.01)
        prices.append(p)
        vols.append(3000 * (1 + rng.random()) if i < 80 else 200 * rng.random())
    return _series(f"dead{seed}", prices, vols, start=start)


def noise(start: datetime, n: int = 400, seed: int = 5) -> TokenSeries:
    rng = random.Random(seed)
    p, prices, vols = 1e-6, [], []
    for _ in range(n):
        p *= 1 + rng.gauss(0, 0.02)
        prices.append(p)
        vols.append(1000 * (1 + rng.random() * 3))
    return _series(f"noise{seed}", prices, vols, start=start)


def scenario_dataset(kinds: list[str], *, start: datetime | None = None, seed: int = 0,
                     tail_minutes: int = 600) -> Dataset:
    """Build a labelled synthetic dataset. A long 'tail' series keeps the clock running so
    tokens whose data stops early are recognised as dead."""
    start = start or datetime(2026, 1, 1, tzinfo=timezone.utc)
    gens = {"rug": rug_pull, "pnd": pump_and_dump, "grind": slow_grind, "dead": dead_token, "noise": noise}
    series = []
    for j, k in enumerate(kinds):
        s = gens[k](start + timedelta(minutes=5 * j), seed=seed + j + 1)
        series.append(s)
    last_end = max(s.end_ts for s in series)
    n_tail = (last_end - int(start.timestamp())) // 60 + tail_minutes
    tail = _series("clock", [1e-6] * n_tail, [0.0] * n_tail, start=start, reserve=1.0)
    series.append(tail)
    info = DatasetInfo(source="synthetic", universe_method="scenari generati", survivorship_free=True,
                       point_in_time_features=False, notes=["DATI SINTETICI: solo test del motore e del risk management"])
    return Dataset(series, info)
