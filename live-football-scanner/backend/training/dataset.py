"""Turn the compact StatsBomb event log into (origin, future-slot) training rows.

Each match contributes several forecast origins (every 5 minutes with a per-match
offset, plus half-time). For every origin we freeze what was observable at that
moment (cumulative shots / shots on target / corners / xG / red cards, the last
10 minutes window, pre-match form) and create one row per future one-minute slot
and attacking team, with the actual score at that slot and the goals / corners
scored in it as targets.
"""
from __future__ import annotations

import json
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.engine.features import (CORNER_FEATURES, GOAL_FEATURES, OriginState, Prior, SideObs,
                                  WindowObs, design_matrix, side_frozen_features)
from app.engine.forecast import build_slot_grid

DATA = Path(__file__).resolve().parent.parent / "data" / "statsbomb_compact.jsonl"
TEMPORAL_SPLIT_DATE = "2016-03-01"
FORM_WINDOW = 10

ALL_FEATURES: list[str] = []
for spec in list(GOAL_FEATURES.values()) + list(CORNER_FEATURES.values()):
    for f in spec:
        if f not in ALL_FEATURES:
            ALL_FEATURES.append(f)


def load_matches(path: Path = DATA) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def split_of(m: dict) -> str:
    if m["role"] == "cross":
        return "val_cross"
    return "train" if m["date"] < TEMPORAL_SPLIT_DATE else "val_temporal"


def goals_mu(matches: list[dict]) -> float:
    tr = [m for m in matches if split_of(m) == "train"]
    return float(np.mean([m["reg_home_goals"] + m["reg_away_goals"] for m in tr]) / 2.0)


def compute_priors(matches: list[dict], mu: float, k: float) -> dict[int, tuple[Prior, Prior]]:
    """Form prior from each team's previous (<= 10) matches in the same competition."""
    by_comp = defaultdict(list)
    for m in matches:
        by_comp[m["competition"]].append(m)
    out: dict[int, tuple[Prior, Prior]] = {}
    for comp, ms in by_comp.items():
        ms.sort(key=lambda m: (m["date"], m["match_id"]))
        hist: dict[int, deque] = defaultdict(lambda: deque(maxlen=FORM_WINDOW))
        for m in ms:
            pri = []
            for tid in (m["home_id"], m["away_id"]):
                h = hist[tid]
                n = len(h)
                gf = sum(x[0] for x in h)
                ga = sum(x[1] for x in h)
                att = np.log(((gf + k * mu) / (n + k)) / mu)
                dfn = np.log(((ga + k * mu) / (n + k)) / mu)
                pri.append(Prior(att=float(att), defn=float(dfn), n_matches=n))
            out[m["match_id"]] = (pri[0], pri[1])
            hist[m["home_id"]].append((m["reg_home_goals"], m["reg_away_goals"]))
            hist[m["away_id"]].append((m["reg_away_goals"], m["reg_home_goals"]))
    return out


def compute_refs(matches: list[dict]) -> dict[str, float]:
    tr = [m for m in matches if split_of(m) == "train"]
    tot = defaultdict(float)
    minutes = 0.0
    for m in tr:
        minutes += 2 * (m["period_end"]["1"] + m["period_end"]["2"] - 45.0)  # two teams
        for ev in m["events"]:
            kind = ev[3]
            if kind == "shot":
                tot["shots"] += 1
                tot["sot"] += ev[4]
                tot["xg"] += ev[5]
            elif kind == "corner":
                tot["corners"] += 1
    per90 = minutes / 90.0
    return {k: tot[k] / per90 for k in ("shots", "sot", "xg", "corners")}


def stoppage_distribution(matches: list[dict], comps_modern: set[str], kmax: int = 16) -> dict[str, list[float]]:
    """Empirical distribution of played added time per half (modern competitions)."""
    out = {}
    for key, nominal in (("1", 45.0), ("2", 90.0)):
        vals = [max(0.0, m["period_end"][key] - nominal) for m in matches
                if m["competition"] in comps_modern and key in m["period_end"]]
        hist = np.zeros(kmax)
        for v in vals:
            # ST = k means the period lasts nominal + k minutes; spread fractional part
            lo = int(np.floor(v))
            fr = v - lo
            hist[min(lo, kmax - 1)] += 1 - fr
            hist[min(lo + 1, kmax - 1)] += fr
        hist = hist / hist.sum()
        out["h" + key] = [round(float(x), 5) for x in hist]
    return out


