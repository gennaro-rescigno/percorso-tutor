"""Download StatsBomb Open Data and extract a compact, minute-level event log.

Source: https://github.com/statsbomb/open-data (free, requires attribution to StatsBomb).
We keep only what the live model can also observe from a live data feed:
goals (incl. own goals and penalties), shots (on/off target, xG), corners,
yellow/red cards, and the actual end minute of each half (stoppage time).

Output: one JSON object per match in ``data/statsbomb_compact.jsonl`` (git-ignored).

Usage:
    python -m training.statsbomb_download            # default competition set
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx

BASE = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"

# (competition_id, season_id, label, role)
# role "train_pool": full league seasons (split temporally into train / temporal-validation)
# role "cross": completely different competitions/seasons, used only for out-of-sample validation
COMPETITIONS = [
    (2, 27, "Premier League 2015/16", "train_pool"),
    (11, 27, "La Liga 2015/16", "train_pool"),
    (12, 27, "Serie A 2015/16", "train_pool"),
    (7, 27, "Ligue 1 2015/16", "train_pool"),
    (1238, 108, "Indian Super League 2021/22", "cross"),
    (43, 3, "FIFA World Cup 2018", "cross"),
    (43, 106, "FIFA World Cup 2022", "cross"),
    (55, 43, "UEFA Euro 2020", "cross"),
    (55, 282, "UEFA Euro 2024", "cross"),
    (223, 282, "Copa America 2024", "cross"),
    (1267, 107, "African Cup of Nations 2023", "cross"),
    (9, 281, "Bundesliga 2023/24 (selected team)", "cross"),
    (9, 27, "Bundesliga 2015/16 (selected team)", "cross"),
]

RED_CARDS = {"Red Card", "Second Yellow"}
ON_TARGET = {"Goal", "Saved", "Saved to Post"}

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _card(ev: dict) -> str | None:
    for key in ("foul_committed", "bad_behaviour"):
        c = (ev.get(key) or {}).get("card")
        if c:
            return c.get("name")
    return None


def _get_json(client: httpx.Client, url: str, attempts: int = 6):
    delay = 2.0
    for i in range(attempts):
        try:
            r = client.get(url, timeout=60)
            r.raise_for_status()
            return r.json()
        except (httpx.TransportError, httpx.HTTPStatusError):
            if i == attempts - 1:
                raise
            time.sleep(delay)
            delay *= 2


def extract_match(client: httpx.Client, match: dict, label: str, role: str) -> dict:
    mid = match["match_id"]
    events = _get_json(client, f"{BASE}/events/{mid}.json")
    home_id = match["home_team"]["home_team_id"]
    away_id = match["away_team"]["away_team_id"]

    def side(team_id: int) -> int:
        return 0 if team_id == home_id else 1

    out: list[list] = []
    period_end: dict[int, float] = {}
    for ev in events:
        period = ev.get("period")
        if period not in (1, 2):
            continue  # regulation time only (markets settle on 90' + stoppage)
        t = ev["minute"] + ev.get("second", 0) / 60.0
        period_end[period] = max(period_end.get(period, 0.0), t)
        etype = ev["type"]["name"]
        team = ev.get("team", {}).get("id")
        if team is None:
            continue
        s = side(team)
        if etype == "Shot":
            shot = ev.get("shot", {})
            outcome = shot.get("outcome", {}).get("name")
            xg = float(shot.get("statsbomb_xg") or 0.0)
            on_t = 1 if outcome in ON_TARGET else 0
            out.append([period, round(t, 3), s, "shot", on_t, round(xg, 4)])
            if outcome == "Goal":
                out.append([period, round(t, 3), s, "goal", 1, round(xg, 4)])
        elif etype == "Own Goal For":
            out.append([period, round(t, 3), s, "goal", 0, 0.0])
        elif etype == "Pass" and (ev.get("pass", {}).get("type") or {}).get("name") == "Corner":
            out.append([period, round(t, 3), s, "corner", 0, 0.0])
        else:
            card = _card(ev)
            if card in RED_CARDS:
                out.append([period, round(t, 3), s, "red", 0, 0.0])
            elif card == "Yellow Card":
                out.append([period, round(t, 3), s, "yellow", 0, 0.0])

    goals_h = sum(1 for e in out if e[3] == "goal" and e[2] == 0)
    goals_a = sum(1 for e in out if e[3] == "goal" and e[2] == 1)
    return {
        "match_id": mid,
        "competition": label,
        "role": role,
        "date": match["match_date"],
        "home": match["home_team"]["home_team_name"],
        "away": match["away_team"]["away_team_name"],
        "home_id": home_id,
        "away_id": away_id,
        "official_home_score": match.get("home_score"),
        "official_away_score": match.get("away_score"),
        "reg_home_goals": goals_h,
        "reg_away_goals": goals_a,
        "period_end": {str(k): round(v, 3) for k, v in period_end.items()},
        "events": sorted(out, key=lambda e: (e[0], e[1])),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(DATA_DIR / "statsbomb_compact.jsonl"))
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with httpx.Client(follow_redirects=True) as client:
        jobs = []
        for comp, season, label, role in COMPETITIONS:
            for m in _get_json(client, f"{BASE}/matches/{comp}/{season}.json"):
                jobs.append((m, label, role))
        out = Path(args.out)
        have: set[int] = set()
        if out.exists():  # resumable
            for line in out.read_text().splitlines():
                try:
                    have.add(json.loads(line)["match_id"])
                except (ValueError, KeyError):
                    pass
        jobs = [j for j in jobs if j[0]["match_id"] not in have]
        print(f"{len(have)} already present, {len(jobs)} matches to download", flush=True)

        done = 0
        mismatches = 0
        with open(args.out, "a") as fh, ThreadPoolExecutor(args.workers) as pool:
            futs = [pool.submit(extract_match, client, m, label, role) for m, label, role in jobs]
            for f in as_completed(futs):
                rec = f.result()
                fh.write(json.dumps(rec, separators=(",", ":")) + "\n")
                done += 1
                if (rec["official_home_score"], rec["official_away_score"]) != (
                    rec["reg_home_goals"], rec["reg_away_goals"]):
                    mismatches += 1
                if done % 200 == 0:
                    print(f"  {done}/{len(jobs)}", flush=True)
        print(f"written {done} matches to {args.out}; "
              f"{mismatches} where regulation goals != official score (extra time or data issue)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
