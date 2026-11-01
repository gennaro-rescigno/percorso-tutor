import httpx
import pytest
import respx

from mci.collectors.dexscreener import DexScreenerCollector
from mci.collectors.geckoterminal import GeckoTerminalCollector
from mci.collectors.jupiter import JupiterCollector
from mci.collectors.pumpportal import estimate_curve_sol_reserve, event_to_snapshot
from mci.collectors.rugcheck import RugCheckCollector
from mci.collectors.social import parse_telegram_members
from mci.domain import TokenSnapshot, utcnow
from mci.onchain.wash import coordinated_selling, wash_metrics
from mci.utils.http import ApiClient, SourceUnavailable

PAIR = {
    "chainId": "solana", "dexId": "raydium", "pairAddress": "POOL1",
    "baseToken": {"address": "MINT1", "name": "Cat", "symbol": "CAT"},
    "quoteToken": {"address": "So111", "symbol": "SOL"},
    "priceNative": "0.0000123", "priceUsd": "0.00185",
    "txns": {"m5": {"buys": 10, "sells": 5}, "h1": {"buys": 100, "sells": 80}, "h6": {}, "h24": {"buys": 900, "sells": 700}},
    "volume": {"m5": 1500, "h1": 20000, "h6": 90000, "h24": 300000},
    "priceChange": {"m5": 1.2, "h1": 12.5, "h24": -3},
    "liquidity": {"usd": 50000, "base": 1, "quote": 166.6},
    "fdv": 1850000, "marketCap": 1850000, "pairCreatedAt": 1767225600000,
    "info": {"socials": [{"type": "twitter", "url": "https://x.com/cat"}], "websites": [{"url": "https://cat.xyz"}]},
    "boosts": {"active": 2},
}


def test_dexscreener_pair_parsing():
    s = DexScreenerCollector.pair_to_snapshot(PAIR)
    assert s.token_address == "MINT1" and s.symbol == "CAT"
    assert s.price_native == pytest.approx(0.0000123)
    assert s.liquidity_quote == pytest.approx(166.6)
    assert s.buys["h1"] == 100 and s.vol("h1") == 20000
    assert s.socials["twitter"] and s.socials["website"]
    assert s.boosts_active == 2 and s.created_at is not None
    # windows DexScreener does not provide stay unknown
    assert s.buyers == {} and s.vol("m15") is None


def test_best_pair_prefers_sol_quote_then_liquidity():
    usdc = {**PAIR, "pairAddress": "POOL2", "quoteToken": {"symbol": "USDC"}, "liquidity": {"usd": 900000}}
    best = DexScreenerCollector.best_pair_per_token([usdc, PAIR])
    assert best["MINT1"]["pairAddress"] == "POOL1"


def test_gecko_pool_parsing_has_unique_buyers():
    pool = {"attributes": {"address": "POOL1", "name": "CAT / SOL", "base_token_price_usd": "0.0018",
                           "base_token_price_quote_token": "0.000012", "pool_created_at": "2026-01-01T00:00:00Z",
                           "reserve_in_usd": "50000", "fdv_usd": "1800000", "market_cap_usd": None,
                           "transactions": {"m5": {"buys": 3, "sells": 2, "buyers": 3, "sellers": 2},
                                            "h1": {"buys": 50, "sells": 40, "buyers": 30, "sellers": 25}},
                           "volume_usd": {"m5": "100", "m15": "900", "h1": "5000"}, "price_change_percentage": {"h1": "4.2"}},
            "relationships": {"base_token": {"data": {"id": "solana_MINT1"}}, "dex": {"data": {"id": "raydium"}}}}
    s = GeckoTerminalCollector.pool_to_snapshot(pool)
    assert s.token_address == "MINT1" and s.buyers["h1"] == 30 and s.vol("m15") == 900
    assert s.market_cap_usd is None  # not invented


@pytest.mark.asyncio
@respx.mock
async def test_gecko_ohlcv_parsing_and_validation():
    respx.get("https://gt.test/networks/solana/pools/P/ohlcv/minute").mock(return_value=httpx.Response(200, json={
        "data": {"attributes": {"ohlcv_list": [[120, 1, 2, 0.5, 1.5, 10], [60, 1, 1.1, 0.9, 1.0, 5], [180, -1, 1, 1, 1, 1]]}}}))
    g = GeckoTerminalCollector("https://gt.test", 600)
    c = await g.ohlcv("P", "1m")
    assert [x.ts for x in c] == [60, 120]  # sorted, invalid candle dropped
    await g.close()


