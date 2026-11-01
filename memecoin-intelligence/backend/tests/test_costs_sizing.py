import math

import pytest

from mci.execution.costs import (
    CostModel,
    amm_buy,
    amm_sell,
    dex_fee,
    max_size_for_impact,
    reserve_at_price,
    reserve_from_liquidity,
)
from mci.risk_management.profiles import AGGRESSIVE, CONSERVATIVE, MODERATE
from mci.risk_management.sizing import size_position


def test_amm_buy_matches_constant_product():
    x, p = 100.0, 1e-6  # 100 SOL reserve, price 1e-6 SOL/token
    f = amm_buy(1.0, x, p, 0.0)
    y = x / p
    expected = y * 1.0 / (x + 1.0)
    assert f.out_amount == pytest.approx(expected)
    assert f.impact_pct == pytest.approx(1 / 101)
    assert f.effective_price > p  # buying pushes the price up


def test_amm_round_trip_loses_fees_and_impact():
    x, p, fee = 50.0, 1e-5, 0.01
    buy = amm_buy(0.5, x, p, fee)
    # after the buy the pool has moved; selling into the ORIGINAL state is an upper bound
    sell = amm_sell(buy.out_amount, x, p, fee)
    assert sell.out_amount < 0.5
    assert 0.5 - sell.out_amount > 2 * fee * 0.5 * 0.9


def test_max_size_for_impact_inverse():
    x = 200.0
    size = max_size_for_impact(x, 0.02)
    assert size / (x + size) == pytest.approx(0.02)


def test_reserve_laws():
    assert reserve_from_liquidity(30_000, 150) == pytest.approx(100)
    assert reserve_at_price(100, 1.0, 4.0) == pytest.approx(200)  # sqrt law
    assert reserve_from_liquidity(None, 150) is None


def test_pumpswap_fee_tiers_decrease_with_mcap():
    assert dex_fee("pumpswap", 1e5) == pytest.approx(0.0125)
    assert dex_fee("pumpswap", 2e7) == pytest.approx(0.003)
    assert dex_fee("pumpswap", 1e6) < dex_fee("pumpswap", 2e5)
    assert dex_fee("unknown_dex") == 0.01


def _size(equity=2.0, cash=2.0, exposure=0.0, stop=0.2, reserve=300.0, profile=MODERATE, dd=0.0):
    return size_position(equity=equity, cash=cash, open_exposure=exposure, stop_distance_pct=stop, reserve_sol=reserve,
                         fee_pct=0.01, profile=profile, costs=CostModel(), drawdown_pct=dd)


def test_risk_based_size_respects_risk_budget():
    d = _size()
    assert not d.rejected
    # money at risk (size * effective stop) never exceeds the risk budget
    assert d.size_sol * d.effective_stop_pct <= 2.0 * MODERATE.risk_per_trade_pct + 1e-9
    assert d.size_sol <= 2.0 * MODERATE.max_position_pct + 1e-9


def test_no_martingale_size_shrinks_after_losses():
    full = _size(equity=2.0, cash=2.0)
    after_loss = _size(equity=1.6, cash=1.6)
    assert after_loss.size_sol < full.size_sol


def test_drawdown_reduces_risk():
    normal = _size(stop=0.3)
    dd = _size(stop=0.3, dd=0.5)
    assert dd.size_sol < normal.size_sol


def test_illiquid_pool_caps_size_or_rejects():
    d = _size(reserve=2.0)  # tiny pool
    assert d.rejected or d.binding_constraint in ("impatto di prezzo", "quota del pool")
    assert _size(reserve=None).rejected  # unknown liquidity -> no trade


def test_exposure_cap():
    d = _size(exposure=2.0 * MODERATE.max_exposure_pct)
    assert d.rejected


def test_profiles_ordering():
    c, m, a = (_size(profile=p, stop=0.25).size_sol for p in (CONSERVATIVE, MODERATE, AGGRESSIVE))
    assert c <= m <= a
    assert all(math.isfinite(x) for x in (c, m, a))


def test_worst_case_rug_loss_is_capped():
    for prof in (CONSERVATIVE, MODERATE, AGGRESSIVE):
        d = _size(profile=prof, stop=0.10)  # tight stop would allow a big position
        assert not d.rejected
        # if the token rugs (-100%), the loss stays within the worst-case budget
        assert d.size_sol * prof.max_rug_loss_assumption <= 2.0 * prof.max_worst_case_loss_pct + 1e-9
