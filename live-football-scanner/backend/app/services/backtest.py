"""Settlement of opportunities / logged predictions and forward-test performance metrics.

Important: there is no free historical archive of *in-play* odds, so ROI / yield can only be
measured on data this system collects going forward ("paper trading"): every opportunity is
recorded with the odds available at detection and settled on the official result.
Each (fixture, market, selection, line) is counted once (first detection) to avoid
double counting when an opportunity disappears and re-appears.
"""
from __future__ import annotations

import datetime as dt
import math
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import Fixture, MatchEvent, Opportunity, Prediction, StatSnapshot, utcnow
from ..engine.markets import Selection, profit, settle

BANKROLL_UNITS = 100.0
ODDS_BANDS = [(1.75, 2.0), (2.0, 2.5), (2.5, 3.5), (3.5, 6.0), (6.0, 1000.0)]


def _aware(t):
    if t is None:
        return None
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)


def goal_timeline(db: Session, fid: int) -> list[dict]:
    """Goals derived from consecutive score snapshots: [{ts, minute, side}] (VAR reversals removed)."""
    snaps = db.scalars(select(StatSnapshot).where(StatSnapshot.fixture_id == fid).order_by(StatSnapshot.ts)).all()
    goals: list[dict] = []
    prev = None
    for s in snaps:
        cur = (s.home_goals or 0, s.away_goals or 0)
        if prev is not None and cur != prev:
            minute = (s.elapsed or 0) + (s.extra or 0)
            for idx, side in ((0, "home"), (1, "away")):
                d = cur[idx] - prev[idx]
                for _ in range(max(d, 0)):
                    goals.append({"ts": _aware(s.ts), "minute": minute, "side": side, "status": s.status})
                for _ in range(max(-d, 0)):  # disallowed goal
                    for j in range(len(goals) - 1, -1, -1):
                        if goals[j]["side"] == side:
                            goals.pop(j)
                            break
        prev = cur
    return goals


def _event_goal_minutes(db: Session, fid: int) -> list[int]:
    evs = db.scalars(select(MatchEvent).where(MatchEvent.fixture_id == fid, MatchEvent.type == "Goal")).all()
    return [int(e.minute or 0) for e in evs if (e.detail or "").lower() != "missed penalty"]


def _settle_one(sel: Selection, row: Fixture, at_ts: dt.datetime, at_score: tuple[int, int], at_minute: int | None,
                at_period: int | None, goals: list[dict], ev_minutes: list[int]) -> str | None:
    final = (row.ft_home, row.ft_away)
    if final[0] is None or final[1] is None:
        return None
    ht = (row.ht_home, row.ht_away) if row.ht_home is not None else None
    corners = None
    if row.corners_home_final is not None and row.corners_away_final is not None:
        corners = int(row.corners_home_final + row.corners_away_final)
    after = [g for g in goals if g["ts"] and g["ts"] > at_ts and g["status"] in ("1H", "2H", "HT")]
    next_goal = None
    if after:
        next_goal = after[0]["side"]
    elif final == at_score:
        next_goal = "none"
    elif final[0] > at_score[0] and final[1] == at_score[1]:
        next_goal = "home"
    elif final[1] > at_score[1] and final[0] == at_score[0]:
        next_goal = "away"
    goal10 = None
    if at_minute is not None:
        if goals:
            goal10 = any(g["ts"] > at_ts and g["minute"] <= at_minute + 10 for g in goals)
        elif final == at_score:
            goal10 = False
    goal_2h = None
    if ht is not None:
        goal_2h = (final[0] + final[1]) > (ht[0] + ht[1])
    minutes = [g["minute"] for g in goals] or ev_minutes
    return settle(sel, final, ht, corners, next_goal, goal10, goal_2h, minutes)


def settle_fixture(db: Session, row: Fixture, void: bool = False) -> int:
    goals = goal_timeline(db, row.id)
    ev_minutes = _event_goal_minutes(db, row.id)
    n = 0
    opps = db.scalars(select(Opportunity).where(Opportunity.fixture_id == row.id, Opportunity.result.is_(None))).all()
    for o in opps:
        if void:
            res = "void"
        else:
            sc = tuple(int(x) for x in o.score_at_detection.split("-"))
            res = _settle_one(Selection(o.market, o.pick, o.line), row, _aware(o.first_seen), sc,
                              o.minute_at_detection, o.period_at_detection, goals, ev_minutes) or "void"
        o.result = res
        o.profit = 0.0 if res == "void" else profit(res, o.odds_at_detection)
        if o.status == "active":
            o.status = "settled"
            o.invalidation_reason = o.invalidation_reason or "Partita terminata"
            o.invalidated_at = o.invalidated_at or utcnow()
            o.closing_odds = o.closing_odds or o.last_odds
        o.settled_at = utcnow()
        n += 1
    preds = db.scalars(select(Prediction).where(Prediction.fixture_id == row.id, Prediction.result.is_(None))).all()
    for p in preds:
        if void:
            p.result = "void"
            continue
        p.result = _settle_one(Selection(p.market, p.pick, p.line), row, _aware(p.ts), (p.home_goals, p.away_goals),
                               p.elapsed, p.period, goals, ev_minutes) or "void"
    db.commit()
    return n


