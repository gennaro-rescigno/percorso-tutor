from datetime import datetime, timezone

import httpx
import pytest
import respx

from mci.backtesting.engine import BacktestConfig, run_backtest
from mci.backtesting.universe import (
    build_universe_dataset,
    launches_from_csv,
    launches_from_dune,
    parse_time,
    rows_to_launches,
)
from mci.collectors.geckoterminal import GeckoTerminalCollector

GT = "https://gt.test"
T0 = int(datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc).timestamp())


def test_parse_dune_time_formats():
    assert parse_time("2026-09-01 12:00:00.000 UTC") == datetime(2026, 9, 1, 12, tzinfo=timezone.utc)
    assert parse_time("2026-09-01T12:00:00Z") == datetime(2026, 9, 1, 12, tzinfo=timezone.utc)
    assert parse_time("") is None and parse_time("boh") is None


def test_rows_and_csv(tmp_path):
    rows = [{"account_mint": "AAApump", "call_block_time": "2026-09-01 12:00:00.000 UTC", "symbol": "A"},
            {"mint": "", "created_at": "2026-09-01"}]
    assert [x.mint for x in rows_to_launches(rows)] == ["AAApump"]
    f = tmp_path / "dune.csv"
    f.write_text("mint,created_at,symbol\nBBBpump,2026-09-02 10:00:00.000 UTC,B\n")
    assert launches_from_csv(f)[0].mint == "BBBpump"


@pytest.mark.asyncio
@respx.mock
async def test_dune_api_results():
    respx.get("https://api.dune.com/api/v1/query/123/results").mock(return_value=httpx.Response(200, json={
        "result": {"rows": [{"mint": "CCCpump", "created_at": "2026-09-01 12:00:00.000 UTC"}]}}))
    got = await launches_from_dune(123, "key")
    assert got[0].mint == "CCCpump"
    respx.get("https://api.dune.com/api/v1/query/124/results").mock(return_value=httpx.Response(401, text="bad key"))
    with pytest.raises(Exception, match="401"):
        await launches_from_dune(124, "bad")


def _pool(addr, mint, dex="pump-fun"):
    return {"attributes": {"address": addr, "name": "X / SOL", "pool_created_at": "2026-09-01T12:00:00Z",
                           "quote_token_price_usd": "150", "reserve_in_usd": "20000",
                           "base_token_price_quote_token": "0.00000003"},
            "relationships": {"base_token": {"data": {"id": f"solana_{mint}"}}, "dex": {"data": {"id": dex}}}}


def _ohlcv(n=200, p=3e-8):
    rows = []
    for i in range(n):
        o = p
        p *= 1.004
        rows.append([T0 + 60 * i, o, p * 1.002, o * 0.998, p, 500 + 10 * i])
    return {"data": {"attributes": {"ohlcv_list": rows}}}


@pytest.mark.asyncio
@respx.mock
async def test_build_universe_dataset_and_coverage_flag():
    from mci.backtesting.universe import Launch

    launches = [Launch(f"M{i}pump", datetime.fromtimestamp(T0, tz=timezone.utc)) for i in range(10)]
    for i in range(10):
        pools = [_pool(f"P{i}", f"M{i}pump")] if i < 9 else []  # last token: no data on GeckoTerminal
        respx.get(f"{GT}/networks/solana/tokens/M{i}pump/pools").mock(return_value=httpx.Response(200, json={"data": pools}))
        respx.get(f"{GT}/networks/solana/pools/P{i}/ohlcv/minute").mock(return_value=httpx.Response(200, json=_ohlcv()))
    g = GeckoTerminalCollector(GT, 6000)
    ds = await build_universe_dataset(launches, g, sample=10, hours=24)
    await g.close()
    assert len(ds.series) == 9
    assert ds.info.survivorship_free is True  # 90% coverage
    s = ds.series[0]
    assert s.dex_id == "pump-fun" and s.reserve_sol0 and s.reserve_sol0 > 0 and s.first_seen_at
    # the dataset runs through the backtest engine
    res = run_backtest(ds, BacktestConfig(strategy_codes=["A", "B"], p_fail_entry=0, p_fail_exit=0))
    assert res.metrics.n_trades >= 0 and res.data_info["source"] == "dune_universe"


@pytest.mark.asyncio
@respx.mock
async def test_low_coverage_is_flagged_not_survivorship_free():
    from mci.backtesting.universe import Launch

    launches = [Launch(f"N{i}pump", datetime.fromtimestamp(T0, tz=timezone.utc)) for i in range(4)]
    for i in range(4):
        pools = [_pool(f"Q{i}", f"N{i}pump")] if i == 0 else []
        respx.get(f"{GT}/networks/solana/tokens/N{i}pump/pools").mock(return_value=httpx.Response(200, json={"data": pools}))
    respx.get(f"{GT}/networks/solana/pools/Q0/ohlcv/minute").mock(return_value=httpx.Response(200, json=_ohlcv()))
    g = GeckoTerminalCollector(GT, 6000)
    ds = await build_universe_dataset(launches, g, sample=4)
    await g.close()
    assert ds.info.survivorship_free is False
    assert any("NON" in n for n in ds.info.notes)
