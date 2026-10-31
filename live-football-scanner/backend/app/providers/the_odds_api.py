"""The Odds API v4 client — optional second odds source (multi-bookmaker h2h / totals).

Docs: https://the-odds-api.com/liveapi/guides/v4/
Cost: each /odds call costs (#markets x #regions) credits; /sports is free.
The Odds API carries no live match state, so its quotes are only used when their
``last_update`` is fresh *and* newer than the last score change we observed.
"""
from __future__ import annotations

import datetime as dt
import logging
import re
import time
import unicodedata
from difflib import SequenceMatcher

import httpx

from ..config import Settings
from .base import LiveFixture, OddsQuote, ProviderError, QuotaExceeded

log = logging.getLogger("provider.the_odds_api")

# API-Football league id -> The Odds API sport key (best effort; verified against /v4/sports at runtime)
LEAGUE_TO_SPORT = {
    39: "soccer_epl", 40: "soccer_efl_champ", 41: "soccer_england_league1", 42: "soccer_england_league2",
    45: "soccer_fa_cup", 48: "soccer_england_efl_cup", 140: "soccer_spain_la_liga",
    141: "soccer_spain_segunda_division", 135: "soccer_italy_serie_a", 136: "soccer_italy_serie_b",
    78: "soccer_germany_bundesliga", 79: "soccer_germany_bundesliga2", 81: "soccer_germany_dfb_pokal",
    61: "soccer_france_ligue_one", 62: "soccer_france_ligue_two", 2: "soccer_uefa_champs_league",
    3: "soccer_uefa_europa_league", 848: "soccer_uefa_europa_conference_league",
    88: "soccer_netherlands_eredivisie", 94: "soccer_portugal_primeira_liga", 144: "soccer_belgium_first_div",
    203: "soccer_turkey_super_league", 179: "soccer_spl", 253: "soccer_usa_mls", 71: "soccer_brazil_campeonato",
    128: "soccer_argentina_primera_division", 262: "soccer_mexico_ligamx", 98: "soccer_japan_j_league",
    292: "soccer_korea_kleague1", 188: "soccer_australia_aleague", 113: "soccer_sweden_allsvenskan",
    103: "soccer_norway_eliteserien", 119: "soccer_denmark_superliga", 197: "soccer_greece_super_league",
    218: "soccer_austria_bundesliga", 207: "soccer_switzerland_superleague", 106: "soccer_poland_ekstraklasa",
    169: "soccer_china_superleague", 13: "soccer_conmebol_copa_libertadores", 1: "soccer_fifa_world_cup",
    4: "soccer_uefa_european_championship",
}

_STOP = {"fc", "cf", "afc", "sc", "ac", "as", "ss", "us", "cd", "ud", "rc", "club", "de", "calcio", "the", "fk",
         "sk", "if", "bk", "1", "real", "sporting"}


def norm_team(name: str) -> str:
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    toks = [t for t in s.split() if t not in _STOP]
    return " ".join(toks) or s.strip()


def team_similarity(a: str, b: str) -> float:
    na, nb = norm_team(a), norm_team(b)
    if not na or not nb:
        return 0.0
    if na == nb or na in nb or nb in na:
        return 1.0
    return SequenceMatcher(None, na, nb).ratio()


def match_event(ev: dict, fixtures: list[LiveFixture]) -> LiveFixture | None:
    try:
        ct = dt.datetime.fromisoformat(ev["commence_time"].replace("Z", "+00:00"))
    except (KeyError, ValueError):
        return None
    best, best_score = None, 0.0
    for f in fixtures:
        if f.kickoff is None or abs((f.kickoff - ct).total_seconds()) > 20 * 60:
            continue
        sh = team_similarity(ev.get("home_team", ""), f.home_name)
        sa = team_similarity(ev.get("away_team", ""), f.away_name)
        score = min(sh, sa)
        if score > best_score:
            best, best_score = f, score
    return best if best_score >= 0.72 else None


