"""Market definitions, outcome probabilities from a Forecast, and settlement rules.

Every market is evaluated as a distribution over settlement outcomes
(win / half-win / push / half-loss / loss) so that Asian lines, Draw No Bet and
whole-number totals are priced correctly.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats

from .forecast import K, Forecast

# market key -> human label (Italian)
MARKET_LABELS = {
    "total_goals": "Totale gol (Over/Under)",
    "btts": "Entrambe le squadre segnano",
    "1x2": "Esito finale 1X2",
    "double_chance": "Doppia chance",
    "dnb": "Draw No Bet",
    "team_goals_home": "Gol squadra casa (Over/Under)",
    "team_goals_away": "Gol squadra ospite (Over/Under)",
    "next_goal": "Prossima squadra a segnare",
    "goal_next_10": "Gol nei prossimi 10 minuti",
    "goal_window": "Gol in una finestra di 10 minuti",
    "ht_total_goals": "Totale gol 1° tempo",
    "ht_1x2": "Esito 1° tempo",
    "goal_2h": "Gol nel 2° tempo",
    "correct_score": "Risultato esatto",
    "total_corners": "Totale calci d'angolo",
}

# market families used for validation-based error margins
MARKET_FAMILY = {
    "total_goals": "totals",
    "team_goals_home": "team_totals",
    "team_goals_away": "team_totals",
    "btts": "btts",
    "1x2": "1x2",
    "double_chance": "1x2",
    "dnb": "1x2",
    "next_goal": "next_goal",
    "goal_next_10": "goal_next_10",
    "goal_window": "goal_next_10",
    "ht_total_goals": "ht_totals",
    "ht_1x2": "ht_1x2",
    "goal_2h": "goal_2h",
    "correct_score": "correct_score",
    "total_corners": "corners",
}


@dataclass(frozen=True)
class Selection:
    market: str
    pick: str  # over/under, yes/no, home/draw/away, 1X/X2/12, "2-1", none
    line: float | None = None

    def key(self) -> str:
        ln = "" if self.line is None else f"@{self.line:g}"
        return f"{self.market}:{self.pick}{ln}"

    def label(self, home: str = "Casa", away: str = "Ospite") -> str:
        m = self.market
        p = self.pick
        names = {"home": home, "away": away, "draw": "Pareggio", "none": "Nessun gol"}
        if m in ("total_goals", "ht_total_goals", "total_corners", "team_goals_home", "team_goals_away"):
            prefix = {"team_goals_home": f"{home} ", "team_goals_away": f"{away} "}.get(m, "")
            what = {"total_corners": " corner", "ht_total_goals": " gol 1°T"}.get(m, " gol")
            return f"{prefix}{p.capitalize()} {self.line:g}{what}"
        if m == "btts":
            return f"Entrambe segnano: {'Sì' if p == 'yes' else 'No'}"
        if m in ("1x2", "ht_1x2"):
            suffix = " (1° tempo)" if m == "ht_1x2" else ""
            return f"{names[p]} vince{suffix}" if p != "draw" else f"Pareggio{suffix}"
        if m == "double_chance":
            return f"Doppia chance {p}"
        if m == "dnb":
            return f"Draw No Bet: {names[p]}"
        if m == "next_goal":
            return f"Prossimo gol: {names[p]}"
        if m == "goal_next_10":
            return f"Gol nei prossimi 10': {'Sì' if p == 'yes' else 'No'}"
        if m == "goal_2h":
            return f"Gol nel 2° tempo: {'Sì' if p == 'yes' else 'No'}"
        if m == "goal_window":
            a = int(self.line or 0)
            return f"Gol tra {a}:00 e {a + 9}:59: {'Sì' if p == 'yes' else 'No'}"
        if m == "correct_score":
            return f"Risultato esatto {p}"
        return self.key()


@dataclass
class OutcomeProbs:
    """Per-draw probabilities (arrays of shape (D,))."""

    win: np.ndarray
    half_win: np.ndarray
    push: np.ndarray
    half_loss: np.ndarray
    loss: np.ndarray

    def ev(self, odds: float, win_shift: float = 0.0) -> np.ndarray:
        """EV per unit stake. ``win_shift`` moves probability mass from win to loss (prudential)."""
        w = np.clip(self.win - win_shift, 0.0, 1.0)
        lo = self.loss + (self.win - w)
        return (w * (odds - 1) + self.half_win * (odds - 1) / 2 - self.half_loss * 0.5 - lo)

    def p_effective(self) -> np.ndarray:
        """Win probability counting half outcomes at 1/2 (pushes excluded)."""
        return self.win + 0.5 * self.half_win


def _ou(pmf: np.ndarray, values: np.ndarray, line: float, pick: str) -> OutcomeProbs:
    """Over/Under incl. Asian quarter/whole lines on a discrete distribution.

    pmf: (D, n) probabilities for ``values`` (n,)."""
    def settle_whole_or_half(L: float):
        over = (values > L + 1e-9)
        under = (values < L - 1e-9)
        push = ~over & ~under
        return over, push, under

    frac = round(line * 4) % 4  # 0 whole, 2 half, 1/3 quarter
    D = pmf.shape[0]
    zeros = np.zeros(D)
    if frac in (0, 2):
        over, push, under = settle_whole_or_half(line)
        po, pp, pu = pmf[:, over].sum(1), pmf[:, push].sum(1), pmf[:, under].sum(1)
        if pick == "over":
            return OutcomeProbs(po, zeros, pp, zeros, pu)
        return OutcomeProbs(pu, zeros, pp, zeros, po)
    # quarter line: half stake on each neighbouring line
    lo_line, hi_line = line - 0.25, line + 0.25
    o1, p1, u1 = settle_whole_or_half(lo_line)
    o2, p2, u2 = settle_whole_or_half(hi_line)
    if pick == "under":
        o1, u1 = u1, o1
        o2, u2 = u2, o2
    # outcome classes per value
    win = o1 & o2
    loss = u1 & u2
    half_win = (o1 & p2) | (p1 & o2)
    half_loss = (u1 & p2) | (p1 & u2)
    return OutcomeProbs(pmf[:, win].sum(1), pmf[:, half_win].sum(1), zeros,
                        pmf[:, half_loss].sum(1), pmf[:, loss].sum(1))


def _binary(p_yes: np.ndarray, pick_yes: bool) -> OutcomeProbs:
    z = np.zeros_like(p_yes)
    p = p_yes if pick_yes else 1.0 - p_yes
    return OutcomeProbs(p, z, z, z, 1.0 - p)


def _final_grid(fc: Forecast) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    hg = fc.home_goals + np.arange(K + 1)
    ag = fc.away_goals + np.arange(K + 1)
    H, A = np.meshgrid(hg, ag, indexing="ij")
    return fc.p_end, H, A


def _total_pmf(P: np.ndarray, base: int) -> tuple[np.ndarray, np.ndarray]:
    D = P.shape[0]
    n = 2 * K + 1
    out = np.zeros((D, n))
    for i in range(K + 1):
        for j in range(K + 1):
            out[:, i + j] += P[:, i, j]
    return out, base + np.arange(n)


def _nb_pmf(mean: np.ndarray, alpha: float, nmax: int = 40) -> np.ndarray:
    k = np.arange(nmax + 1)
    mean = np.maximum(mean, 1e-9)
    if alpha <= 1e-6:
        pmf = stats.poisson.pmf(k[None, :], mean[:, None])
    else:
        n = 1.0 / alpha
        p = n / (n + mean)
        pmf = stats.nbinom.pmf(k[None, :], n, p[:, None])
    pmf[:, -1] += np.clip(1.0 - pmf.sum(1), 0, None)
    return pmf


def outcome_probs(fc: Forecast, sel: Selection, period: int,
                  ht_score: tuple[int, int] | None = None) -> OutcomeProbs | None:
    """Return per-draw settlement probabilities, or None if the market cannot be priced."""
    m, p, L = sel.market, sel.pick, sel.line
    P, H, A = _final_grid(fc)
    # markets already decided by the current state are not priced (bookmakers close them)
    if m == "total_goals" and L is not None and fc.home_goals + fc.away_goals > L + 0.25:
        return None
    if m == "team_goals_home" and L is not None and fc.home_goals > L + 0.25:
        return None
    if m == "team_goals_away" and L is not None and fc.away_goals > L + 0.25:
        return None
    if m == "btts" and fc.home_goals > 0 and fc.away_goals > 0:
        return None
    if m == "total_corners" and L is not None and fc.corners_now is not None and sum(fc.corners_now) > L + 0.25:
        return None
    if m == "total_goals" and L is not None:
        pmf, vals = _total_pmf(P, fc.home_goals + fc.away_goals)
        return _ou(pmf, vals, L, p)
    if m in ("team_goals_home", "team_goals_away") and L is not None:
        if m == "team_goals_home":
            pmf, vals = P.sum(2), fc.home_goals + np.arange(K + 1)
        else:
            pmf, vals = P.sum(1), fc.away_goals + np.arange(K + 1)
        return _ou(pmf, vals, L, p)
    if m == "btts":
        yes = ((H > 0) & (A > 0))
        return _binary((P * yes).sum((1, 2)), p == "yes")
    if m in ("1x2", "double_chance", "dnb"):
        ph = (P * (H > A)).sum((1, 2))
        pd = (P * (H == A)).sum((1, 2))
        pa = (P * (H < A)).sum((1, 2))
        z = np.zeros_like(ph)
        if m == "1x2":
            pw = {"home": ph, "draw": pd, "away": pa}[p]
            return OutcomeProbs(pw, z, z, z, 1 - pw)
        if m == "double_chance":
            pw = {"1X": ph + pd, "X2": pd + pa, "12": ph + pa}[p]
            return OutcomeProbs(pw, z, z, z, 1 - pw)
        pw, pl = (ph, pa) if p == "home" else (pa, ph)
        return OutcomeProbs(pw, z, pd, z, pl)
    if m == "next_goal":
        pw = {"home": fc.p_next_home, "away": fc.p_next_away, "none": fc.p_next_none}[p]
        return _binary(pw, True)
    if m == "goal_next_10":
        return _binary(fc.p_goal_next10, p == "yes")
    if m == "goal_window" and L is not None:
        pw = fc.p_goal_window.get(float(L)) if fc.p_goal_window else None
        if pw is None:
            return None
        return _binary(pw, p == "yes")
    if m == "goal_2h":
        if period == 2 and ht_score is not None and fc.home_goals + fc.away_goals > sum(ht_score):
            return None  # already settled
        return _binary(fc.p_goal_2h, p == "yes")
    if m in ("ht_total_goals", "ht_1x2"):
        if period != 1 or fc.p_ht is None:
            return None
        PH = fc.p_ht
        if m == "ht_total_goals" and L is not None:
            pmf, vals = _total_pmf(PH, fc.home_goals + fc.away_goals)
            return _ou(pmf, vals, L, p)
        ph = (PH * (H > A)).sum((1, 2))
        pd = (PH * (H == A)).sum((1, 2))
        pa = (PH * (H < A)).sum((1, 2))
        pw = {"home": ph, "draw": pd, "away": pa}[p]
        return _binary(pw, True)
    if m == "correct_score":
        try:
            h, a = (int(x) for x in p.split("-"))
        except ValueError:
            return None
        i, j = h - fc.home_goals, a - fc.away_goals
        if not (0 <= i <= K and 0 <= j <= K):
            return None
        return _binary(P[:, i, j], True)
    if m == "total_corners" and L is not None:
        if fc.corners_home is None or fc.corners_now is None:
            return None
        mean = fc.corners_home + fc.corners_away
        pmf = _nb_pmf(mean, fc.corners_dispersion)
        vals = sum(fc.corners_now) + np.arange(pmf.shape[1])
        return _ou(pmf, vals, L, p)
    return None


# --------------------------------------------------------------------------------------
# Settlement (used by backtesting)
# --------------------------------------------------------------------------------------

def settle(sel: Selection, final: tuple[int, int], ht: tuple[int, int] | None = None,
           corners_total: int | None = None, next_goal: str | None = None,
           goal_next10: bool | None = None, goal_2h: bool | None = None,
           goal_minutes: list[int] | None = None) -> str | None:
    """Return 'win' | 'half_win' | 'push' | 'half_loss' | 'loss', or None if unknown."""
    fh, fa = final

    def ou(value: int, line: float, pick: str) -> str:
        vals = np.array([value])
        probs = _ou(np.ones((1, 1)), vals, line, pick)
        for name in ("win", "half_win", "push", "half_loss", "loss"):
            if getattr(probs, name)[0] > 0.5:
                return name
        return "loss"

    m, p, L = sel.market, sel.pick, sel.line
    if m == "total_goals":
        return ou(fh + fa, L, p)
    if m == "team_goals_home":
        return ou(fh, L, p)
    if m == "team_goals_away":
        return ou(fa, L, p)
    if m == "btts":
        yes = fh > 0 and fa > 0
        return "win" if (yes == (p == "yes")) else "loss"
    res = "home" if fh > fa else ("away" if fa > fh else "draw")
    if m == "1x2":
        return "win" if res == p else "loss"
    if m == "double_chance":
        ok = {"1X": res in ("home", "draw"), "X2": res in ("draw", "away"), "12": res != "draw"}[p]
        return "win" if ok else "loss"
    if m == "dnb":
        if res == "draw":
            return "push"
        return "win" if res == p else "loss"
    if m == "correct_score":
        return "win" if p == f"{fh}-{fa}" else "loss"
    if m == "next_goal":
        if next_goal is None:
            return None
        return "win" if next_goal == p else "loss"
    if m == "goal_next_10":
        if goal_next10 is None:
            return None
        return "win" if goal_next10 == (p == "yes") else "loss"
    if m == "goal_2h":
        if goal_2h is None:
            return None
        return "win" if goal_2h == (p == "yes") else "loss"
    if m == "goal_window":
        if goal_minutes is None or L is None:
            return None
        # provider minute = elapsed (a goal at 70:xx is reported as minute 71)
        hit = any(L + 1 <= gm <= L + 10 for gm in goal_minutes)
        return "win" if hit == (p == "yes") else "loss"
    if m in ("ht_total_goals", "ht_1x2"):
        if ht is None:
            return None
        hh, ha = ht
        if m == "ht_total_goals":
            return ou(hh + ha, L, p)
        r = "home" if hh > ha else ("away" if ha > hh else "draw")
        return "win" if r == p else "loss"
    if m == "total_corners":
        if corners_total is None:
            return None
        return ou(corners_total, L, p)
    return None


PAYOFF = {"win": lambda o: o - 1, "half_win": lambda o: (o - 1) / 2, "push": lambda o: 0.0,
          "half_loss": lambda o: -0.5, "loss": lambda o: -1.0}


def profit(result: str, odds: float) -> float:
    return float(PAYOFF[result](odds))
