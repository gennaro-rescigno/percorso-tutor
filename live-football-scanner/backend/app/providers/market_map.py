"""Map bookmaker / provider market names onto the engine's market keys.

Provider bet names are not standardised, so mapping is rule based and *conservative*:
anything that cannot be mapped unambiguously is skipped and reported as "unmapped"
(visible in /api/health), never guessed. Rest-of-match / Asian handicap / booking-points
markets are deliberately not mapped because their settlement depends on bookmaker rules.
"""
from __future__ import annotations

import re

_NUM = r"(\d+(?:\.\d+)?)"

# (regex on lowercase bet name, market key). First match wins.
WINDOW_RX = re.compile(r"(\d{1,2})[:.]00\s*(?:-|–|to|and)\s*(\d{1,2})[:.]59")

RULES: list[tuple[re.Pattern, str]] = [
    # fixed 10-minute goal windows, e.g. "Goal between 70:00 - 79:59" (must precede the skip rule)
    (re.compile(r"goal.*\d{1,2}[:.]00\s*(?:-|–|to|and)\s*\d{1,2}[:.]59"), "goal_window"),
    (re.compile(r"(asian|handicap|rest of|remaining|booking|player|anytime|first goalscorer|last goal|"
                r"exact goals|exact total|number of goals|odd/even|odd-even|half time/full time|ht/ft|win to nil|clean sheet|margin|method|"
                r"race to|multi|combo|&| and |minute|interval|period|3-way|corner (1x2|handicap)|"
                r"first corner|last corner|next corner)"), "__skip__"),
    (re.compile(r"^(fulltime result|match winner|full time result|1x2|match result|3way result)$"), "1x2"),
    (re.compile(r"^(1x2 \(1st half\)|first half winner|1st half result|half time result|1st half - 1x2|"
                r"first half result|1x2 - 1st half)$"), "ht_1x2"),
    (re.compile(r"^double chance$"), "double_chance"),
    (re.compile(r"^(draw no bet|home/away)$"), "dnb"),
    (re.compile(r"^both teams (to )?score$"), "btts"),
    (re.compile(r"^(over/under line|match goals|goals over/under|over/under|total goals|goal line|"
                r"total - goals|over/under goals)$"), "total_goals"),
    (re.compile(r"^(goals over/under first half|1st half goals|over/under \(1st half\)|first half goals|"
                r"1st half - over/under|over/under 1st half|goal line \(1st half\)|1st half goal line)$"),
     "ht_total_goals"),
    (re.compile(r"^(home team goals|total - home|home team total goals|home total goals|home team - total goals)$"),
     "team_goals_home"),
    (re.compile(r"^(away team goals|total - away|away team total goals|away total goals|away team - total goals)$"),
     "team_goals_away"),
    (re.compile(r"^(total corners|corners over/under|match corners|corners over under|corners - over/under|"
                r"total corners \(over/under\))$"), "total_corners"),
    (re.compile(r"^(correct score|final score|exact score)$"), "correct_score"),
    (re.compile(r"^(next goal|team to score next|which team will score the \d+(st|nd|rd|th) goal\?|"
                r"\d+(st|nd|rd|th) goal|next team to score)$"), "next_goal"),
    (re.compile(r"^(goal in 2nd half|2nd half - goal|second half goal|goals in 2nd half|to score in 2nd half|"
                r"2nd half goal)$"), "goal_2h"),
]


def classify(name: str) -> str | None:
    n = " ".join(name.lower().strip().split())
    for rx, key in RULES:
        if rx.search(n):
            return None if key == "__skip__" else key
    return None


def nth_goal(name: str) -> int | None:
    m = re.search(r"(\d+)(st|nd|rd|th) goal", name.lower())
    return int(m.group(1)) if m else None


def _f(x) -> float | None:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def parse_selection(market: str, value: str, handicap, home_name: str = "", away_name: str = "",
                    current_total: int | None = None, raw_name: str = "") -> tuple[str, float | None] | None:
    """Return (pick, line) or None if the selection cannot be interpreted unambiguously."""
    v = " ".join(str(value).strip().split())
    vl = v.lower()
    line = _f(handicap)

    if market in ("total_goals", "ht_total_goals", "team_goals_home", "team_goals_away", "total_corners"):
        m = re.match(rf"^(over|under)\s*{_NUM}?$", vl)
        if not m:
            return None
        pick = m.group(1)
        if m.group(2) is not None:
            line = float(m.group(2))
        if line is None:
            return None
        # quarter / half / whole lines are all supported by the settlement engine
        if abs(line * 4 - round(line * 4)) > 1e-9:
            return None
        return pick, line
    if market in ("1x2", "ht_1x2"):
        m = {"home": "home", "1": "home", "draw": "draw", "x": "draw", "away": "away", "2": "away"}
        if vl in m:
            return m[vl], None
        if home_name and vl == home_name.lower():
            return "home", None
        if away_name and vl == away_name.lower():
            return "away", None
        return None
    if market == "double_chance":
        m = {"home/draw": "1X", "1x": "1X", "draw/away": "X2", "x2": "X2", "home/away": "12", "12": "12"}
        return (m[vl], None) if vl in m else None
    if market == "dnb":
        m = {"home": "home", "1": "home", "away": "away", "2": "away"}
        if vl in m:
            return m[vl], None
        if home_name and vl == home_name.lower():
            return "home", None
        if away_name and vl == away_name.lower():
            return "away", None
        return None
    if market == "goal_window":
        m = WINDOW_RX.search(raw_name)
        if not m:
            return None
        a, b = int(m.group(1)), int(m.group(2))
        if b + 1 - a != 10 or a < 0 or (a < 45 < b + 1):
            return None  # only 10-minute windows that do not straddle half-time
        yn = {"yes": "yes", "no": "no"}.get(vl)
        return (yn, float(a)) if yn else None
    if market in ("btts", "goal_2h"):
        return ({"yes": ("yes", None), "no": ("no", None)}).get(vl)
    if market == "correct_score":
        m = re.match(r"^(\d+)\s*[:\-]\s*(\d+)$", vl)
        return (f"{int(m.group(1))}-{int(m.group(2))}", None) if m else None
    if market == "next_goal":
        n = nth_goal(raw_name)
        if n is not None and current_total is not None and n != current_total + 1:
            return None  # not the *next* goal
        m = {"home": "home", "1": "home", "away": "away", "2": "away", "no goal": "none", "none": "none",
             "no goals": "none", "neither": "none"}
        if vl in m:
            return m[vl], None
        if home_name and vl == home_name.lower():
            return "home", None
        if away_name and vl == away_name.lower():
            return "away", None
        return None
    return None