def _agg(rows: list[Opportunity]) -> dict:
    n = len(rows)
    if n == 0:
        return {"n": 0}
    wins = sum(1 for o in rows if o.result in ("win", "half_win"))
    pushes = sum(1 for o in rows if o.result == "push")
    prof = sum(o.profit or 0.0 for o in rows)
    exp_ev = sum(o.ev_cons_at_detection for o in rows) / n
    p_model = sum(o.p_model_at_detection for o in rows) / n
    clv = [o.odds_at_detection / o.closing_odds - 1 for o in rows if o.closing_odds]
    decided = max(n - pushes, 1)
    return {
        "n": n, "wins": wins, "pushes": pushes, "losses": n - wins - pushes, "hit_rate": wins / decided,
        "avg_p_model": p_model, "staked": float(n), "profit": prof, "yield": prof / n,
        "roi_bankroll": prof / BANKROLL_UNITS, "avg_odds": sum(o.odds_at_detection for o in rows) / n,
        "avg_ev_cons_expected": exp_ev, "clv": (sum(clv) / len(clv)) if clv else None,
    }


def _calibration(pairs: list[tuple[float, int]], bins: int = 10) -> dict:
    if not pairs:
        return {"n": 0, "bins": []}
    out = []
    for i in range(bins):
        lo, hi = i / bins, (i + 1) / bins
        sel = [(p, y) for p, y in pairs if lo <= p < hi or (i == bins - 1 and p == 1.0)]
        if not sel:
            continue
        mp = sum(p for p, _ in sel) / len(sel)
        of = sum(y for _, y in sel) / len(sel)
        out.append({"p_mean": mp, "obs": of, "n": len(sel)})
    brier = sum((p - y) ** 2 for p, y in pairs) / len(pairs)
    ll = -sum(y * math.log(max(p, 1e-6)) + (1 - y) * math.log(max(1 - p, 1e-6)) for p, y in pairs) / len(pairs)
    return {"n": len(pairs), "bins": out, "brier": brier, "logloss": ll}


def metrics(db: Session) -> dict:
    rows = db.scalars(select(Opportunity).where(Opportunity.result.is_not(None), Opportunity.result != "void")
                      .order_by(Opportunity.first_seen)).all()
    first: dict[tuple, Opportunity] = {}
    for o in rows:
        first.setdefault((o.fixture_id, o.market, o.pick, o.line), o)
    opps = list(first.values())
    fx = {f.id: f for f in db.scalars(select(Fixture).where(Fixture.id.in_({o.fixture_id for o in opps})))} if opps else {}
    by_market, by_league, by_band, by_conf = defaultdict(list), defaultdict(list), defaultdict(list), defaultdict(list)
    for o in opps:
        by_market[o.market].append(o)
        f = fx.get(o.fixture_id)
        by_league[(f.league_name if f else "?") or "?"].append(o)
        for lo, hi in ODDS_BANDS:
            if lo <= o.odds_at_detection < hi:
                by_band[f"{lo:.2f}-{hi:.2f}" if hi < 100 else f"{lo:.2f}+"].append(o)
        by_conf[o.confidence_at_detection].append(o)
    equity, cum, peak, mdd = [], 0.0, 0.0, 0.0
    for o in sorted(opps, key=lambda o: _aware(o.settled_at) or _aware(o.first_seen)):
        cum += o.profit or 0.0
        peak = max(peak, cum)
        mdd = max(mdd, peak - cum)
        equity.append({"t": (_aware(o.settled_at) or _aware(o.first_seen)).isoformat(), "profit": cum})
    preds = db.scalars(select(Prediction).where(Prediction.result.in_(("win", "loss")))).all()
    pairs_all = [(p.p_model, 1 if p.result == "win" else 0) for p in preds]
    pairs_opp = [(o.p_model_at_detection, 1 if o.result == "win" else 0) for o in opps if o.result in ("win", "loss")]
    pending = db.scalars(select(Opportunity).where(Opportunity.result.is_(None))).all()
    return {
        "note": ("Forward test su dati raccolti da questo sistema (nessuno storico di quote live gratuito "
                 "disponibile). Ogni selezione conta una sola volta (prima rilevazione), stake 1u, "
                 f"bankroll nozionale {BANKROLL_UNITS:.0f}u. Yield = profitto / stake totale; "
                 "ROI bankroll = profitto / bankroll; CLV = quota rilevata / ultima quota vista - 1."),
        "overall": _agg(opps),
        "max_drawdown": mdd,
        "by_market": {k: _agg(v) for k, v in sorted(by_market.items())},
        "by_league": {k: _agg(v) for k, v in sorted(by_league.items())},
        "by_odds_band": {k: _agg(v) for k, v in by_band.items()},
        "by_confidence": {k: _agg(v) for k, v in by_conf.items()},
        "equity": equity,
        "calibration_predictions": _calibration(pairs_all),
        "calibration_opportunities": _calibration(pairs_opp),
        "pending": len(pending),
    }
