"""Historical, survivorship-bias-free universe from a FREE Dune account.

Flow:
1. Dune query (SQL in docs/GUIDA_PASSO_PASSO.md) returns a RANDOM sample of ALL Pump.fun
   launches in a period - winners and failures alike, chosen without looking at outcomes.
2. Rows are read from a CSV export or from the Dune API (``GET /api/v1/query/{id}/results``,
   header ``X-Dune-API-Key``; free plan: 2,500 credits/month, ~20 credits per MB exported).
3. For each mint: GeckoTerminal pools (``/tokens/{mint}/pools``) + 1-minute OHLCV in SOL for the
   first ``hours`` after creation.
4. Coverage is measured: if GeckoTerminal has no data for many sampled tokens (e.g. tokens that
   never left the bonding curve), the dataset is automatically flagged as NOT survivorship-free.
"""

from __future__ import annotations

import csv
import logging
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from mci.backtesting.data import Dataset, DatasetInfo, TokenSeries
from mci.collectors.geckoterminal import GeckoTerminalCollector
from mci.collectors.pumpportal import PUMP_INITIAL_VIRTUAL_SOL, PUMP_INITIAL_VIRTUAL_TOKENS
from mci.domain import Candle
from mci.utils.http import SourceUnavailable, fnum

log = logging.getLogger(__name__)

MINT_KEYS = ("mint", "account_mint", "token", "token_address", "token_mint_address")
TIME_KEYS = ("created_at", "call_block_time", "block_time", "launch_time")
TF_SECONDS = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600}
MIN_COVERAGE_SURVIVORSHIP_FREE = 0.9


@dataclass
class Launch:
    mint: str
    created_at: datetime
    symbol: str | None = None


def parse_time(v: Any) -> datetime | None:
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return datetime.fromtimestamp(float(v), tz=timezone.utc)
    s = str(v).strip().replace(" UTC", "").replace("Z", "+00:00")
    if " " in s and "T" not in s:
        s = s.replace(" ", "T", 1)
    try:
        d = datetime.fromisoformat(s)
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def rows_to_launches(rows: list[dict[str, Any]]) -> list[Launch]:
    out: list[Launch] = []
    for r in rows:
        low = {str(k).lower(): v for k, v in r.items()}
        mint = next((low[k] for k in MINT_KEYS if low.get(k)), None)
        created = next((parse_time(low[k]) for k in TIME_KEYS if low.get(k)), None)
        if mint and created:
            out.append(Launch(str(mint).strip(), created, low.get("symbol")))
    return out


def launches_from_csv(path: str | Path) -> list[Launch]:
    with open(path, newline="", encoding="utf-8") as f:
        return rows_to_launches(list(csv.DictReader(f)))


async def launches_from_dune(query_id: int, api_key: str, limit: int = 5000,
                             client: httpx.AsyncClient | None = None) -> list[Launch]:
    """Latest saved result of a Dune query (does not trigger a new execution)."""
    if not api_key:
        raise SourceUnavailable("dune", "MCI_DUNE_API_KEY non configurata")
    own = client is None
    c = client or httpx.AsyncClient(timeout=60)
    try:
        r = await c.get(f"https://api.dune.com/api/v1/query/{int(query_id)}/results",
                        params={"limit": limit}, headers={"X-Dune-API-Key": api_key})
    finally:
        if own:
            await c.aclose()
    if r.status_code != 200:
        raise SourceUnavailable("dune", f"HTTP {r.status_code}: {r.text[:200]}")
    rows = ((r.json() or {}).get("result") or {}).get("rows") or []
    return rows_to_launches(rows)


def _pump_curve_reserve(price_sol: float) -> float:
    """Pump.fun bonding curve: x*y = k with k = 30 SOL * 1.073e9 tokens, price = x/y => x = sqrt(k*p)."""
    return (PUMP_INITIAL_VIRTUAL_SOL * PUMP_INITIAL_VIRTUAL_TOKENS * max(price_sol, 0.0)) ** 0.5