def parse_event_odds(ev: dict, fx: LiveFixture) -> list[OddsQuote]:
    out = []
    for bk in ev.get("bookmakers") or []:
        bname = bk.get("title") or bk.get("key")
        for mk in bk.get("markets") or []:
            key = mk.get("key")
            upd_s = mk.get("last_update") or bk.get("last_update")
            try:
                upd = dt.datetime.fromisoformat(upd_s.replace("Z", "+00:00")) if upd_s else None
            except ValueError:
                upd = None
            for o in mk.get("outcomes") or []:
                price = o.get("price")
                name = str(o.get("name", ""))
                if not isinstance(price, (int, float)) or price <= 1.0:
                    continue
                if key == "h2h":
                    if name == "Draw":
                        pick = "draw"
                    elif team_similarity(name, fx.home_name) >= 0.85 and name == ev.get("home_team"):
                        pick = "home"
                    elif name == ev.get("away_team"):
                        pick = "away"
                    else:
                        continue
                    out.append(OddsQuote(fx.id, "the_odds_api", bname, "1x2", pick, None, float(price), False, upd,
                                         "h2h"))
                elif key == "totals":
                    pt = o.get("point")
                    if pt is None or name.lower() not in ("over", "under"):
                        continue
                    out.append(OddsQuote(fx.id, "the_odds_api", bname, "total_goals", name.lower(), float(pt),
                                         float(price), False, upd, "totals"))
                elif key == "btts":
                    if name.lower() not in ("yes", "no"):
                        continue
                    out.append(OddsQuote(fx.id, "the_odds_api", bname, "btts", name.lower(), None, float(price),
                                         False, upd, "btts"))
                elif key == "draw_no_bet":
                    if name == ev.get("home_team"):
                        pick = "home"
                    elif name == ev.get("away_team"):
                        pick = "away"
                    else:
                        continue
                    out.append(OddsQuote(fx.id, "the_odds_api", bname, "dnb", pick, None, float(price), False, upd,
                                         "draw_no_bet"))
    return out


class TheOddsApi:
    name = "the_odds_api"

    def __init__(self, settings: Settings, log_cb=None):
        self.s = settings
        self.log_cb = log_cb
        self.client = httpx.Client(base_url=settings.the_odds_api_base_url, timeout=20.0)
        self.quota: dict = {}
        self.last_ok: dt.datetime | None = None
        self.last_error: str | None = None
        self._active_sports: set[str] | None = None
        self._active_fetched = 0.0
        self._last_poll = 0.0
        self._cache: list[OddsQuote] = []

    @property
    def configured(self) -> bool:
        return bool(self.s.the_odds_api_key)

    def _get(self, path: str, params: dict) -> list | dict:
        if not self.configured:
            raise ProviderError("THE_ODDS_API_KEY non configurata")
        t0 = time.monotonic()
        status = None
        p = {"apiKey": self.s.the_odds_api_key, **params}
        endpoint = path + "?" + "&".join(f"{k}={v}" for k, v in params.items())
        try:
            r = self.client.get(path, params=p)
            status = r.status_code
            self.quota = {"requests_remaining": r.headers.get("x-requests-remaining"),
                          "requests_used": r.headers.get("x-requests-used"),
                          "last_cost": r.headers.get("x-requests-last")}
            if status in (401, 429):
                raise QuotaExceeded(f"HTTP {status}: {r.text[:200]}")
            r.raise_for_status()
            data = r.json()
            self.last_ok = dt.datetime.now(dt.timezone.utc)
            self.last_error = None
            if self.log_cb:
                self.log_cb(self.name, endpoint, status, len(data) if isinstance(data, list) else None,
                            int((time.monotonic() - t0) * 1000), self.quota, None)
            return data
        except (httpx.HTTPError, ProviderError, ValueError) as e:
            self.last_error = f"{type(e).__name__}: {e}"
            if self.log_cb:
                self.log_cb(self.name, endpoint, status, None, int((time.monotonic() - t0) * 1000), self.quota,
                            self.last_error)
            if isinstance(e, ProviderError):
                raise
            raise ProviderError(self.last_error) from e

    def active_sports(self) -> set[str]:
        if self._active_sports is None or time.monotonic() - self._active_fetched > 3600:
            data = self._get("/sports", {})  # free endpoint
            self._active_sports = {d["key"] for d in data if d.get("active") and d["key"].startswith("soccer")}
            self._active_fetched = time.monotonic()
        return self._active_sports

    def live_odds(self, fixtures: list[LiveFixture]) -> list[OddsQuote]:
        """Poll at most every ``the_odds_api_min_interval_s`` seconds (cached in between)."""
        if time.monotonic() - self._last_poll < self.s.the_odds_api_min_interval_s:
            return self._cache
        self._last_poll = time.monotonic()
        active = self.active_sports()
        by_sport: dict[str, list[LiveFixture]] = {}
        for f in fixtures:
            sk = LEAGUE_TO_SPORT.get(f.league_id or -1)
            if sk and sk in active:
                by_sport.setdefault(sk, []).append(f)
        out: list[OddsQuote] = []
        for sk, fxs in by_sport.items():
            data = self._get(f"/sports/{sk}/odds", {"regions": self.s.the_odds_api_regions,
                                                    "markets": self.s.the_odds_api_markets,
                                                    "oddsFormat": "decimal", "dateFormat": "iso"})
            for ev in data:
                fx = match_event(ev, fxs)
                if fx is not None:
                    out.extend(parse_event_odds(ev, fx))
        self._cache = out
        return out

    def close(self) -> None:
        self.client.close()
