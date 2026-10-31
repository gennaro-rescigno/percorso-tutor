"""Parser tests. Payloads below are hand-written to follow the documented response shapes
(API-Football v3, The Odds API v4). They are test fixtures, never shown in the app."""
import datetime as dt

from app.providers.api_football import parse_fixture, parse_live_odds, parse_statistics
from app.providers.market_map import classify, parse_selection
from app.providers.the_odds_api import match_event, parse_event_odds, team_similarity


def fixture_payload(fid=1001, status="2H", elapsed=72, gh=2, ga=2, with_stats=True):
    item = {
        "fixture": {"id": fid, "date": "2026-10-31T19:45:00+00:00", "status": {"short": status, "elapsed": elapsed, "extra": None},
                    "venue": {"name": "Stadio Test"}},
        "league": {"id": 135, "name": "Serie A", "country": "Italy", "season": 2026, "round": "Regular Season - 10"},
        "teams": {"home": {"id": 1, "name": "Squadra A"}, "away": {"id": 2, "name": "Squadra B"}},
        "goals": {"home": gh, "away": ga},
        "score": {"halftime": {"home": 1, "away": 1}, "fulltime": {"home": None, "away": None}},
        "events": [
            {"time": {"elapsed": 12, "extra": None}, "team": {"id": 1}, "player": {"name": "P1"}, "type": "Goal", "detail": "Normal Goal"},
            {"time": {"elapsed": 60, "extra": None}, "team": {"id": 2}, "player": {"name": "P2"}, "type": "Card", "detail": "Red Card"},
        ],
    }
    if with_stats:
        item["statistics"] = [
            {"team": {"id": 1}, "statistics": [{"type": "Shots on Goal", "value": 6}, {"type": "Total Shots", "value": 14},
                                                {"type": "Corner Kicks", "value": 6}, {"type": "Ball Possession", "value": "58%"},
                                                {"type": "Red Cards", "value": None}, {"type": "expected_goals", "value": "1.84"}]},
            {"team": {"id": 2}, "statistics": [{"type": "Shots on Goal", "value": 4}, {"type": "Total Shots", "value": 9},
                                                {"type": "Corner Kicks", "value": None}, {"type": "Ball Possession", "value": "42%"},
                                                {"type": "Red Cards", "value": 1}, {"type": "expected_goals", "value": "0.95"}]},
        ]
    return item


def test_parse_fixture_and_stats():
    f = parse_fixture(fixture_payload())
    assert f.id == 1001 and f.period == 2 and f.home_goals == 2
    assert f.stats["home"]["sot"] == 6 and f.stats["home"]["possession"] == 58
    assert f.stats["away"]["corners"] == 0  # null count -> 0
    assert f.stats["home"]["red"] == 0
    assert f.stats["home"]["xg"] == 1.84
    assert f.events[1].side == "away" and f.events[1].detail == "Red Card"
    assert parse_statistics([], 1, 2) is None


def test_market_classification():
    assert classify("Over/Under Line") == "total_goals"
    assert classify("Fulltime Result") == "1x2"
    assert classify("Both Teams To Score") == "btts"
    assert classify("Which team will score the 3rd goal?") == "next_goal"
    assert classify("Asian Handicap") is None
    assert classify("Rest of Match") is None
    assert classify("Goal between 70:00 - 79:59") == "goal_window"
    assert classify("Correct Score") == "correct_score"
    assert parse_selection("total_goals", "Over", "2.5") == ("over", 2.5)
    assert parse_selection("total_goals", "Over 3.75", None) == ("over", 3.75)
    assert parse_selection("next_goal", "1", None, current_total=2, raw_name="Which team will score the 3rd goal?") == ("home", None)
    assert parse_selection("next_goal", "1", None, current_total=1, raw_name="Which team will score the 3rd goal?") is None
    assert parse_selection("goal_window", "Yes", None, raw_name="Goal between 70:00 - 79:59") == ("yes", 70.0)
    assert parse_selection("goal_window", "Yes", None, raw_name="Goal between 40:00 - 49:59") is None


def test_parse_live_odds():
    f = parse_fixture(fixture_payload())
    item = {
        "fixture": {"id": 1001, "status": {"long": "Second Half", "elapsed": 72}},
        "teams": {"home": {"id": 1, "goals": 2}, "away": {"id": 2, "goals": 2}},
        "status": {"stopped": False, "blocked": False, "finished": False},
        "update": "2026-10-31T21:20:00+00:00",
        "odds": [
            {"id": 36, "name": "Over/Under Line", "values": [
                {"value": "Over", "odd": "2.10", "handicap": "4.5", "main": True, "suspended": False},
                {"value": "Under", "odd": "1.70", "handicap": "4.5", "main": True, "suspended": False},
                {"value": "Over", "odd": "3.40", "handicap": "5.5", "main": False, "suspended": False}]},
            {"id": 59, "name": "Fulltime Result", "values": [
                {"value": "Home", "odd": "2.60", "handicap": None, "main": None, "suspended": False},
                {"value": "Draw", "odd": "2.20", "handicap": None, "main": None, "suspended": True},
                {"value": "Away", "odd": "4.50", "handicap": None, "main": None, "suspended": False}]},
            {"id": 99, "name": "Asian Handicap", "values": [{"value": "Home", "odd": "1.9", "handicap": "-0.5"}]},
        ],
    }
    quotes, unmapped = parse_live_odds(item, {1001: f})
    keys = {(q.market, q.pick, q.line): q for q in quotes}
    assert ("total_goals", "over", 4.5) in keys and ("total_goals", "over", 5.5) not in keys
    assert keys[("1x2", "draw", None)].suspended
    assert keys[("total_goals", "over", 4.5)].feed_home_goals == 2
    assert unmapped == ["Asian Handicap"]


def test_the_odds_api_matching():
    f = parse_fixture(fixture_payload())
    f.home_name, f.away_name = "AC Milan", "Inter"
    ev = {"id": "x", "commence_time": "2026-10-31T19:45:00Z", "home_team": "AC Milan", "away_team": "Inter Milan",
          "bookmakers": [{"key": "b1", "title": "Book1", "last_update": "2026-10-31T21:20:00Z",
                          "markets": [{"key": "totals", "last_update": "2026-10-31T21:20:00Z",
                                       "outcomes": [{"name": "Over", "price": 2.05, "point": 4.5},
                                                    {"name": "Under", "price": 1.75, "point": 4.5}]},
                                      {"key": "h2h", "outcomes": [{"name": "AC Milan", "price": 2.5},
                                                                  {"name": "Draw", "price": 2.3},
                                                                  {"name": "Inter Milan", "price": 4.0}]}]}]}
    assert team_similarity("Inter Milan", "Inter") == 1.0
    assert match_event(ev, [f]) is f
    q = parse_event_odds(ev, f)
    assert {(x.market, x.pick) for x in q} == {("total_goals", "over"), ("total_goals", "under"), ("1x2", "home"),
                                               ("1x2", "draw"), ("1x2", "away")}
    assert all(x.updated is None or x.updated.tzinfo == dt.timezone.utc for x in q)
