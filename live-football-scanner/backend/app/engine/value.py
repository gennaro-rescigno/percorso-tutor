"""Value engine: implied / fair probabilities, EV, prudential margin, filters and model confidence.

Definitions (per unit stake, decimal odds ``o``):
    implied probability        = 1 / o
    EV                         = p * o - 1                    (binary markets)
    EV (push / quarter lines)  = sum_outcome P(outcome) * payoff(outcome)
    p_conservative             = q10(p over parameter draws) - validation margin(market family)
    EV_conservative            = EV evaluated with p_conservative
A selection is shown only if every filter passes; the reasons for rejection are kept.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .markets import MARKET_FAMILY, OutcomeProbs, Selection

# outcome sets that form a partition (used for de-vigging)
PARTITIONS = {
    "1x2": {"home", "draw", "away"},
    "ht_1x2": {"home", "draw", "away"},
    "total_goals": {"over", "under"},
    "ht_total_goals": {"over", "under"},
    "team_goals_home": {"over", "under"},
    "team_goals_away": {"over", "under"},
    "total_corners": {"over", "under"},
    "btts": {"yes", "no"},
    "goal_2h": {"yes", "no"},
    "dnb": {"home", "away"},
    "next_goal": {"home", "none", "away"},
}


def fair_probabilities(prices: dict[str, float], market: str) -> tuple[dict[str, float], float] | None:
    """Proportional de-vig of a complete outcome set. Returns ({pick: fair_p}, overround)."""
    need = PARTITIONS.get(market)
    if not need or set(prices) != need:
        return None
    inv = {k: 1.0 / v for k, v in prices.items() if v > 1.0}
    if len(inv) != len(need):
        return None
    s = sum(inv.values())
    if s <= 0.9 or s > 1.6:  # implausible book: ignore
        return None
    return {k: v / s for k, v in inv.items()}, s - 1.0


@dataclass
class Evaluation:
    sel: Selection
    label: str
    odds: float
    source: str
    bookmaker: str | None
    p_model: float
    p_low: float
    p_high: float
    p_cons: float
    p_push: float
    implied: float
    p_market_fair: float | None
    overround: float | None
    ev: float
    ev_cons: float
    edge: float
    margin: float
    passed: bool = False
    fail_reasons: list[str] = field(default_factory=list)
    confidence: float = 0.0
    confidence_label: str = "bassa"
    rank_score: float = 0.0
    reasons: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    odds_age_s: float | None = None

    def to_dict(self) -> dict:
        return {
            "key": self.sel.key(), "market": self.sel.market, "pick": self.sel.pick, "line": self.sel.line,
            "label": self.label, "odds": self.odds, "source": self.source, "bookmaker": self.bookmaker,
            "p_model": self.p_model, "p_low": self.p_low, "p_high": self.p_high, "p_cons": self.p_cons,
            "p_push": self.p_push, "implied": self.implied, "p_market_fair": self.p_market_fair,
            "overround": self.overround, "ev": self.ev, "ev_cons": self.ev_cons, "edge": self.edge,
            "margin": self.margin, "passed": self.passed, "fail_reasons": self.fail_reasons,
            "confidence": round(self.confidence, 1), "confidence_label": self.confidence_label,
            "rank_score": self.rank_score, "reasons": self.reasons, "risks": self.risks,
            "odds_age_s": self.odds_age_s,
        }


def evaluate_selection(sel: Selection, label: str, op: OutcomeProbs, odds: float, source: str,
                       bookmaker: str | None, family_margins: dict[str, float], quantile: float,
                       p_market_fair: float | None, overround: float | None) -> Evaluation:
    eff = op.p_effective()  # (D,)
    push = op.push + 0.0
    p_model = float(np.mean(eff))
    p_push = float(np.mean(push))
    lo = float(np.quantile(eff, quantile))
    hi = float(np.quantile(eff, 1 - quantile))
    fam = MARKET_FAMILY.get(sel.market, "")
    margin = float(family_margins.get(fam, 0.05))
    p_cons = max(0.0, lo - margin)
    mean_op = OutcomeProbs(*(np.array([float(np.mean(getattr(op, k)))]) for k in
                             ("win", "half_win", "push", "half_loss", "loss")))
    ev = float(mean_op.ev(odds)[0])
    ev_cons = float(mean_op.ev(odds, win_shift=max(0.0, p_model - p_cons))[0])
    implied = 1.0 / odds
    denom = max(1e-9, 1.0 - p_push)
    edge = p_cons / denom - implied
    return Evaluation(sel=sel, label=label, odds=odds, source=source, bookmaker=bookmaker, p_model=p_model,
                      p_low=lo, p_high=hi, p_cons=p_cons, p_push=p_push, implied=implied,
                      p_market_fair=p_market_fair, overround=overround, ev=ev, ev_cons=ev_cons, edge=edge,
                      margin=margin)


@dataclass
class DataQuality:
    has_stats: bool
    has_corners: bool
    has_xg: bool
    window_minutes: float | None  # minutes of snapshot history behind the 10' window (None = none)
    prior_home_n: int
    prior_away_n: int
    goal_model: str


def confidence_score(ev: Evaluation, dq: DataQuality, minutes_left: float, source_has_state: bool) -> float:
    """Confidence in the *model estimate* (0-100) — not the probability of the event."""
    s = 100.0
    if dq.goal_model == "goals_context":
        s -= 30
    elif dq.goal_model == "goals_stats":
        s -= 5
    if dq.window_minutes is None:
        s -= 15
    elif dq.window_minutes < 10:
        s -= 8
    if dq.prior_home_n < 5 or dq.prior_away_n < 5:
        s -= 10
    s -= min(30.0, 100.0 * (ev.p_high - ev.p_low))
    s -= min(20.0, 400.0 * ev.margin)
    if ev.p_market_fair is not None:
        comp = ev.p_model / max(1e-9, 1 - ev.p_push)
        s -= min(20.0, 100.0 * abs(comp - ev.p_market_fair))
    else:
        s -= 8  # no complete market to compare with
    if not source_has_state:
        s -= 10
    if ev.odds_age_s is not None and ev.odds_age_s > 45:
        s -= 5
    if minutes_left > 60:
        s -= 5
    return float(np.clip(s, 0, 100))


def confidence_label(score: float) -> str:
    if score >= 70:
        return "alta"
    if score >= 50:
        return "media"
    return "bassa"
