"""In-play forecast engine: score-state Markov chain driven by minute-level Poisson hazards.

For each remaining minute (slot) the home and away goal hazards come from the
fitted GLM and depend on the score *at that slot*. A dynamic-programming pass
propagates the exact distribution of extra goals (no Monte-Carlo noise).
Parameter uncertainty is propagated by repeating the pass for ``n_draws``
coefficient vectors drawn from the cluster-robust sampling distribution.

This is the Dixon & Robinson (1998) style in-play model: dependence between the
two teams' goals arises from score-state effects instead of a static copula.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .features import OriginState, design_matrix, side_frozen_features
from .model import GLM, ModelBundle

K = 8  # max extra goals tracked per side (P(> 8 more) is negligible)


@dataclass
class SlotGrid:
    period: np.ndarray
    clock: np.ndarray
    weight: np.ndarray  # expected exposure (minutes) of the slot
    lag: np.ndarray  # play-minutes since origin
    is_p1: np.ndarray


def _stoppage_overlap(x: np.ndarray, nominal_end: float, dist: np.ndarray) -> np.ndarray:
    """E[ |[x, x+1) ∩ [nominal_end, nominal_end + ST)| ] under ST ~ dist (k = 0, 1, ...)."""
    ks = np.arange(len(dist), dtype=float)
    ends = nominal_end + ks  # (k,)
    lo = np.maximum(x, nominal_end)[:, None]
    hi = np.minimum(x[:, None] + 1.0, ends[None, :])
    ov = np.clip(hi - lo, 0.0, 1.0)
    return ov @ dist


def _conditioned(dist: list[float], already: float) -> np.ndarray:
    d = np.asarray(dist, dtype=float)
    ks = np.arange(len(d), dtype=float)
    mask = ks > already
    if already <= 0:
        return d / d.sum()
    if not mask.any() or d[mask].sum() <= 0:
        out = np.zeros(int(np.ceil(already)) + 2)
        out[int(np.ceil(already)) + 1] = 1.0
        return out
    out = np.where(mask, d, 0.0)
    return out / out.sum()


def build_slot_grid(state: OriginState, stoppage: dict[str, list[float]],
                    end1_actual: float | None = None, end2_actual: float | None = None) -> SlotGrid:
    """Remaining one-minute slots from the origin to the (uncertain) final whistle.

    If ``end*_actual`` is given (training/validation) the true period ends are used.
    """
    periods, clocks, weights = [], [], []
    p0, c0 = state.period, state.clock

    def add_period(p: int, start: float, nominal: float, dist_key: str, actual: float | None):
        if actual is not None:
            xs = np.arange(start, max(actual, start), 1.0)
            if len(xs) == 0:
                return
            w = np.clip(actual - xs, 0.0, 1.0)
        else:
            dist = _conditioned(stoppage[dist_key], max(0.0, start - nominal))
            last = nominal + len(dist)
            xs = np.arange(start, last, 1.0)
            if len(xs) == 0:
                return
            w = np.clip(np.minimum(xs + 1.0, nominal) - xs, 0.0, 1.0) + _stoppage_overlap(xs, nominal, dist)
            w = np.minimum(w, 1.0)
        keep = w > 1e-4
        periods.append(np.full(keep.sum(), p))
        clocks.append(xs[keep])
        weights.append(w[keep])

    if p0 == 1:
        add_period(1, c0, 45.0, "h1", end1_actual)
        add_period(2, 45.0, 90.0, "h2", end2_actual)
    else:
        add_period(2, max(c0, 45.0), 90.0, "h2", end2_actual)

    period = np.concatenate(periods) if periods else np.zeros(0, dtype=int)
    clock = np.concatenate(clocks) if clocks else np.zeros(0)
    weight = np.concatenate(weights) if weights else np.zeros(0)
    # play-time lag (exclude half-time break)
    if p0 == 1:
        exp_st1 = float(np.dot(np.arange(len(stoppage["h1"])), np.asarray(stoppage["h1"]) / np.sum(stoppage["h1"])))
        end1 = end1_actual if end1_actual is not None else 45.0 + exp_st1
        pt = np.where(period == 1, clock, end1 + (clock - 45.0))
        lag = pt - c0
    else:
        lag = clock - max(c0, 45.0)
    return SlotGrid(period=period.astype(int), clock=clock, weight=weight, lag=np.maximum(lag, 0.0),
                    is_p1=period == 1)


@dataclass
class Forecast:
    """All arrays have a leading axis of length n_draws (row 0 = point estimate)."""

    home_goals: int
    away_goals: int
    p_end: np.ndarray  # (D, K+1, K+1) distribution of extra goals (home, away) at full time
    p_ht: np.ndarray | None  # same at half-time (only if origin in 1st half)
    p_next_home: np.ndarray
    p_next_away: np.ndarray
    p_next_none: np.ndarray
    p_goal_next10: np.ndarray
    p_goal_2h: np.ndarray  # P(at least one goal in the 2nd half)  (from origin)
    exp_goals_home: np.ndarray
    exp_goals_away: np.ndarray
    corners_home: np.ndarray | None = None  # expected remaining corners
    corners_away: np.ndarray | None = None
    corners_dispersion: float = 0.0
    corners_now: tuple[int, int] | None = None
    p_goal_window: dict[float, np.ndarray] | None = None  # window start minute -> P(goal in [a, a+10))
    grid: SlotGrid | None = None
    model_name: str = ""


def _hazards(glm: GLM, betas: np.ndarray, state: OriginState, grid: SlotGrid, refs: dict,
             side: int, add_h: np.ndarray, add_a: np.ndarray) -> np.ndarray:
    """Exposure-weighted hazards with shape (S, n_states, D)."""
    fr = side_frozen_features(state, side, refs)
    S = len(grid.clock)
    nst = add_h.size
    gh, ga = state.home.goals, state.away.goals
    if side == 0:
        diff = (gh + add_h) - (ga + add_a)
    else:
        diff = (ga + add_a) - (gh + add_h)
    gtot = gh + ga + add_h + add_a
    # rows ordered slot-major
    period = np.repeat(grid.period, nst)
    clock = np.repeat(grid.clock, nst)
    lag = np.repeat(grid.lag, nst)
    diff_r = np.tile(diff.ravel(), S)
    gtot_r = np.tile(gtot.ravel(), S)
    X = design_matrix(glm.features, fr.values, period, clock, lag, diff_r, gtot_r)
    eta = X @ betas.T  # (S*nst, D)
    eta = np.clip(eta, -20, 3)
    lam = np.exp(eta).reshape(S, nst, -1)
    return lam * grid.weight[:, None, None]


def forecast(bundle: ModelBundle, state: OriginState, goal_model: str = "goals_stats",
             n_draws: int = 200, seed: int = 7, with_corners: bool = True,
             end1_actual: float | None = None, end2_actual: float | None = None,
             windows: list[float] | None = None) -> Forecast:
    rng = np.random.default_rng(seed)
    glm = bundle.glms[goal_model]
    betas = glm.draws(n_draws, rng)
    D = betas.shape[0]
    grid = build_slot_grid(state, bundle.stoppage, end1_actual, end2_actual)
    S = len(grid.clock)

    ah, aa = np.meshgrid(np.arange(K + 1), np.arange(K + 1), indexing="ij")  # (K+1, K+1)

    if S == 0:
        p_end = np.zeros((D, K + 1, K + 1))
        p_end[:, 0, 0] = 1.0
        z = np.zeros(D)
        return Forecast(state.home.goals, state.away.goals, p_end, p_end.copy() if state.period == 1 else None,
                        z, z, np.ones(D), z, z, z, z, grid=grid, model_name=goal_model)

    lam_h = _hazards(glm, betas, state, grid, bundle.refs, 0, ah, aa)  # (S, nst, D)
    lam_a = _hazards(glm, betas, state, grid, bundle.refs, 1, ah, aa)

    corner = bundle.glms.get("corners_stats") if with_corners else None
    have_corner_data = state.home.corners is not None and state.away.corners is not None
    if corner is not None and have_corner_data:
        cb = corner.draws(n_draws, rng)
        lc_h = _hazards(corner, cb, state, grid, bundle.refs, 0, ah, aa)
        lc_a = _hazards(corner, cb, state, grid, bundle.refs, 1, ah, aa)
        corners_h = np.zeros(D)
        corners_a = np.zeros(D)
    else:
        lc_h = lc_a = None
        corners_h = corners_a = None

    # ---- frozen-state quantities (state can only change after a goal) ----
    l0 = lam_h[:, 0, :] + lam_a[:, 0, :]  # (S, D)
    cum = np.cumsum(l0, axis=0)
    surv_before = np.exp(-(cum - l0))  # P(no goal before slot s)
    p_goal_slot = 1.0 - np.exp(-l0)
    share_h = np.divide(lam_h[:, 0, :], l0, out=np.full_like(l0, 0.5), where=l0 > 0)
    p_next_home = np.sum(surv_before * p_goal_slot * share_h, axis=0)
    p_next_away = np.sum(surv_before * p_goal_slot * (1 - share_h), axis=0)
    p_next_none = np.exp(-cum[-1])
    # next 10 minutes of play
    within = np.clip(10.0 - grid.lag, 0.0, 1.0)  # fraction of the slot inside the window
    p_goal_next10 = 1.0 - np.exp(-np.sum(l0 * within[:, None], axis=0))

    # ---- exact score-state chain ----
    P = np.zeros((D, K + 1, K + 1))
    P[:, 0, 0] = 1.0
    p_ht = None
    exp_h = np.zeros(D)
    exp_a = np.zeros(D)
    lam_h_t = lam_h.transpose(0, 2, 1).reshape(S, D, K + 1, K + 1)
    lam_a_t = lam_a.transpose(0, 2, 1).reshape(S, D, K + 1, K + 1)
    if lc_h is not None:
        lc_h_t = lc_h.transpose(0, 2, 1).reshape(S, D, K + 1, K + 1)
        lc_a_t = lc_a.transpose(0, 2, 1).reshape(S, D, K + 1, K + 1)
    # fixed 10-minute goal windows [a, a+10) on the match clock (regulation minutes only)
    win_specs = {}
    for a in windows or []:
        per = 1 if a + 10 <= 45 else 2
        in_win = (grid.period == per) & (grid.clock >= a) & (grid.clock < a + 10)
        idx = np.where(in_win)[0]
        if len(idx) == 0:
            continue
        lt_w = (lam_h_t + lam_a_t)[idx].sum(axis=0)  # frozen-state cumulative hazard (D, K+1, K+1)
        win_specs[float(a)] = (idx[0], np.exp(-lt_w))
    p_goal_window: dict[float, np.ndarray] = {}
    p1_slots = np.where(grid.is_p1)[0]
    last_p1 = p1_slots[-1] if len(p1_slots) else -1
    p2_mask = ~grid.is_p1
    if state.period == 1:
        # P(no goal in 2nd half | state at HT) computed from frozen state hazards over p2 slots
        lt = (lam_h_t + lam_a_t)[p2_mask].sum(axis=0)  # (D, K+1, K+1)
        no_goal_2h_given = np.exp(-lt)
    for s in range(S):
        for a, (first, no_goal_given) in win_specs.items():
            if s == first:
                p_goal_window[a] = 1.0 - np.sum(P * no_goal_given, axis=(1, 2))
        lh = lam_h_t[s]
        la = lam_a_t[s]
        exp_h += np.sum(P * lh, axis=(1, 2))
        exp_a += np.sum(P * la, axis=(1, 2))
        if lc_h is not None:
            corners_h += np.sum(P * lc_h_t[s], axis=(1, 2))
            corners_a += np.sum(P * lc_a_t[s], axis=(1, 2))
        qh = 1.0 - np.exp(-lh)
        qa = 1.0 - np.exp(-la)
        stay = P * (1 - qh) * (1 - qa)
        mh = P * qh * (1 - qa)
        ma = P * (1 - qh) * qa
        mb = P * qh * qa
        newP = stay
        newP[:, 1:, :] += mh[:, :-1, :]
        newP[:, -1, :] += mh[:, -1, :]
        newP[:, :, 1:] += ma[:, :, :-1]
        newP[:, :, -1] += ma[:, :, -1]
        newP[:, 1:, 1:] += mb[:, :-1, :-1]
        newP[:, -1, -1] += mb[:, -1, -1]
        P = newP
        if s == last_p1:
            p_ht = P.copy()
    if state.period == 1:
        if p_ht is None:  # origin at the very end of the first half
            p_ht = np.zeros((D, K + 1, K + 1))
            p_ht[:, 0, 0] = 1.0
        p_goal_2h = 1.0 - np.sum(p_ht * no_goal_2h_given, axis=(1, 2))
    else:
        p_goal_2h = 1.0 - p_next_none

    fc = Forecast(
        home_goals=state.home.goals, away_goals=state.away.goals, p_end=P, p_ht=p_ht,
        p_next_home=p_next_home, p_next_away=p_next_away, p_next_none=p_next_none,
        p_goal_next10=p_goal_next10, p_goal_2h=p_goal_2h,
        exp_goals_home=exp_h, exp_goals_away=exp_a, grid=grid, model_name=goal_model,
        p_goal_window=p_goal_window,
    )
    if corners_h is not None:
        fc.corners_home = corners_h
        fc.corners_away = corners_a
        fc.corners_dispersion = corner.dispersion
        fc.corners_now = (int(state.home.corners), int(state.away.corners))
    return fc
