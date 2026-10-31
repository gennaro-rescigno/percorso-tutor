"""API-Football v3 (api-sports.io) client: live fixtures, statistics, events, in-play odds, team form.

Docs: https://www.api-football.com/documentation-v3
Auth header: ``x-apisports-key`` (direct) or ``x-rapidapi-key`` (RapidAPI).
Every call is logged in ``provider_log`` with HTTP status, result count and quota headers,
which is the audit trail proving the data shown in the dashboard really came from the API.
"""
from __future__ import annotations

import datetime as dt
import logging
import time
from typing import Any

import httpx

from ..config import Settings
from .base import LiveFixture, MatchEventData, OddsQuote, ProviderError, QuotaExceeded, TeamForm
from .market_map import classify, parse_selection

log = logging.getLogger("provider.api_football")

STAT_MAP = {
    "shots on goal": "sot",
    "shots off goal": "shots_off",
    "total shots": "shots",
    "blocked shots": "blocked",
    "shots insidebox": "shots_in_box",
    "shots outsidebox": "shots_out_box",
    "fouls": "fouls",
    "corner kicks": "corners",
    "offsides": "offsides",
    "ball possession": "possession",
    "yellow cards": "yellow",
    "red cards": "red",
    "goalkeeper saves": "saves",
    "total passes": "passes",
    "passes accurate": "passes_acc",
    "expected_goals": "xg",
}
# for these, API-Football returns null when the count is zero
NULL_IS_ZERO = {"sot", "shots_off", "shots", "blocked", "shots_in_box", "shots_out_box", "fouls", "corners",
                "offsides", "yellow", "red", "saves"}


