"""Build the model's OriginState from live provider data + the stored snapshot history.

API-Football statistics are cumulative, so the "last 5/10/15 minutes" windows are
computed as differences between the current snapshot and the snapshot taken 5/10/15
minutes of play earlier. If the scanner has not been running long enough the window
is reported as unavailable (never invented).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from ..engine.features import OriginState, Prior, SideObs, WindowObs

WINDOW_STATS = ("shots", "sot", "corners", "xg")


@dataclass
class Snap:
    status: str | None
    elapsed: int | None
    extra: int | None
    home_goals: int
    away_goals: int
    stats: dict | None


def clock_of(status: str | None, elapsed: int | None, extra: int | None) -> tuple[int | None, float | None]:
    """(period, clock). Half-time maps to the start of the 2nd half."""
    if status == "1H":
        return 1, float(min(elapsed or 0, 45) + (extra or 0) if (elapsed or 0) >= 45 else (elapsed or 0))
    if status == "HT":
        return 2, 45.0
    if status == "2H":
        e = elapsed or 46
        return 2, float(min(e, 90) + (extra or 0) if e >= 90 else e)
    return None, None


def play_time(period: int, clock: float, first_half_extra: float) -> float:
    return clock if period == 1 else 45.0 + first_half_extra + (clock - 45.0)


def first_half_extra(history: list[Snap]) -> float:
    ex = [s.extra or 0 for s in history if s.status == "1H" and (s.elapsed or 0) >= 45]
    return float(max(ex)) if ex else 2.0


def window_counts(history: list[Snap], current: Snap, minutes: float) -> tuple[dict | None, float | None]:
    """Counts in the last ``minutes`` of play. Returns ({side: {stat: n}}, minutes covered)."""
    if current.stats is None:
        return None, None
    p0, c0 = clock_of(current.status, current.elapsed, current.extra)
    if p0 is None:
        return None, None
    fh = first_half_extra(history)
    pt0 = play_time(p0, c0, fh) if current.status != "HT" else 45.0 + fh
    best = None
    best_pt = None
    earliest_pt = None
    for s in history:
        p, c = clock_of(s.status, s.elapsed, s.extra)
        if p is None or s.stats is None:
            continue
        pt = play_time(p, c, fh) if s.status != "HT" else 45.0 + fh
        earliest_pt = pt if earliest_pt is None else min(earliest_pt, pt)
        if pt <= pt0 - minutes + 0.5 and (best_pt is None or pt > best_pt):
            best, best_pt = s, pt
    if best is None:
        # the scanner saw the match from (almost) kick-off: counts so far are the window
        if earliest_pt is not None and earliest_pt <= 2.0 and pt0 <= minutes + 0.5:
            return {side: {k: current.stats[side].get(k) for k in WINDOW_STATS} for side in ("home", "away")}, pt0
        return None, (pt0 - earliest_pt) if earliest_pt is not None else None
    out = {}
    for side in ("home", "away"):
        out[side] = {}
        for k in WINDOW_STATS:
            a = current.stats[side].get(k)
            b = best.stats[side].get(k)
            out[side][k] = None if a is None or b is None else max(0.0, a - b)
    return out, pt0 - best_pt


def prior_from_form(form: dict | None, mu: float, k: float) -> Prior:
    if not form or not form.get("matches"):
        return Prior()
    n = int(form["matches"])
    gf, ga = float(form["goals_for"]), float(form["goals_against"])
    return Prior(att=math.log(((gf + k * mu) / (n + k)) / mu), defn=math.log(((ga + k * mu) / (n + k)) / mu),
                 n_matches=n)


def side_obs(stats: dict | None, side: str, goals: int, reds_events: int) -> SideObs:
    if stats is None:
        return SideObs(goals=goals, reds=reds_events)
    st = stats.get(side) or {}
    reds = max(int(st.get("red") or 0), reds_events)
    return SideObs(goals=goals, reds=reds, shots=st.get("shots"), sot=st.get("sot"), corners=st.get("corners"),
                   xg=st.get("xg"))


def build_origin(current: Snap, history: list[Snap], form_home: dict | None, form_away: dict | None,
                 mu: float, k: float, reds_home_ev: int = 0, reds_away_ev: int = 0) -> tuple[OriginState, dict]:
    period, clock = clock_of(current.status, current.elapsed, current.extra)
    if period is None:
        raise ValueError(f"stato partita non analizzabile: {current.status}")
    w10, cov10 = window_counts(history, current, 10)
    w5, _ = window_counts(history, current, 5)
    w15, cov15 = window_counts(history, current, 15)

    def wobs(w, side):
        if w is None:
            return None
        d = w[side]
        return WindowObs(shots=d.get("shots"), sot=d.get("sot"), corners=d.get("corners"), xg=d.get("xg"))

    state = OriginState(
        period=period, clock=clock,
        home=side_obs(current.stats, "home", current.home_goals, reds_home_ev),
        away=side_obs(current.stats, "away", current.away_goals, reds_away_ev),
        home_w10=wobs(w10, "home"), away_w10=wobs(w10, "away"),
        home_prior=prior_from_form(form_home, mu, k), away_prior=prior_from_form(form_away, mu, k),
    )
    windows = {"w5": w5, "w10": w10, "w15": w15, "coverage_min": cov10 if w10 is not None else cov15}
    return state, windows
