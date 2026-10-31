"""Provider-agnostic data structures. Every provider maps its payloads onto these."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

# Statistic keys we normalise to (None = not provided by the source for this fixture)
STAT_KEYS = [
    "shots", "sot", "shots_off", "blocked", "shots_in_box", "shots_out_box", "corners", "possession",
    "fouls", "yellow", "red", "saves", "offsides", "passes", "passes_acc", "xg",
    # not offered by API-Football; kept so the UI can state explicitly that they are missing
    "dangerous_attacks", "attacks", "big_chances", "xgot",
]

LIVE_STATUSES = {"1H", "HT", "2H", "ET", "BT", "P", "LIVE", "INT", "SUSP"}
FINISHED_STATUSES = {"FT", "AET", "PEN"}
VOID_STATUSES = {"PST", "CANC", "ABD", "AWD", "WO"}


class ProviderError(RuntimeError):
    pass


class QuotaExceeded(ProviderError):
    pass


@dataclass
class MatchEventData:
    minute: int | None
    extra: int | None
    side: str | None  # "home" | "away"
    type: str  # Goal | Card | subst | Var
    detail: str | None
    player: str | None

    def signature(self) -> str:
        return f"{self.minute}|{self.extra}|{self.side}|{self.type}|{self.detail}|{self.player}"


@dataclass
class LiveFixture:
    id: int
    league_id: int | None
    league_name: str | None
    country: str | None
    season: int | None
    round: str | None
    home_id: int | None
    home_name: str
    away_id: int | None
    away_name: str
    kickoff: dt.datetime | None
    status: str
    elapsed: int | None
    extra: int | None
    home_goals: int
    away_goals: int
    ht_home: int | None = None
    ht_away: int | None = None
    ft_home: int | None = None
    ft_away: int | None = None
    events: list[MatchEventData] = field(default_factory=list)
    stats: dict[str, dict[str, float | None]] | None = None  # {"home": {...}, "away": {...}}
    venue: str | None = None

    @property
    def period(self) -> int | None:
        if self.status == "1H":
            return 1
        if self.status in ("HT", "2H"):
            return 2
        return None


@dataclass
class OddsQuote:
    fixture_id: int
    source: str
    bookmaker: str | None
    market: str
    pick: str
    line: float | None
    odds: float
    suspended: bool
    updated: dt.datetime | None
    raw_market: str
    # match context reported by the odds feed itself (consistency checks)
    feed_elapsed: int | None = None
    feed_home_goals: int | None = None
    feed_away_goals: int | None = None
    feed_blocked: bool = False

    def key(self) -> tuple:
        return (self.market, self.pick, self.line)


@dataclass
class TeamForm:
    team_id: int
    matches: int
    goals_for: int
    goals_against: int
    over15: int
    over25: int
    over35: int
    btts: int
    home_matches: int
    home_gf: int
    home_ga: int
    away_matches: int
    away_gf: int
    away_ga: int
    last5_gf: int
    last5_ga: int
    last5_n: int
    results: list[str] = field(default_factory=list)  # W/D/L most recent first