async def build_universe_dataset(
    launches: list[Launch],
    gecko: GeckoTerminalCollector,
    *,
    sample: int = 500,
    seed: int = 7,
    timeframe: str = "1m",
    hours: int = 24,
    description: str = "",
    progress: Any = None,
) -> Dataset:
    rng = random.Random(seed)
    picked = launches if len(launches) <= sample else rng.sample(launches, sample)
    tf_s = TF_SECONDS[timeframe]
    series: list[TokenSeries] = []
    stats = {"campionati": len(picked), "senza_pool": 0, "senza_candele": 0, "liquidita_sconosciuta": 0,
             "errori_api": 0}
    for i, ln in enumerate(picked, 1):
        if progress and i % 25 == 0:
            progress(i, len(picked), len(series))
        start = int(ln.created_at.timestamp())
        end = start + hours * 3600
        try:
            pools = await gecko.token_pools(ln.mint)
        except SourceUnavailable:
            stats["errori_api"] += 1
            continue
        sol_pools = []
        for p in pools:
            snap = GeckoTerminalCollector.pool_to_snapshot(p)
            if (snap.quote_symbol or "").upper() in ("SOL", "WSOL") and snap.pair_address:
                sol_pools.append((snap.created_at or ln.created_at, snap, p))
        if not sol_pools:
            stats["senza_pool"] += 1
            continue
        sol_pools.sort(key=lambda x: x[0])
        merged: dict[int, Candle] = {}
        dex_ids: list[str] = []
        current: dict[str, Any] | None = None
        for _, snap, raw in sol_pools[:2]:  # bonding curve + migrated pool at most
            try:
                cs = await gecko.ohlcv_window(snap.pair_address, timeframe, start, end, currency="token")
            except SourceUnavailable:
                stats["errori_api"] += 1
                continue
            if cs:
                dex_ids.append(snap.dex_id or "")
                current = current or {"snap": snap, "raw": raw}
            for c in cs:
                if c.ts not in merged or c.volume > merged[c.ts].volume:
                    merged[c.ts] = c
        candles = [merged[k] for k in sorted(merged)]
        if len(candles) < 5:
            stats["senza_candele"] += 1
            continue
        p0 = candles[0].open
        is_pump = ln.mint.endswith("pump") or any("pump" in d for d in dex_ids)
        reserve0: float | None = None
        sol_usd = None
        if current:
            attrs = current["raw"].get("attributes") or {}
            sol_usd = fnum(attrs.get("quote_token_price_usd"))
        if is_pump:
            reserve0 = _pump_curve_reserve(p0)
        elif current and sol_usd:
            snap = current["snap"]
            if snap.liquidity_usd and snap.price_native:
                reserve_now = snap.liquidity_usd / 2 / sol_usd
                reserve0 = reserve_now * (p0 / snap.price_native) ** 0.5
        if not reserve0:
            stats["liquidita_sconosciuta"] += 1
            continue
        series.append(TokenSeries(
            token=ln.mint, symbol=ln.symbol, pool=sol_pools[0][1].pair_address,
            dex_id=(dex_ids[0] if dex_ids else None) or ("pumpfun" if is_pump else None),
            created_at=ln.created_at, first_seen_at=ln.created_at, candles=candles, timeframe_s=tf_s,
            reserve_sol0=reserve0, sol_usd=sol_usd, meta={"source": "dune+geckoterminal"},
        ))
    coverage = len(series) / len(picked) if picked else 0.0
    notes = [
        f"copertura: {len(series)}/{len(picked)} token con dati utilizzabili ({coverage:.0%})",
        "esclusi: " + ", ".join(f"{k}={v}" for k, v in stats.items() if k != "campionati"),
        "liquidità Pump.fun stimata dalla bonding curve (k = 30 SOL x 1,073e9 token); altrimenti dalla riserva attuale",
    ]
    free = coverage >= MIN_COVERAGE_SURVIVORSHIP_FREE
    if stats["errori_api"]:
        notes.append(f"{stats['errori_api']} token non scaricati per errori di rete/API: risultato incompleto, "
                     "ripeti l'import (stesso --seed = stesso campione)")
    if not free:
        cause = ("errori di rete/API" if stats["errori_api"] >= max(1, len(picked) - len(series)) / 2
                 else "probabilmente mancano i token rimasti in bonding curve o morti subito")
        notes.append(f"copertura < 90% ({cause}) -> il dataset NON è considerato privo di survivorship bias")
    info = DatasetInfo(
        source="dune_universe",
        universe_method=description or f"campione casuale di {len(picked)} lanci da Dune",
        survivorship_free=free, point_in_time_features=False, notes=notes,
    )
    return Dataset(series, info)