@dataclass
class Timeline:
    pt: np.ndarray  # play-time of each event
    period: np.ndarray
    t: np.ndarray
    side: np.ndarray
    kind: np.ndarray
    on_t: np.ndarray
    xg: np.ndarray
    end1: float
    end2: float


def timeline(m: dict) -> Timeline:
    ev = m["events"]
    end1 = float(m["period_end"].get("1", 45.0))
    end2 = float(m["period_end"].get("2", 90.0))
    if not ev:
        z = np.zeros(0)
        return Timeline(z, z.astype(int), z, z.astype(int), np.array([], dtype=object), z, z, end1, end2)
    period = np.array([e[0] for e in ev], dtype=int)
    t = np.array([e[1] for e in ev], dtype=float)
    pt = np.where(period == 1, t, end1 + (t - 45.0))
    return Timeline(pt=pt, period=period, t=t, side=np.array([e[2] for e in ev], dtype=int),
                    kind=np.array([e[3] for e in ev], dtype=object),
                    on_t=np.array([e[4] for e in ev], dtype=float),
                    xg=np.array([e[5] for e in ev], dtype=float), end1=end1, end2=end2)


def origins_for(m: dict, tl: Timeline) -> list[tuple[int, float]]:
    off = m["match_id"] % 5
    out: list[tuple[int, float]] = []
    c = 2.0 + off
    while c < min(45.0, tl.end1):
        out.append((1, float(c)))
        c += 5.0
    out.append((2, 45.0))  # half-time
    c = 47.0 + off
    while c < tl.end2 - 0.5:
        out.append((2, float(c)))
        c += 5.0
    return out


def origin_pt(tl: Timeline, period: int, clock: float) -> float:
    if period == 1:
        return clock
    return tl.end1 + (clock - 45.0)


def _sum(mask: np.ndarray, kind: str, side: int, tl: Timeline, field: str | None = None) -> float:
    sel = mask & (tl.kind == kind) & (tl.side == side)
    if field is None:
        return float(sel.sum())
    return float(getattr(tl, field)[sel].sum())


def origin_state(m: dict, tl: Timeline, period: int, clock: float,
                 priors: tuple[Prior, Prior], with_xg: bool = True) -> OriginState:
    pt0 = origin_pt(tl, period, clock)
    if period == 2 and clock <= 45.0:
        before = tl.period == 1
    else:
        before = tl.pt < pt0
    win = before & (tl.pt >= pt0 - 10.0)
    sides = []
    windows = []
    for s in (0, 1):
        sides.append(SideObs(
            goals=int(_sum(before, "goal", s, tl)),
            reds=int(_sum(before, "red", s, tl)),
            shots=_sum(before, "shot", s, tl),
            sot=_sum(before, "shot", s, tl, "on_t"),
            corners=_sum(before, "corner", s, tl),
            xg=_sum(before, "shot", s, tl, "xg") if with_xg else None,
        ))
        windows.append(WindowObs(
            shots=_sum(win, "shot", s, tl),
            sot=_sum(win, "shot", s, tl, "on_t"),
            corners=_sum(win, "corner", s, tl),
            xg=_sum(win, "shot", s, tl, "xg") if with_xg else None,
        ))
    neutral = m["role"] == "cross" and "League" not in m["competition"] and "Bundesliga" not in m["competition"]
    return OriginState(period=period, clock=clock if period == 1 else max(clock, 45.0),
                       home=sides[0], away=sides[1], home_w10=windows[0], away_w10=windows[1],
                       home_prior=priors[0], away_prior=priors[1], neutral=neutral)


@dataclass
class OriginRecord:
    match_id: int
    competition: str
    split: str
    period: int
    clock: float
    state: OriginState
    end1: float
    end2: float
    # outcomes
    final: tuple[int, int]
    ht: tuple[int, int]
    next_goal: int  # 0 home, 1 away, 2 none
    goal_next10: int
    goal_2h: int
    goals_2h: int
    corners_final: tuple[int, int]


