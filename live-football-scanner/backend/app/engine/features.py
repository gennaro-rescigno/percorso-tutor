"""Feature definitions shared by training (historical StatsBomb events) and live inference.

The same functions build the hazard design matrix in both contexts, so the model
never sees a feature at inference time that it was not trained on.

Conventions
-----------
* ``clock`` is the match clock in minutes (0-45 first half, 45-90 second half,
  values above 45 in period 1 / above 90 in period 2 are stoppage time).
* A *slot* is one minute of play ``[clock, clock+1)``.
* A forecast is made at an *origin* (the current live state). The hazard of each
  future slot depends on: what has been observed up to the origin (performance
  features, frozen), the lag between origin and slot (recent pressure fades),
  and the score at that future slot (simulated by the score-state Markov chain).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

# Pseudo-minutes used to shrink in-match rates toward the population mean.
RATE_PSEUDO_MINUTES = 20.0
LAG_BUCKETS = (0.0, 5.0, 15.0, 30.0)  # [0,5) [5,15) [15,30) [30,inf)
CLOCK_BUCKETS = (0.0, 15.0, 30.0, 45.0, 60.0, 75.0)  # in regulation time (period-aware below)


@dataclass
class SideObs:
    """Cumulative observations for one team at the origin. ``None`` = not available."""

    goals: int = 0
    reds: int = 0
    shots: float | None = None
    sot: float | None = None
    corners: float | None = None
    xg: float | None = None


@dataclass
class WindowObs:
    """Counts in the last 10 minutes of play before the origin. ``None`` = not available."""

    shots: float | None = None
    sot: float | None = None
    corners: float | None = None
    xg: float | None = None


@dataclass
class Prior:
    """Pre-match strength expressed as log ratio vs. population mean (0 = average)."""

    att: float = 0.0  # log(goals scored per match / mu)
    defn: float = 0.0  # log(goals conceded per match / mu)
    n_matches: int = 0


@dataclass
class OriginState:
    period: int  # 1 or 2 (half-time origin -> period=2, clock=45)
    clock: float
    home: SideObs = field(default_factory=SideObs)
    away: SideObs = field(default_factory=SideObs)
    home_w10: WindowObs | None = None
    away_w10: WindowObs | None = None
    home_prior: Prior = field(default_factory=Prior)
    away_prior: Prior = field(default_factory=Prior)
    neutral: bool = False

    def minutes_played(self) -> float:
        return max(0.0, self.clock)


# --------------------------------------------------------------------------------------
# Feature specs per model
# --------------------------------------------------------------------------------------

BASE_TIME = ["c15_30", "c30_45", "c45_60", "c60_75", "c75_90", "st1", "st2"]
BASE_STATE = ["d_m2", "d_m1", "d_p1", "d_p2", "trail_late", "lead_late", "gtot"]
BASE_CTX = ["home", "man_up", "man_down", "prior_att", "prior_def_opp"]
LAGS = ["lag0", "lag1", "lag2", "lag3"]


def _lagged(name: str) -> list[str]:
    return [f"{name}_x_{lag}" for lag in LAGS]


GOAL_FEATURES: dict[str, list[str]] = {
    # Baseline: clock + score state + red cards + pre-match strength. No in-play performance.
    "goals_context": ["const", *BASE_TIME, *BASE_STATE, *BASE_CTX],
    # Main live model: adds shot / shot-on-target / corner information (universally available).
    "goals_stats": [
        "const", *BASE_TIME, *BASE_STATE, *BASE_CTX,
        "lr_sot", "lr_shots", "lr_sot_opp",
        *_lagged("w_sot"), *_lagged("w_shots"), *_lagged("w_cor"),
    ],
    # Variant used only when the live feed provides xG.
    "goals_xg": [
        "const", *BASE_TIME, *BASE_STATE, *BASE_CTX,
        "lr_sot", "lr_shots", "lr_xg", "lr_sot_opp",
        *_lagged("w_sot"), *_lagged("w_shots"), *_lagged("w_cor"), *_lagged("w_xg"),
    ],
}

CORNER_FEATURES: dict[str, list[str]] = {
    "corners_stats": [
        "const", *BASE_TIME, "d_m2", "d_m1", "d_p1", "d_p2", "trail_late", "lead_late",
        "home", "man_up", "man_down",
        "lr_cor", "lr_shots", "lr_cor_opp",
        *_lagged("w_cor"), *_lagged("w_shots"),
    ],
}


def lag_bucket(lag: np.ndarray) -> np.ndarray:
    out = np.zeros(lag.shape, dtype=np.int64)
    for i, edge in enumerate(LAG_BUCKETS[1:], start=1):
        out[lag >= edge] = i
    return out


def _log_rate_ratio(count: float | None, minutes: float, ref_per90: float) -> float:
    """Shrunk log ratio of an in-match per-90 rate vs. the population reference."""
    if count is None or ref_per90 <= 0:
        return 0.0
    tau = RATE_PSEUDO_MINUTES
    rate = (count + ref_per90 * tau / 90.0) / (minutes + tau) * 90.0
    return math.log(rate / ref_per90)


def _cap(x: float | None, hi: float) -> float:
    if x is None:
        return 0.0
    return float(min(max(x, 0.0), hi))


@dataclass
class SideFrozen:
    """Origin-time features for one attacking side (do not change during the forecast)."""

    values: dict[str, float]
    goals_for: int
    goals_against: int


def side_frozen_features(state: OriginState, side: int, refs: dict[str, float]) -> SideFrozen:
    """Compute features that are fixed at the origin for attacking ``side`` (0=home, 1=away)."""
    me, opp = (state.home, state.away) if side == 0 else (state.away, state.home)
    w_me = state.home_w10 if side == 0 else state.away_w10
    pr_me = state.home_prior if side == 0 else state.away_prior
    pr_opp = state.away_prior if side == 0 else state.home_prior
    mins = state.minutes_played()
    adv = (opp.reds or 0) - (me.reds or 0)
    v = {
        "const": 1.0,
        "home": 0.0 if state.neutral else (1.0 if side == 0 else 0.0),
        "man_up": 1.0 if adv > 0 else 0.0,
        "man_down": 1.0 if adv < 0 else 0.0,
        "prior_att": pr_me.att,
        "prior_def_opp": pr_opp.defn,
        "lr_sot": _log_rate_ratio(me.sot, mins, refs["sot"]),
        "lr_shots": _log_rate_ratio(me.shots, mins, refs["shots"]),
        "lr_xg": _log_rate_ratio(me.xg, mins, refs["xg"]),
        "lr_sot_opp": _log_rate_ratio(opp.sot, mins, refs["sot"]),
        "lr_cor": _log_rate_ratio(me.corners, mins, refs["corners"]),
        "lr_cor_opp": _log_rate_ratio(opp.corners, mins, refs["corners"]),
    }
    # last-10-minute windows; when unavailable they are imputed with the expected count
    # under the (shrunk) cumulative rate, i.e. "no evidence of a recent change".
    for key, src, cap in (("w_sot", "sot", 5), ("w_shots", "shots", 8), ("w_cor", "corners", 5),
                          ("w_xg", "xg", 2.0)):
        val = getattr(w_me, src) if w_me is not None else None
        if val is None:
            cum = getattr(me, src)
            ref = refs[src]
            tau = RATE_PSEUDO_MINUTES
            if cum is None:
                val = ref * 10 / 90
            else:
                val = (cum + ref * tau / 90) / (mins + tau) * 10
        v[key] = _cap(val, cap)
    return SideFrozen(values=v, goals_for=me.goals, goals_against=opp.goals)


def slot_time_features(period: np.ndarray, clock: np.ndarray) -> dict[str, np.ndarray]:
    """Clock-bucket indicators for each slot. ``clock`` is the slot start minute."""
    p1 = period == 1
    p2 = period == 2
    reg = np.where(p1, np.minimum(clock, 44.999), np.minimum(clock, 89.999))
    f = {
        "c15_30": ((reg >= 15) & (reg < 30)).astype(float),
        "c30_45": ((reg >= 30) & (reg < 45)).astype(float),
        "c45_60": ((reg >= 45) & (reg < 60)).astype(float),
        "c60_75": ((reg >= 60) & (reg < 75)).astype(float),
        "c75_90": ((reg >= 75) & (reg < 90)).astype(float),
        "st1": (p1 & (clock >= 45)).astype(float),
        "st2": (p2 & (clock >= 90)).astype(float),
    }
    f["_tlate"] = np.clip((np.where(p2, clock, 0.0) - 60.0) / 30.0, 0.0, 1.3)
    return f


def design_matrix(
    names: list[str],
    frozen: dict[str, float],
    period: np.ndarray,
    clock: np.ndarray,
    lag: np.ndarray,
    diff: np.ndarray,
    gtot: np.ndarray,
) -> np.ndarray:
    """Build the design matrix for N rows (all arrays broadcast to shape (N,)).

    ``diff`` = goals_for - goals_against of the attacking side *at the slot*;
    ``gtot`` = total goals in the match at the slot.
    """
    n = np.broadcast(period, clock, lag, diff, gtot).shape[0]
    period = np.broadcast_to(period, (n,))
    clock = np.broadcast_to(clock, (n,))
    lag = np.broadcast_to(lag, (n,))
    diff = np.broadcast_to(diff, (n,))
    gtot = np.broadcast_to(gtot, (n,))
    tf = slot_time_features(period, clock)
    lb = lag_bucket(lag)
    tlate = tf["_tlate"]
    cols = {
        **{k: v for k, v in tf.items() if not k.startswith("_")},
        "d_m2": (diff <= -2).astype(float),
        "d_m1": (diff == -1).astype(float),
        "d_p1": (diff == 1).astype(float),
        "d_p2": (diff >= 2).astype(float),
        "trail_late": (diff < 0) * tlate,
        "lead_late": (diff > 0) * tlate,
        "gtot": np.minimum(gtot, 6).astype(float),
    }
    X = np.empty((n, len(names)), dtype=float)
    for j, name in enumerate(names):
        if name in cols:
            X[:, j] = cols[name]
        elif "_x_lag" in name:
            base, lagname = name.split("_x_")
            k = LAGS.index(lagname)
            X[:, j] = frozen[base] * (lb == k)
        else:
            X[:, j] = frozen[name]
    return X
