"""Prove that LIVE data really arrives from the configured APIs.

Run from ``backend/``:   python -m scripts.verify_live
It performs real HTTP calls with your keys (from .env / environment), prints what each
source actually returns right now and saves a JSON report in data/verify_report_<UTC>.json.
Nothing is simulated: if a call fails, the error is printed and the check is marked FAIL.

API-Football cost: 1 (/status) + 1 (/fixtures?live=all) + 1 (/fixtures?ids=...) + 1 (/odds/live) = 4 requests.
The Odds API cost: /sports is free; one /odds call costs (#markets x #regions) credits.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from collections import Counter
from pathlib import Path

from app.config import get_settings
from app.providers.api_football import ApiFootball
from app.providers.base import ProviderError
from app.providers.the_odds_api import LEAGUE_TO_SPORT, TheOddsApi

OK, FAIL, SKIP = "OK  ", "FAIL", "SKIP"


def line(status: str, msg: str) -> None:
    print(f"[{status}] {msg}", flush=True)


def main() -> int:
    s = get_settings()
    now = dt.datetime.now(dt.timezone.utc)
    report: dict = {"run_at_utc": now.isoformat(), "checks": []}
    failures = 0

    def check(name: str, status: str, **data):
        nonlocal failures
        failures += status == FAIL
        report["checks"].append({"name": name, "status": status.strip(), **data})

    print(f"Verifica fonti dati LIVE — {now:%Y-%m-%d %H:%M:%S} UTC\n")
    af = ApiFootball(s)
    if not af.configured:
        line(FAIL, "API_FOOTBALL_KEY non impostata (file .env o variabile d'ambiente)")
        check("api_football.configured", FAIL)
    else:
        try:
            st = af.account_status()
            sub = (st.get("subscription") or {})
            req = (st.get("requests") or {})
            line(OK, f"API-Football account: piano={sub.get('plan')} attivo={sub.get('active')} "
                     f"scadenza={sub.get('end')} richieste oggi={req.get('current')}/{req.get('limit_day')}")
            check("api_football.status", OK, plan=sub.get("plan"), requests=req)
        except ProviderError as e:
            line(FAIL, f"/status: {e}")
            check("api_football.status", FAIL, error=str(e))

        live = []
        try:
            live = af.live_fixtures(s.leagues or None)
            line(OK if live else SKIP, f"/fixtures?live=all → {len(live)} partite live in questo momento")
            for f in live[:8]:
                print(f"       {f.elapsed or '-':>3}' {f.status:3} {f.home_name} {f.home_goals}-{f.away_goals} "
                      f"{f.away_name}  ({f.league_name}, {f.country})")
            check("api_football.live_fixtures", OK if live else SKIP, count=len(live),
                  sample=[{"id": f.id, "match": f"{f.home_name}-{f.away_name}", "minute": f.elapsed,
                           "score": f"{f.home_goals}-{f.away_goals}", "league": f.league_name} for f in live[:10]])
        except ProviderError as e:
            line(FAIL, f"/fixtures?live=all: {e}")
            check("api_football.live_fixtures", FAIL, error=str(e))

        if live:
            ids = [f.id for f in live if f.status in ("1H", "HT", "2H")][:20]
            try:
                det = af.fixtures_by_ids(ids)
                with_stats = [f for f in det if f.stats]
                with_xg = [f for f in with_stats if f.stats["home"].get("xg") is not None]
                with_events = [f for f in det if f.events]
                line(OK, f"/fixtures?ids=… → {len(det)} partite: statistiche live per {len(with_stats)}, "
                         f"xG live per {len(with_xg)}, eventi per {len(with_events)}")
                if with_stats:
                    f = with_stats[0]
                    print(f"       esempio {f.home_name}-{f.away_name}: {json.dumps(f.stats)}")
                keys = Counter(k for f in with_stats for k, v in f.stats["home"].items() if v is not None)
                check("api_football.statistics", OK, fixtures=len(det), with_stats=len(with_stats),
                      with_xg=len(with_xg), stat_keys=dict(keys))
            except ProviderError as e:
                line(FAIL, f"/fixtures?ids: {e}")
                check("api_football.statistics", FAIL, error=str(e))

            try:
                quotes, unmapped = af.live_odds({f.id: f for f in live})
                fixtures_with_odds = {q.fixture_id for q in quotes}
                markets = Counter(q.market for q in quotes)
                ages = [(now - q.updated).total_seconds() for q in quotes if q.updated]
                line(OK if quotes else SKIP,
                     f"/odds/live → {len(quotes)} quote normalizzate su {len(fixtures_with_odds)} partite; "
                     f"età mediana quota {sorted(ages)[len(ages) // 2]:.0f}s" if ages else
                     f"/odds/live → {len(quotes)} quote normalizzate")
                print(f"       mercati mappati: {dict(markets)}")
                print(f"       mercati NON mappati (esclusi): {dict(Counter(unmapped).most_common(15))}")
                ge175 = [q for q in quotes if q.odds >= 1.75 and not q.suspended]
                print(f"       quote >= 1.75 non sospese: {len(ge175)}")
                check("api_football.live_odds", OK if quotes else SKIP, quotes=len(quotes),
                      fixtures=len(fixtures_with_odds), markets=dict(markets), unmapped=dict(Counter(unmapped)))
            except ProviderError as e:
                line(FAIL, f"/odds/live: {e}")
                check("api_football.live_odds", FAIL, error=str(e))

    toa = TheOddsApi(s)
    if not toa.configured:
        line(SKIP, "THE_ODDS_API_KEY non impostata (fonte opzionale)")
        check("the_odds_api.configured", SKIP)
    else:
        try:
            sports = toa.active_sports()
            line(OK, f"The Odds API /sports → {len(sports)} competizioni di calcio attive")
            target = None
            for f in (live if af.configured else []):
                sk = LEAGUE_TO_SPORT.get(f.league_id or -1)
                if sk in sports:
                    target = sk
                    break
            if target:
                data = toa._get(f"/sports/{target}/odds", {"regions": s.the_odds_api_regions, "markets": "h2h,totals",
                                                           "oddsFormat": "decimal", "dateFormat": "iso"})
                started = [e for e in data if dt.datetime.fromisoformat(e["commence_time"].replace("Z", "+00:00")) < now]
                line(OK, f"The Odds API {target}: {len(data)} eventi, {len(started)} già iniziati (quote in-play) · "
                         f"crediti rimasti {toa.quota.get('requests_remaining')}")
                check("the_odds_api.odds", OK, sport=target, events=len(data), in_play=len(started), quota=toa.quota)
            else:
                line(SKIP, "Nessuna partita live di un campionato coperto da The Odds API: chiamata /odds non eseguita")
                check("the_odds_api.odds", SKIP)
        except ProviderError as e:
            line(FAIL, f"The Odds API: {e}")
            check("the_odds_api", FAIL, error=str(e))

    out = Path(__file__).resolve().parent.parent / "data" / f"verify_report_{now:%Y%m%dT%H%M%SZ}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1, default=str))
    print(f"\nReport salvato in {out}")
    print("ESITO:", "tutte le fonti configurate rispondono con dati reali" if failures == 0 else f"{failures} controlli FALLITI")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