@pytest.mark.asyncio
@respx.mock
async def test_api_unavailable_raises_and_opens_circuit():
    route = respx.get("https://down.test/x").mock(return_value=httpx.Response(503))
    api = ApiClient("down", "https://down.test", rate_per_s=1000, max_retries=0)
    for _ in range(api.breaker.failure_threshold):
        with pytest.raises(SourceUnavailable):
            await api.get("/x")
    calls = route.call_count
    with pytest.raises(SourceUnavailable, match="circuit open"):
        await api.get("/x")
    assert route.call_count == calls  # no request made while open
    await api.close()


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_429_is_retried():
    respx.get("https://rl.test/y").mock(side_effect=[httpx.Response(429, headers={"retry-after": "0"}),
                                                     httpx.Response(200, json={"ok": 1})])
    api = ApiClient("rl", "https://rl.test", rate_per_s=1000, max_retries=2)
    assert await api.get("/y") == {"ok": 1}
    await api.close()


@pytest.mark.asyncio
@respx.mock
async def test_jupiter_quote_and_no_route():
    respx.get("https://jup.test/swap/v1/quote").mock(side_effect=[
        httpx.Response(200, json={"inAmount": "100000000", "outAmount": "5000000", "otherAmountThreshold": "4900000",
                                  "priceImpactPct": "0.012", "routePlan": [{"swapInfo": {"label": "Raydium"}}]}),
        httpx.Response(400, json={"error": "no route"}),
    ])
    j = JupiterCollector("https://jup.test", rps=1000)
    q = await j.buy_quote("MINT", 0.1)
    assert q.out_amount == 5_000_000 and q.price_impact_pct == pytest.approx(0.012) and q.route_labels == ["Raydium"]
    assert await j.sell_quote("MINT", 1000) is None
    await j.close()


def test_rugcheck_report_parsing_excludes_pools():
    snap = TokenSnapshot(chain="solana", token_address="M", observed_at=utcnow(), pair_address="POOLVAULT")
    rep = {"mintAuthority": None, "freezeAuthority": "Frz111", "creator": "DEV", "rugged": False,
           "tokenProgram": "TokenzQd", "token_extensions": {"transferHook": {}},
           "risks": [{"name": "Freeze Authority still enabled", "level": "danger", "score": 7500}],
           "score_normalised": 55, "markets": [{"pubkey": "MKT", "lp": {"lpLockedPct": 100}}],
           "knownAccounts": {"AMMV": {"type": "AMM"}},
           "topHolders": [{"address": "AMMV", "owner": "AMMV", "pct": 40}, {"address": "h1", "owner": "DEV", "pct": 8},
                          {"address": "h2", "owner": "o2", "pct": 5, "insider": True}],
           "totalHolders": 321}
    RugCheckCollector.apply_report(snap, rep)
    assert snap.mint_authority_revoked is True and snap.freeze_authority_revoked is False
    assert snap.top1_pct == 8 and snap.top10_pct == 13  # pool vault excluded
    assert snap.dev_pct == 8 and snap.insider_cluster_pct == 5
    assert "transfer_hook" in snap.dangerous_extensions and snap.holders_count == 321


def test_pumpportal_event_and_curve_reserve():
    ev = {"mint": "PUMPMINT", "txType": "create", "traderPublicKey": "DEV", "name": "X", "symbol": "X",
          "vSolInBondingCurve": 32.0, "vTokensInBondingCurve": 1_000_000_000.0, "marketCapSol": 32.0, "pool": "pump"}
    s = event_to_snapshot(ev)
    assert s.bonding_curve and s.deployer == "DEV" and s.liquidity_quote == 32.0
    assert estimate_curve_sol_reserve(32.19) == pytest.approx(32.19, rel=0.01)


def test_wash_metrics_detects_round_trips():
    t = utcnow()
    clean = [{"ts": t, "wallet": f"w{i}", "side": "buy", "usd": 50} for i in range(40)]
    wash = []
    for i in range(40):
        wash.append({"ts": t, "wallet": f"b{i % 3}", "side": "buy", "usd": 500})
        wash.append({"ts": t, "wallet": f"b{i % 3}", "side": "sell", "usd": 500})
    assert wash_metrics(clean).wash_score < 0.2
    assert wash_metrics(wash).wash_score > 0.7
    assert not wash_metrics(clean[:5]).sufficient


def test_coordinated_selling():
    from datetime import timedelta

    t = utcnow()
    tr = [{"ts": t + timedelta(seconds=30 * i), "wallet": f"h{i}", "side": "sell"} for i in range(3)]
    assert coordinated_selling(tr, {"h0", "h1", "h2"})
    assert not coordinated_selling(tr, {"h0"})


def test_telegram_members_parser():
    assert parse_telegram_members('<div class="tgme_page_extra">12 345 members, 300 online</div>') == 12345
    assert parse_telegram_members("nothing") is None
