"""Build backtest datasets from REAL data.

1. ``dataset_from_db``: the survivorship-bias-free path. Universe = every token the
   scanner recorded (``tokens.first_seen_at`` in the period), including excluded and
   dead ones; candles from the ``candles`` table; point-in-time snapshots from
   ``token_snapshots``.
2. ``fetch_candles_for_universe``: download missing OHLCV (GeckoTerminal, SOL-quoted,
   ``currency=token``) for the recorded universe, so the history of tokens that later
   died is preserved locally even if the data provider drops them.
3. ``dataset_from_pool_list``: pools provided by the user (e.g. a complete Dune export
   of launches). Survivorship-free ONLY if the list is complete for the period -
   the caller declares it.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select

from mci.backtesting.data import Dataset, DatasetInfo, TokenSeries
from mci.collectors.geckoterminal import GeckoTerminalCollector
from mci.database import repo
from mci.database.models import Token, TokenSnapshotRow
from mci.database.session import session_scope
from mci.domain import TokenSnapshot, to_utc
from mci.utils.http import SourceUnavailable

log = logging.getLogger(__name__)

TF_SECONDS = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600}


def dataset_from_db(start: datetime, end: datetime, timeframe: str = "1m", min_candles: int = 30) -> Dataset:
    series: list[TokenSeries] = []
    skipped_no_candles = 0
    with session_scope() as s:
        toks = s.scalars(select(Token).where(Token.first_seen_at >= start, Token.first_seen_at < end)).all()
        for t in toks:
            if not t.pair_address:
                skipped_no_candles += 1
                continue
            candles = repo.load_candles(s, t.pair_address, timeframe)
            if len(candles) < min_candles:
                skipped_no_candles += 1
                continue
            rows = s.scalars(select(TokenSnapshotRow).where(TokenSnapshotRow.token_id == t.id)
                             .order_by(TokenSnapshotRow.observed_at.asc())).all()
            snaps = [TokenSnapshot.from_dict(r.data) for r in rows]
            reserve0 = None
            sol_usd = None
            for sn in snaps:
                if sn.liquidity_quote and sn.price_native:
                    # back out the reserve at the first candle with the constant-product law
                    reserve0 = sn.liquidity_quote * (candles[0].open / sn.price_native) ** 0.5
                    if sn.liquidity_usd and sn.liquidity_quote:
                        sol_usd = sn.liquidity_usd / 2 / sn.liquidity_quote
                    break
            series.append(TokenSeries(
                token=t.address, symbol=t.symbol, pool=t.pair_address, dex_id=t.dex_id,
                created_at=to_utc(t.created_at), first_seen_at=to_utc(t.first_seen_at), candles=candles,
                timeframe_s=TF_SECONDS[timeframe], reserve_sol0=reserve0, sol_usd=sol_usd, snapshots=snaps,
                meta={"status": t.status},
            ))
    info = DatasetInfo(
        source="recorded", universe_method="tutti i token scoperti dallo scanner nel periodo (inclusi esclusi e morti)",
        survivorship_free=True, point_in_time_features=any(x.snapshots for x in series),
        notes=[f"{skipped_no_candles} token senza candele sufficienti (esclusi dal dataset ma conteggiati)"],
    )
    return Dataset(series, info)


async def fetch_candles_for_universe(gecko: GeckoTerminalCollector, start: datetime, end: datetime,
                                     timeframe: str = "1m", max_tokens: int = 2000) -> dict[str, int]:
    stats = {"tokens": 0, "candles": 0, "errors": 0}
    with session_scope() as s:
        toks = [(t.address, t.pair_address, t.first_seen_at) for t in s.scalars(
            select(Token).where(Token.first_seen_at >= start, Token.first_seen_at < end)).all() if t.pair_address]
    for addr, pool, first_seen in toks[:max_tokens]:
        since = int((to_utc(first_seen) or start).timestamp()) - 6 * 3600
        try:
            candles = await gecko.ohlcv_history(pool, timeframe, since, currency="token", max_pages=10)
        except SourceUnavailable as e:
            stats["errors"] += 1
            log.info("candles %s failed: %s", pool, e)
            continue
        with session_scope() as s:
            stats["candles"] += repo.upsert_candles(s, addr, pool, timeframe, candles)
        stats["tokens"] += 1
    return stats


async def dataset_from_pool_list(
    gecko: GeckoTerminalCollector, pools: list[dict], timeframe: str, since: datetime, *, complete_universe: bool,
    universe_description: str,
) -> Dataset:
    """``pools``: [{"pool": addr, "token": mint, "dex_id": ..., "reserve_sol": optional, "created_at": iso}]."""
    series = []
    since_ts = int(since.timestamp())
    for p in pools:
        try:
            candles = await gecko.ohlcv_history(p["pool"], timeframe, since_ts, currency="token")
        except SourceUnavailable:
            continue
        if not candles:
            continue
        created = datetime.fromisoformat(p["created_at"]) if p.get("created_at") else None
        series.append(TokenSeries(
            token=p["token"], symbol=p.get("symbol"), pool=p["pool"], dex_id=p.get("dex_id"), created_at=created,
            first_seen_at=created, candles=candles, timeframe_s=TF_SECONDS[timeframe],
            reserve_sol0=p.get("reserve_sol"), sol_usd=p.get("sol_usd"),
        ))
    info = DatasetInfo(
        source="gecko_pools_file", universe_method=universe_description, survivorship_free=complete_universe,
        point_in_time_features=False,
        notes=["liquidità storica stimata con la legge del prodotto costante dalla riserva fornita",
               f"scaricato il {datetime.now(timezone.utc):%Y-%m-%d}"],
    )
    return Dataset(series, info)
