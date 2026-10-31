import numpy as np
import pytest

from app.engine.features import OriginState, Prior, SideObs, WindowObs
from app.engine.forecast import forecast
from app.engine.markets import Selection, outcome_probs, profit, settle
from app.engine.model import DEFAULT_MODEL_PATH, ModelBundle
from app.engine.value import evaluate_selection, fair_probabilities

pytestmark = pytest.mark.skipif(not DEFAULT_MODEL_PATH.exists(), reason="model not trained")


@pytest.fixture(scope="module")
def bundle():
    return ModelBundle.load(DEFAULT_MODEL_PATH)


def state(period=2, clock=72.0, gh=2, ga=2, sot=(5, 4), shots=(12, 11), cor=(5, 4), w_sot=(2, 2), reds=(0, 0)):
    return OriginState(
        period=period, clock=clock,
        home=SideObs(goals=gh, reds=reds[0], shots=shots[0], sot=sot[0], corners=cor[0]),
        away=SideObs(goals=ga, reds=reds[1], shots=shots[1], sot=sot[1], corners=cor[1]),
        home_w10=WindowObs(shots=3, sot=w_sot[0], corners=1), away_w10=WindowObs(shots=3, sot=w_sot[1], corners=1),
        home_prior=Prior(0.1, 0.0, 10), away_prior=Prior(0.0, 0.1, 10))


def test_distributions_sum_to_one(bundle):
    fc = forecast(bundle, state(), n_draws=20)
    assert np.allclose(fc.p_end.sum(axis=(1, 2)), 1.0, atol=1e-6)
    assert np.allclose(fc.p_next_home + fc.p_next_away + fc.p_next_none, 1.0, atol=1e-6)
    for m in ("1x2",):
        tot = sum(outcome_probs(fc, Selection(m, p), 2).win for p in ("home", "draw", "away"))
        assert np.allclose(tot, 1.0, atol=1e-6)
    o = outcome_probs(fc, Selection("total_goals", "over", 4.5), 2)
    u = outcome_probs(fc, Selection("total_goals", "under", 4.5), 2)
    assert np.allclose(o.win + u.win, 1.0)


def test_more_time_means_more_goals(bundle):
    early = forecast(bundle, state(clock=50.0), n_draws=1)
    late = forecast(bundle, state(clock=85.0), n_draws=1)
    assert (1 - early.p_next_none[0]) > (1 - late.p_next_none[0])


def test_red_card_shifts_next_goal(bundle):
    even = forecast(bundle, state(gh=1, ga=1), n_draws=1)
    away_down = forecast(bundle, state(gh=1, ga=1, reds=(0, 1)), n_draws=1)
    assert away_down.p_next_home[0] > even.p_next_home[0]


def test_first_half_markets(bundle):
    fc = forecast(bundle, state(period=1, clock=30.0, gh=0, ga=0), n_draws=5)
    ht = outcome_probs(fc, Selection("ht_total_goals", "over", 0.5), 1)
    assert ht is not None and 0.2 < ht.win.mean() < 0.7
    assert 0.5 < fc.p_goal_2h.mean() < 0.95


def test_goal_window(bundle):
    fc = forecast(bundle, state(clock=72.0), n_draws=5, windows=[70.0, 80.0])
    assert set(fc.p_goal_window) == {70.0, 80.0}
    assert 0 < fc.p_goal_window[70.0].mean() < fc.p_goal_window[80.0].mean() + 0.2


def test_asian_settlement():
    s = Selection("total_goals", "over", 2.25)
    assert settle(s, (1, 1)) == "half_loss"
    assert settle(s, (2, 1)) == "win"
    assert settle(Selection("total_goals", "over", 2.75), (2, 1)) == "half_win"
    assert settle(Selection("total_goals", "under", 3.0), (2, 1)) == "push"
    assert settle(Selection("dnb", "home"), (1, 1)) == "push"
    assert profit("half_win", 2.0) == pytest.approx(0.5)
    assert profit("half_loss", 2.0) == pytest.approx(-0.5)


def test_ev_formula_matches_spec(bundle):
    # EV = p * odds - 1 for a binary market (spec example: p=0.58, odds=2.00 -> +0.16)
    from app.engine.markets import OutcomeProbs
    z = np.zeros(3)
    op = OutcomeProbs(np.full(3, 0.58), z, z, z, np.full(3, 0.42))
    ev = evaluate_selection(Selection("btts", "yes"), "x", op, 2.0, "t", None, {"btts": 0.02}, 0.1, None, None)
    assert ev.ev == pytest.approx(0.16)
    assert ev.implied == pytest.approx(0.5)
    assert ev.p_cons == pytest.approx(0.56)
    assert ev.ev_cons == pytest.approx(0.12)


def test_devig():
    fair, over = fair_probabilities({"over": 1.9, "under": 1.9}, "total_goals")
    assert fair["over"] == pytest.approx(0.5)
    assert over == pytest.approx(2 / 1.9 - 1)
    assert fair_probabilities({"over": 1.9}, "total_goals") is None
