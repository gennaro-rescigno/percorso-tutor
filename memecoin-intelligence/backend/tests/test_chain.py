"""On-chain decoders tested on REAL mainnet samples (tests/fixtures/live, collected by memecoin-live-probe)."""

from __future__ import annotations

import base64
import json
from pathlib import Path

import httpx
import pytest

from mci.chain import pump
from mci.chain.borsh import b58decode, b58encode
from mci.chain.pda import is_on_curve, metaplex_metadata_address, pump_bonding_curve_address
from mci.chain.rpc_pool import BudgetExceeded, RpcPool
from mci.chain.tokens import analyze_mint, apply_metaplex
from mci.chain.tx import funding_transfer, parse_transaction
from mci.utils.http import SourceUnavailable

LIVE = Path(__file__).parent / "fixtures" / "live"


def live(name: str):
    return json.loads((LIVE / f"{name}.json").read_text())


def test_base58_roundtrip():
    for addr in ("6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P", "11111111111111111111111111111111"):
        assert b58encode(b58decode(addr)) == addr
    assert len(b58decode("11111111111111111111111111111111")) == 32


def test_pda_matches_real_accounts():
    assert pump_bonding_curve_address("7SHruMKRr1DGKNe4FBQDBsYK7pEHwMPQb1chbzW1pump") == \
        live("curve_account_mayhem")["curve"]
    assert pump_bonding_curve_address("DswyQA5A1jFNF43QMfpp5jVpc6R7iP2wHgwfb2Pfpump") == \
        live("early_txs_normal")["create"]["bonding_curve"]
    md = live("metadata_account_classic")
    assert metaplex_metadata_address(md["mint"]) == md["metadata"]
    # wallets are ed25519 points, PDAs are not
    assert is_on_curve(b58decode("46x7gJqyQhsjQuXcws7ESW8h47kGcbQ1FD2RhFjfAWJN"))
    assert not is_on_curve(b58decode(md["metadata"]))


def test_bonding_curve_account_decodes_mayhem_curve():
    d = live("curve_account_mayhem")
    st = pump.decode_bonding_curve(base64.b64decode(d["result"]["value"]["data"][0]))
    assert st.is_mayhem_mode is True and st.complete is False
    assert st.quote_mint in pump.NATIVE_QUOTES
    assert st.virtual_token_reserves > st.real_token_reserves > 0
    assert st.creator == "BKvgKfNEN9dEcDJAGhovupEY47WgMAfnEE7ARTG2YUvV"  # = PumpPortal traderPublicKey
    assert st.extra["initial_virtual_quote_reserves"] == 30 * 10**9 and st.extra["depth"] == 0
    assert st.token_total_supply == 10**15
    # mayhem curves do not follow the constant product (real SOL reserve 2 lamports): no price is derived
    assert st.real_quote_reserves == 2 and st.price is None
    with pytest.raises(ValueError):
        pump.decode_bonding_curve(b"\0" * 166)


def test_trade_events_from_real_transactions():
    d = live("early_txs_normal")
    mint = d["create"]["mint"]
    trades = [e for t in d["txs"] for e in parse_transaction(t).events if isinstance(e, pump.TradeEvent)]
    assert len(trades) == 13  # 15 transactions, 2 failed
    assert all(t.mint == mint for t in trades)
    first = trades[0]
    assert first.is_buy and first.ix_name.startswith("buy") and first.quote_mint in pump.NATIVE_QUOTES
    assert abs(first.sol - 0.4849) < 0.001 and first.user == "46x7gJqyQhsjQuXcws7ESW8h47kGcbQ1FD2RhFjfAWJN"
    assert first.mayhem_mode is False
    assert sum(1 for t in trades if not t.is_buy) == 6
    for t in trades:
        assert t.price and 1e-8 < t.price < 1e-6


def test_transaction_facts_priority_and_jito():
    d = live("early_txs_normal")
    facts = [parse_transaction(t) for t in d["txs"]]
    assert sum(1 for f in facts if not f.ok) == 2
    assert [f.jito_tip_lamports for f in facts if f.uses_jito] == [10_000]
    f0 = facts[0]
    assert f0.cu_limit == 145_000 and f0.cu_price_micro == 1_000_000 and f0.priority_lamports == 145_000
    assert f0.fee_payer == "46x7gJqyQhsjQuXcws7ESW8h47kGcbQ1FD2RhFjfAWJN"
    assert all(not f.events for f in facts if not f.ok)  # failed transactions never produce trades


