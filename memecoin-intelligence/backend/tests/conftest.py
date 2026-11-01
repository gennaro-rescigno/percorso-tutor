from __future__ import annotations

from datetime import timedelta

import pytest

from mci.config import reset_settings_cache
from mci.database.session import init_engine
from mci.domain import TokenSnapshot, utcnow


@pytest.fixture()
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path}/test.db"
    monkeypatch.setenv("MCI_DATABASE_URL", url)
    monkeypatch.setenv("MCI_ENV", "test")
    reset_settings_cache()
    init_engine(url)
    yield url
    reset_settings_cache()


def good_snapshot(**over) -> TokenSnapshot:
    """A token that passes every filter and has full data coverage."""
    now = utcnow()
    s = TokenSnapshot(
        chain="solana", token_address="GoodMint111", observed_at=now, symbol="GOOD", name="Good",
        pair_address="GoodPool111", dex_id="pumpswap", quote_symbol="SOL", created_at=now - timedelta(hours=3),
        price_usd=0.001, price_native=0.001 / 150, market_cap_usd=1_000_000, fdv_usd=1_000_000,
        liquidity_usd=120_000, liquidity_quote=400.0,
        volume_usd={"m5": 20_000, "m15": 50_000, "h1": 150_000, "h6": 600_000, "h24": 1_200_000},
        buys={"m5": 120, "h1": 900, "h6": 4000, "h24": 9000}, sells={"m5": 80, "h1": 600, "h6": 3000, "h24": 7000},
        buyers={"m5": 70, "h1": 400}, sellers={"m5": 40, "h1": 250},
        price_change_pct={"m5": 3.0, "h1": 35.0, "h6": 80.0, "h24": 120.0},
        holders_count=2500, top1_pct=3.0, top10_pct=14.0, dev_pct=0.5, insider_cluster_pct=2.0,
        mint_authority_revoked=True, freeze_authority_revoked=True, rugcheck_score_norm=10.0, rugcheck_risks=[],
        sell_route_ok=True, sell_impact_pct=0.6, quote_probe_sol=0.1, wash_score=0.1, bonding_curve=False,
        socials={"twitter": "x", "telegram": "t", "website": "w"}, has_profile=True,
        social_metrics={"reddit": {"unique_authors": 12, "posts": 20}},
    )
    s.sources["security"] = "rugcheck"
    for k, v in over.items():
        setattr(s, k, v)
    return s