def _parse_dt(s: str | None) -> dt.datetime | None:
    if not s:
        return None
    try:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def _num(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().rstrip("%")
    try:
        return float(s)
    except ValueError:
        return None


def parse_statistics(block: list[dict] | None, home_id: int | None, away_id: int | None) -> dict | None:
    """Normalise the ``statistics`` array. Returns None if the fixture has no statistics coverage."""
    if not block:
        return None
    out: dict[str, dict[str, float | None]] = {"home": {}, "away": {}}
    seen_any = False
    for entry in block:
        tid = (entry.get("team") or {}).get("id")
        side = "home" if tid == home_id else ("away" if tid == away_id else None)
        if side is None:
            continue
        for st in entry.get("statistics") or []:
            key = STAT_MAP.get(str(st.get("type", "")).strip().lower())
            if key is None:
                continue
            val = _num(st.get("value"))
            if val is not None:
                seen_any = True
            out[side][key] = val
    if not seen_any:
        return None
    for side in ("home", "away"):
        for key in NULL_IS_ZERO:
            if key in out[side] and out[side][key] is None:
                out[side][key] = 0.0
    return out


def parse_events(events: list[dict] | None, home_id: int | None, away_id: int | None) -> list[MatchEventData]:
    out = []
    for e in events or []:
        tid = (e.get("team") or {}).get("id")
        side = "home" if tid == home_id else ("away" if tid == away_id else None)
        tm = e.get("time") or {}
        out.append(MatchEventData(minute=tm.get("elapsed"), extra=tm.get("extra"), side=side,
                                  type=str(e.get("type") or ""), detail=e.get("detail"),
                                  player=(e.get("player") or {}).get("name")))
    return out


def parse_fixture(item: dict) -> LiveFixture:
    fx = item.get("fixture") or {}
    lg = item.get("league") or {}
    teams = item.get("teams") or {}
    goals = item.get("goals") or {}
    score = item.get("score") or {}
    st = fx.get("status") or {}
    home = teams.get("home") or {}
    away = teams.get("away") or {}
    ht = score.get("halftime") or {}
    ft = score.get("fulltime") or {}
    f = LiveFixture(
        id=int(fx["id"]), league_id=lg.get("id"), league_name=lg.get("name"), country=lg.get("country"),
        season=lg.get("season"), round=lg.get("round"), home_id=home.get("id"), home_name=home.get("name") or "?",
        away_id=away.get("id"), away_name=away.get("name") or "?", kickoff=_parse_dt(fx.get("date")),
        status=str(st.get("short") or ""), elapsed=st.get("elapsed"), extra=st.get("extra"),
        home_goals=int(goals.get("home") or 0), away_goals=int(goals.get("away") or 0),
        ht_home=ht.get("home"), ht_away=ht.get("away"), ft_home=ft.get("home"), ft_away=ft.get("away"),
        venue=(fx.get("venue") or {}).get("name"),
    )
    f.events = parse_events(item.get("events"), f.home_id, f.away_id)
    f.stats = parse_statistics(item.get("statistics"), f.home_id, f.away_id)
    return f


def parse_live_odds(item: dict, fixtures: dict[int, LiveFixture]) -> tuple[list[OddsQuote], list[str]]:
    """Normalise one element of the ``/odds/live`` response. Returns (quotes, unmapped bet names)."""
    fx = item.get("fixture") or {}
    fid = fx.get("id")
    if fid is None:
        return [], []
    fid = int(fid)
    lf = fixtures.get(fid)
    teams = item.get("teams") or {}
    status = item.get("status") or {}
    blocked = bool(status.get("blocked")) or bool(status.get("stopped")) or bool(status.get("finished"))
    upd = _parse_dt(item.get("update"))
    feed_elapsed = (fx.get("status") or {}).get("elapsed")
    fh = (teams.get("home") or {}).get("goals")
    fa = (teams.get("away") or {}).get("goals")
    cur_total = None if fh is None or fa is None else int(fh) + int(fa)
    quotes, unmapped = [], []
    for bet in item.get("odds") or []:
        name = str(bet.get("name") or "")
        market = classify(name)
        if market is None:
            unmapped.append(name)
            continue
        for v in bet.get("values") or []:
            odd = _num(v.get("odd"))
            if odd is None or odd <= 1.0:
                continue
            # duplicate lines: keep only the bookmaker's "main" line when the flag is present
            if v.get("main") is False:
                continue
            sel = parse_selection(market, v.get("value", ""), v.get("handicap"),
                                  lf.home_name if lf else "", lf.away_name if lf else "", cur_total, name)
            if sel is None:
                continue
            pick, line = sel
            quotes.append(OddsQuote(
                fixture_id=fid, source="api_football", bookmaker="api-football live", market=market, pick=pick,
                line=line, odds=odd, suspended=bool(v.get("suspended")) or blocked, updated=upd, raw_market=name,
                feed_elapsed=feed_elapsed, feed_home_goals=fh, feed_away_goals=fa, feed_blocked=blocked))
    return quotes, unmapped


class ApiFootball:
    name = "api_football"

    def __init__(self, settings: Settings, log_cb=None):
        self.s = settings
        self.log_cb = log_cb  # callable(provider, endpoint, status, results, latency_ms, quota, error)
        headers = {"Accept": "application/json"}
        if settings.api_football_mode == "rapidapi":
            headers["x-rapidapi-key"] = settings.api_football_key or ""
            headers["x-rapidapi-host"] = "api-football-v1.p.rapidapi.com"
        else:
            headers["x-apisports-key"] = settings.api_football_key or ""
        self.client = httpx.Client(base_url=settings.api_football_base_url, headers=headers, timeout=20.0)
        self.quota: dict[str, Any] = {}
        self.last_ok: dt.datetime | None = None
        self.last_error: str | None = None

    @property
    def configured(self) -> bool:
        return bool(self.s.api_football_key)

    def _get(self, path: str, params: dict | None = None) -> dict:
        if not self.configured:
            raise ProviderError("API_FOOTBALL_KEY non configurata")
        t0 = time.monotonic()
        endpoint = path + ("?" + "&".join(f"{k}={v}" for k, v in (params or {}).items()) if params else "")
        status = None
        try:
            r = self.client.get(path, params=params)
            status = r.status_code
            h = r.headers
            self.quota = {
                "requests_limit_day": h.get("x-ratelimit-requests-limit"),
                "requests_remaining_day": h.get("x-ratelimit-requests-remaining"),
                "limit_minute": h.get("x-ratelimit-limit"),
                "remaining_minute": h.get("x-ratelimit-remaining"),
            }
            if status == 429:
                raise QuotaExceeded("HTTP 429: limite di richieste raggiunto")
            r.raise_for_status()
            data = r.json()
            errors = data.get("errors")
            if errors:
                msg = str(errors)
                if any(k in msg.lower() for k in ("request limit", "ratelimit", "rate limit", "too many")):
                    raise QuotaExceeded(msg)
                raise ProviderError(msg)
            self.last_ok = dt.datetime.now(dt.timezone.utc)
            self.last_error = None
            if self.log_cb:
                self.log_cb(self.name, endpoint, status, data.get("results"), int((time.monotonic() - t0) * 1000),
                            self.quota, None)
            return data
        except (httpx.HTTPError, ProviderError, ValueError) as e:
            self.last_error = f"{type(e).__name__}: {e}"
            if self.log_cb:
                self.log_cb(self.name, endpoint, status, None, int((time.monotonic() - t0) * 1000), self.quota,
                            self.last_error)
            if isinstance(e, ProviderError):
                raise
            raise ProviderError(self.last_error) from e

    def _paged(self, path: str, params: dict | None = None, max_pages: int = 5) -> list[dict]:
        params = dict(params or {})
        data = self._get(path, params)
        out = list(data.get("response") or [])
        total = int((data.get("paging") or {}).get("total") or 1)
        page = 1
        while page < min(total, max_pages):
            page += 1
            params["page"] = page
            out.extend(self._get(path, params).get("response") or [])
        return out

    # ------------------------------------------------------------------ endpoints
    def account_status(self) -> dict:
        return self._get("/status").get("response") or {}

    def live_fixtures(self, leagues: set[int] | None = None) -> list[LiveFixture]:
        live = "-".join(str(x) for x in sorted(leagues)) if leagues else "all"
        return [parse_fixture(x) for x in self._get("/fixtures", {"live": live}).get("response") or []]

    def fixtures_by_ids(self, ids: list[int]) -> list[LiveFixture]:
        """Full fixture objects (events + statistics) — at most 20 ids per call."""
        out: list[LiveFixture] = []
        for i in range(0, len(ids), 20):
            chunk = ids[i:i + 20]
            data = self._get("/fixtures", {"ids": "-".join(str(x) for x in chunk)})
            out.extend(parse_fixture(x) for x in data.get("response") or [])
        return out

    def fixture_statistics(self, fixture_id: int, home_id: int | None, away_id: int | None) -> dict | None:
        data = self._get("/fixtures/statistics", {"fixture": fixture_id})
        return parse_statistics(data.get("response"), home_id, away_id)

    def live_odds(self, fixtures: dict[int, LiveFixture]) -> tuple[list[OddsQuote], dict[str, int]]:
        quotes: list[OddsQuote] = []
        unmapped: dict[str, int] = {}
        for item in self._paged("/odds/live"):
            q, um = parse_live_odds(item, fixtures)
            quotes.extend(q)
            for n in um:
                unmapped[n] = unmapped.get(n, 0) + 1
        return quotes, unmapped

    def team_form(self, team_id: int, last: int = 10) -> TeamForm | None:
        items = self._get("/fixtures", {"team": team_id, "last": last}).get("response") or []
        fin = [parse_fixture(x) for x in items]
        fin = [f for f in fin if f.status in ("FT", "AET", "PEN")]
        if not fin:
            return None
        fin.sort(key=lambda f: f.kickoff or dt.datetime.min.replace(tzinfo=dt.timezone.utc), reverse=True)
        tf = TeamForm(team_id=team_id, matches=0, goals_for=0, goals_against=0, over15=0, over25=0, over35=0, btts=0,
                      home_matches=0, home_gf=0, home_ga=0, away_matches=0, away_gf=0, away_ga=0,
                      last5_gf=0, last5_ga=0, last5_n=0)
        for i, f in enumerate(fin):
            # regulation-time score when available
            h = f.ft_home if f.ft_home is not None else f.home_goals
            a = f.ft_away if f.ft_away is not None else f.away_goals
            is_home = f.home_id == team_id
            gf, ga = (h, a) if is_home else (a, h)
            tf.matches += 1
            tf.goals_for += gf
            tf.goals_against += ga
            tf.over15 += int(h + a > 1.5)
            tf.over25 += int(h + a > 2.5)
            tf.over35 += int(h + a > 3.5)
            tf.btts += int(h > 0 and a > 0)
            if is_home:
                tf.home_matches += 1
                tf.home_gf += gf
                tf.home_ga += ga
            else:
                tf.away_matches += 1
                tf.away_gf += gf
                tf.away_ga += ga
            if i < 5:
                tf.last5_n += 1
                tf.last5_gf += gf
                tf.last5_ga += ga
            tf.results.append("W" if gf > ga else ("D" if gf == ga else "L"))
        return tf

    def fixture_final(self, fixture_id: int) -> LiveFixture | None:
        items = self._get("/fixtures", {"id": fixture_id}).get("response") or []
        return parse_fixture(items[0]) if items else None

    def close(self) -> None:
        self.client.close()