def test_funding_is_never_invented():
    w = live("funding_busy_address")
    assert funding_transfer(w["oldest_tx"], w["wallet"]) is None
    d = live("early_txs_normal")
    tx = d["txs"][0]
    payer = parse_transaction(tx).fee_payer
    dest = parse_transaction(tx).transfers[0].destination
    got = funding_transfer(tx, dest)
    assert got is not None and got.source == payer


def test_mint_security_on_real_mints():
    new = analyze_mint("7SHruMKRr1DGKNe4FBQDBsYK7pEHwMPQb1chbzW1pump", live("mint_new_mayhem")["result"]["value"])
    assert new.complete and not new.findings and new.metadata_mutable is False
    assert new.extensions == ["metadataPointer", "tokenMetadata"] and new.symbol == "NCUBED"

    bonk = analyze_mint("DezX", live("mint_bonk")["result"]["value"])
    assert bonk.complete and not bonk.findings

    classic = analyze_mint("6UpQ", live("mint_classic_bonk_pool")["result"]["value"])
    assert {f.code for f in classic.blocking} == {"MINT_AUTHORITY_ACTIVE", "FREEZE_AUTHORITY_ACTIVE"}
    apply_metaplex(classic, live("metadata_account_classic")["result"]["value"])
    assert classic.metadata_mutable is True and classic.symbol == "wXRP"

    pyusd = analyze_mint("2b1k", live("mint_pyusd")["result"]["value"])
    codes = {f.code for f in pyusd.blocking}
    assert {"PERMANENT_DELEGATE", "TRANSFER_HOOK_AUTHORITY", "CONFIDENTIAL_TRANSFER"} <= codes
    assert "TRANSFER_FEE" not in codes  # fee configured at 0 bps -> only a (non-blocking) authority finding


def test_unknown_is_never_safe():
    assert analyze_mint("x", None).blocking
    weird = {"owner": "Evil1111111111111111111111111111111111111", "data": {"parsed": {"type": "mint", "info": {}}}}
    assert analyze_mint("x", weird).blocking[0].code == "UNKNOWN_TOKEN_PROGRAM"
    acc = live("mint_new_mayhem")["result"]["value"]
    acc = json.loads(json.dumps(acc))
    acc["data"]["parsed"]["info"]["extensions"].append({"extension": "futureThing", "state": {}})
    assert [f.code for f in analyze_mint("x", acc).blocking] == ["UNKNOWN_EXTENSION"]


def test_events_from_logs_ignores_garbage():
    assert pump.events_from_logs(["Program data: !!!", "Program log: hi", "Program data: AAAA"]) == []


async def test_rpc_pool_failover_cache_and_budget():
    calls = {"a": 0, "b": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        host = request.url.host
        body = json.loads(request.content)
        if host == "a.example":
            calls["a"] += 1
            return httpx.Response(429)
        calls["b"] += 1
        if body["method"] == "getBalance":
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": body["id"],
                                             "error": {"code": -32602, "message": "invalid param"}})
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": body["id"], "result": {"value": {"ok": 1}}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    pool = RpcPool(["https://a.example", "https://b.example"], rps=100, budgets={"getAccountInfo": 2}, client=client)
    assert (await pool.account("X")) == {"ok": 1}
    assert calls == {"a": 1, "b": 1}  # 429 on the first endpoint -> failover
    assert (await pool.account("X")) == {"ok": 1} and pool.stats["cache_hits"] == 1  # cached
    await pool.account("Y")
    with pytest.raises(BudgetExceeded):
        await pool.account("Z")  # 2 calls per minute allowed
    with pytest.raises(SourceUnavailable):
        await pool.call("getBalance", ["X"])  # request error is not an endpoint failure
    h = pool.health()
    assert h["endpoints"][0]["rate_limited"] == 1 and h["budget_refused"] == 1
    assert "example" not in json.dumps(h)  # endpoint URLs (may contain keys) are never exposed
    await client.aclose()


def test_decoder_layouts_match_the_official_idl():
    from mci.chain.pump import check_idl

    idl = live("pump_idl_layouts")
    assert check_idl(idl) == []
    broken = json.loads(json.dumps(idl))
    t = next(x for x in broken["types"] if x["name"] == "TradeEvent")
    t["type"]["fields"][1], t["type"]["fields"][2] = t["type"]["fields"][2], t["type"]["fields"][1]
    assert any("TradeEvent" in p for p in check_idl(broken))
