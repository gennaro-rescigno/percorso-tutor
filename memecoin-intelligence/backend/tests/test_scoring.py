from datetime import timedelta

from conftest import good_snapshot

from mci.domain import TokenSnapshot, utcnow
from mci.scoring.filters import evaluate_filters
from mci.scoring.scorer import score_token


def test_good_token_scores_high_and_explains():
    r = score_token(good_snapshot(), for_trading=True)
    assert not r.excluded, r.exclusion_reasons
    assert r.total >= 70
    assert r.coverage > 0.8
    assert any("Liquidità" in e for e in r.explanations)
    assert sum(c["max"] for c in r.categories.values()) == 100


def test_missing_data_is_never_positive():
    full = score_token(good_snapshot())
    sparse = score_token(good_snapshot(top10_pct=None, holders_count=None, dev_pct=None, insider_cluster_pct=None,
                                       wash_score=None, rugcheck_score_norm=None))
    assert sparse.total < full.total
    assert sparse.coverage < full.coverage
    feats = {f["name"]: f for f in sparse.categories["onchain"]["features"]}
    assert feats["concentrazione top 10"]["points"] == 0
    assert feats["concentrazione top 10"]["note"] == "dato non disponibile"


def test_empty_token_cannot_be_traded():
    s = TokenSnapshot(chain="solana", token_address="X", observed_at=utcnow())
    r = score_token(s, for_trading=True)
    assert r.excluded
    assert any("dati insufficienti" in x for x in r.exclusion_reasons)


def test_honeypot_and_authorities_excluded():
    for over, code in (
        ({"sell_route_ok": False}, "HONEYPOT_NO_SELL_ROUTE"),
        ({"mint_authority_revoked": False}, "MINT_AUTHORITY_ACTIVE"),
        ({"freeze_authority_revoked": False}, "FREEZE_AUTHORITY_ACTIVE"),
        ({"dangerous_extensions": ["transfer_hook"]}, "DANGEROUS_EXTENSION"),
        ({"rugged_flag": True}, "RUGGED"),
    ):
        f = evaluate_filters(good_snapshot(**over), for_trading=True)
        assert f.excluded and code in f.codes, (over, f.codes)


def test_illiquid_and_slippage_excluded():
    assert "LOW_LIQUIDITY" in evaluate_filters(good_snapshot(liquidity_usd=4_000)).codes
    assert "SELL_IMPACT" in evaluate_filters(good_snapshot(sell_impact_pct=12.0)).codes


def test_concentration_and_wash_excluded():
    assert "TOP10_CONCENTRATION" in evaluate_filters(good_snapshot(top10_pct=82)).codes  # LIBRA-like
    assert "INSIDER_CLUSTER" in evaluate_filters(good_snapshot(insider_cluster_pct=60)).codes
    assert "WASH_TRADING" in evaluate_filters(good_snapshot(wash_score=0.9)).codes


def test_price_anomaly_excluded():
    assert "PRICE_ANOMALY" in evaluate_filters(good_snapshot(price_divergence_pct=40)).codes


def test_extreme_pump_flagged_as_risk_not_rewarded():
    r = score_token(good_snapshot(price_change_pct={"m5": 80.0, "h1": 450.0, "h6": 500.0}))
    assert any("estensione eccessiva" in x for x in r.risks)
    mom = {f["name"]: f for f in r.categories["momentum"]["features"]}
    assert mom["variazione 1h"]["points"] == 0


def test_lp_unlocked_for_non_launchpad_pool():
    f = evaluate_filters(good_snapshot(dex_id="raydium", lp_locked_pct=10.0))
    assert "LP_UNLOCKED" in f.codes


def test_too_young_token_is_pending_not_excluded():
    young = good_snapshot(created_at=utcnow() - timedelta(minutes=1))
    f = evaluate_filters(young)
    assert not f.excluded and "età minima" in f.pending_checks
    assert "TOO_YOUNG" in evaluate_filters(young, for_trading=True).codes