def outcomes(tl: Timeline, m: dict, period: int, clock: float) -> dict:
    pt0 = origin_pt(tl, period, clock)
    is_goal = tl.kind == "goal"
    after = (tl.period == 2) if (period == 2 and clock <= 45.0) else (tl.pt >= pt0)
    g_after = is_goal & after
    if g_after.any():
        first = np.argmin(np.where(g_after, tl.pt, np.inf))
        nxt = int(tl.side[first])
    else:
        nxt = 2
    # next 10 minutes of play
    if period == 2 and clock <= 45.0:
        start = tl.end1
    else:
        start = pt0
    g10 = int((is_goal & (tl.pt >= start) & (tl.pt < start + 10.0)).any())
    g2h = int((is_goal & (tl.period == 2)).sum())
    ht = (int((is_goal & (tl.period == 1) & (tl.side == 0)).sum()),
          int((is_goal & (tl.period == 1) & (tl.side == 1)).sum()))
    cor = (int(((tl.kind == "corner") & (tl.side == 0)).sum()), int(((tl.kind == "corner") & (tl.side == 1)).sum()))
    return dict(final=(m["reg_home_goals"], m["reg_away_goals"]), ht=ht, next_goal=nxt, goal_next10=g10,
                goal_2h=int(g2h > 0), goals_2h=g2h, corners_final=cor)


def build(matches: list[dict], priors: dict, refs: dict, stoppage: dict,
          splits_for_rows: set[str], keep_records: set[str]):
    """Training rows for the requested splits plus origin records (with outcomes) for validation."""
    Xs, offs, yg, yc, grp, spl, oids = [], [], [], [], [], [], []
    oid = 0
    records: list[OriginRecord] = []
    name_idx = {n: i for i, n in enumerate(ALL_FEATURES)}
    for m in matches:
        sp = split_of(m)
        if sp not in splits_for_rows and sp not in keep_records:
            continue
        tl = timeline(m)
        pri = priors[m["match_id"]]
        for period, clock in origins_for(m, tl):
            st = origin_state(m, tl, period, clock, pri)
            if sp in keep_records:
                records.append(OriginRecord(m["match_id"], m["competition"], sp, period, st.clock, st,
                                            tl.end1, tl.end2, **outcomes(tl, m, period, clock)))
            if sp not in splits_for_rows:
                continue
            oid += 1
            grid = build_slot_grid(st, stoppage, end1_actual=tl.end1, end2_actual=tl.end2)
            if len(grid.clock) == 0:
                continue
            slot_pt = np.where(grid.period == 1, grid.clock, tl.end1 + (grid.clock - 45.0))
            goal_pt = tl.pt[tl.kind == "goal"]
            goal_side = tl.side[tl.kind == "goal"]
            cor_pt = tl.pt[tl.kind == "corner"]
            cor_side = tl.side[tl.kind == "corner"]
            # score at slot start (actual)
            gh = (goal_pt[None, goal_side == 0] < slot_pt[:, None]).sum(axis=1)
            ga = (goal_pt[None, goal_side == 1] < slot_pt[:, None]).sum(axis=1)
            for side in (0, 1):
                fr = side_frozen_features(st, side, refs)
                diff = (gh - ga) if side == 0 else (ga - gh)
                X = design_matrix(ALL_FEATURES, fr.values, grid.period, grid.clock, grid.lag, diff, gh + ga)
                in_slot = lambda pts, sides: ((pts[None, sides == side] >= slot_pt[:, None]) &
                                              (pts[None, sides == side] < slot_pt[:, None] + 1.0)).sum(axis=1)
                Xs.append(X.astype(np.float32))
                offs.append(np.log(grid.weight))
                yg.append(in_slot(goal_pt, goal_side))
                yc.append(in_slot(cor_pt, cor_side))
                grp.append(np.full(len(grid.clock), m["match_id"]))
                spl.append(np.full(len(grid.clock), sp))
                oids.append(np.full(len(grid.clock), oid))
    if Xs:
        X = np.vstack(Xs)
        return dict(X=X, offset=np.concatenate(offs), y_goal=np.concatenate(yg), y_corner=np.concatenate(yc),
                    groups=np.concatenate(grp), split=np.concatenate(spl), oid=np.concatenate(oids),
                    records=records, name_idx=name_idx)
    return dict(X=None, records=records, name_idx=name_idx)
