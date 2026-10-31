"""The live scanning loop.

Every ``POLL_INTERVAL_S`` (30-60 s):
  1. fetch all live fixtures (API-Football), then events + statistics for them;
  2. store a statistics snapshot per fixture (used for the 5/10/15-minute windows);
  3. fetch in-play odds (API-Football /odds/live, optionally The Odds API) and store changes;
  4. rebuild the model state, run the forecast, price every quoted selection;
  5. apply the mandatory filters, update the opportunity lifecycle (create / update / invalidate);
  6. settle finished fixtures (opportunities + prediction log) for backtesting;
  7. publish the new state to WebSocket subscribers.
Nothing is ever simulated: if a provider is not configured or fails, the state says so.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import logging
import threading
import time
from collections import Counter, defaultdict

import numpy as np
from sqlalchemy import select

from ..config import Settings
from ..db import Fixture, MatchEvent, OddsSnapshot, Opportunity, Prediction, ProviderLog, StatSnapshot, session, utcnow
from ..engine.explain import fixture_reasons, intensity, risk_factors
from ..engine.forecast import forecast
from ..engine.markets import MARKET_LABELS, Selection, outcome_probs
from ..engine.model import ModelBundle
from ..engine.value import (DataQuality, Evaluation, confidence_label, confidence_score, evaluate_selection,
                            fair_probabilities)
from ..providers.api_football import ApiFootball
from ..providers.base import FINISHED_STATUSES, LIVE_STATUSES, VOID_STATUSES, LiveFixture, OddsQuote, ProviderError, \
    QuotaExceeded
from ..providers.the_odds_api import TheOddsApi
from .backtest import settle_fixture
from .state_builder import Snap, build_origin, clock_of

log = logging.getLogger("scanner")

ANALYSABLE = {"1H", "HT", "2H"}
NOT_PROVIDED = {
    "dangerous_attacks": "Attacchi pericolosi",
    "attacks": "Attacchi",
    "big_chances": "Big chances",
    "xgot": "Expected Goals on Target (xGOT)",
}


def _aware(t: dt.datetime | None) -> dt.datetime | None:
    if t is None:
        return None
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)


class Scanner:
    def __init__(self, settings: Settings, bundle: ModelBundle | None):
        self.s = settings
        self.bundle = bundle
        self.af = ApiFootball(settings, log_cb=self._log_provider)
        self.toa = TheOddsApi(settings, log_cb=self._log_provider)
        self.lock = threading.Lock()
        self.public: dict = self._empty_state()
        self.analyses: dict[int, dict] = {}
        self.unmapped: Counter = Counter()
        self.subscribers: set[asyncio.Queue] = set()
        self.loop: asyncio.AbstractEventLoop | None = None
        self._last_pred_log: dict[int, float] = {}
        self._score_change_at: dict[int, dt.datetime] = {}
        self._last_score: dict[int, tuple[int, int]] = {}
        self._odds_cache: dict[tuple, tuple[float, bool]] = {}
        self._fail_streak: dict[tuple, int] = defaultdict(int)
        self._pending_final: dict[int, float] = {}
        self._paused_until: float = 0.0
        self.cycle_count = 0
        self.last_cycle_at: dt.datetime | None = None
        self.last_cycle_ms: int | None = None
        self.last_error: str | None = None
        self._stop = asyncio.Event()

    # ------------------------------------------------------------------ infra
    def _empty_state(self) -> dict:
        return {"updated_at": None, "n_live": 0, "n_opportunities": 0, "fixtures": [], "opportunities": [],
                "invalidated": [], "message": None}

    def _log_provider(self, provider, endpoint, status, results, latency_ms, quota, error):
        try:
            with session() as db:
                db.add(ProviderLog(provider=provider, endpoint=endpoint[:256], http_status=status, results=results,
                                   latency_ms=latency_ms, quota=quota, error=error))
                db.commit()
        except Exception:  # pragma: no cover - logging must never break the loop
            log.exception("provider log failed")

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=5)
        self.subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self.subscribers.discard(q)

    def _publish(self) -> None:
        if self.loop is None:
            return
        payload = self.snapshot()
        for q in list(self.subscribers):
            def put(q=q):
                if q.full():
                    try:
                        q.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                q.put_nowait(payload)
            self.loop.call_soon_threadsafe(put)

    def snapshot(self) -> dict:
        with self.lock:
            st = dict(self.public)
        st["providers"] = self.provider_status()
        return st

    def provider_status(self) -> dict:
        return {
            "api_football": {"configured": self.af.configured, "last_ok": self.af.last_ok.isoformat()
                             if self.af.last_ok else None, "last_error": self.af.last_error, "quota": self.af.quota},
            "the_odds_api": {"configured": self.toa.configured, "last_ok": self.toa.last_ok.isoformat()
                             if self.toa.last_ok else None, "last_error": self.toa.last_error, "quota": self.toa.quota},
            "scanner": {"cycles": self.cycle_count, "last_cycle_at": self.last_cycle_at.isoformat()
                        if self.last_cycle_at else None, "last_cycle_ms": self.last_cycle_ms,
                        "last_error": self.last_error, "poll_interval_s": self.s.poll_interval_s,
                        "paused": time.monotonic() < self._paused_until},
            "model": {"loaded": self.bundle is not None, "version": self.bundle.version if self.bundle else None},
            "unmapped_markets": self.unmapped.most_common(40),
        }

    async def run(self) -> None:
        self.loop = asyncio.get_running_loop()
        while not self._stop.is_set():
            t0 = time.monotonic()
            try:
                await asyncio.to_thread(self.cycle)
            except Exception as e:  # keep the loop alive
                log.exception("cycle failed")
                self.last_error = f"{type(e).__name__}: {e}"
            self._publish()
            wait = max(5.0, self.s.poll_interval_s - (time.monotonic() - t0))
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=wait)
            except asyncio.TimeoutError:
                pass

    def stop(self) -> None:
        self._stop.set()

    # ------------------------------------------------------------------ cycle
    def cycle(self) -> None:
        t0 = time.monotonic()
        now = utcnow()
        if not self.af.configured:
            with self.lock:
                self.public = self._empty_state()
                self.public["updated_at"] = now.isoformat()
                self.public["message"] = ("API_FOOTBALL_KEY non configurata: nessun dato live disponibile. "
                                          "Imposta la chiave nel file .env e riavvia.")
            return
        if self.bundle is None:
            self.last_error = "Modello non trovato: esegui `python -m training.train`"
        if time.monotonic() < self._paused_until:
            return
        try:
            live = self.af.live_fixtures(self.s.leagues or None)
        except QuotaExceeded as e:
            self._paused_until = time.monotonic() + 600
            self.last_error = f"Quota API-Football esaurita, pausa 10 minuti: {e}"
            return
        except ProviderError as e:
            # never keep showing stale opportunities when the source is unreachable
            self.last_error = f"API-Football non raggiungibile: {e}"
            with self.lock:
                self.public = self._empty_state()
                self.public["updated_at"] = now.isoformat()
                self.public["message"] = f"Impossibile scaricare le partite live: {e}"
            return
        live = [f for f in live if f.status in LIVE_STATUSES][: self.s.max_fixtures_per_cycle]
        details: dict[int, LiveFixture] = {}
        try:
            for f in self.af.fixtures_by_ids([f.id for f in live if f.status in ANALYSABLE]):
                details[f.id] = f
        except ProviderError as e:
            self.last_error = f"dettagli partite: {e}"
        fixtures: dict[int, LiveFixture] = {}
        for f in live:
            d = details.get(f.id)
            if d is not None:
                # status / score from the freshest call, stats and events from the details call
                d.status, d.elapsed, d.extra = f.status, f.elapsed, f.extra
                d.home_goals, d.away_goals = f.home_goals, f.away_goals
                fixtures[f.id] = d
            else:
                fixtures[f.id] = f

        self._store_fixtures(fixtures, now)

        quotes: list[OddsQuote] = []
        try:
            q, unmapped = self.af.live_odds(fixtures)
            quotes.extend(q)
            self.unmapped.update(unmapped)
        except ProviderError as e:
            self.last_error = f"quote live API-Football: {e}"
        if self.toa.configured and fixtures:
            try:
                quotes.extend(self.toa.live_odds([f for f in fixtures.values() if f.status in ANALYSABLE]))
            except ProviderError as e:
                self.last_error = f"The Odds API: {e}"
        self._store_odds(quotes, now)
        self._refresh_forms(fixtures)

        by_fix: dict[int, list[OddsQuote]] = defaultdict(list)
        for qt in quotes:
            by_fix[qt.fixture_id].append(qt)

        analyses: dict[int, dict] = {}
        passing: dict[tuple, tuple[Evaluation, dict]] = {}
        evaluated_keys: dict[tuple, Evaluation] = {}
        for fid, f in fixtures.items():
            try:
                a = self._analyse(f, by_fix.get(fid, []), now)
            except Exception as e:
                log.exception("analysis failed for %s", fid)
                a = {"fixture": self._fixture_summary(f), "error": f"{type(e).__name__}: {e}", "evaluations": []}
            analyses[fid] = a
            for ev in a.get("_evals", []):
                k = (fid, ev.sel.market, ev.sel.pick, ev.sel.line)
                prev = evaluated_keys.get(k)
                if prev is None or ev.odds > prev.odds:
                    evaluated_keys[k] = ev
                if ev.passed:
                    cur = passing.get(k)
                    if cur is None or ev.rank_score > cur[0].rank_score:
                        passing[k] = (ev, a)

        self._update_opportunities(passing, evaluated_keys, fixtures, now)
        self._log_predictions(analyses, now)
        self._settle_finished(set(fixtures))

        # public state
        opps = self._active_opportunities()
        inval = self._recent_invalidated()
        for a in analyses.values():
            a.pop("_evals", None)
            a.pop("_state", None)
        summaries = []
        for fid, f in fixtures.items():
            a = analyses.get(fid, {})
            s = self._fixture_summary(f)
            s["n_opportunities"] = sum(1 for o in opps if o["fixture_id"] == fid)
            s["n_quotes"] = len(by_fix.get(fid, []))
            s["has_stats"] = f.stats is not None
            s["model"] = a.get("model", {}).get("goal_model")
            s["p_more_goals"] = a.get("model", {}).get("p_more_goals")
            s["analysable"] = a.get("analysable", False)
            s["not_analysable_reason"] = a.get("not_analysable_reason")
            summaries.append(s)
        summaries.sort(key=lambda s: (-(s["n_opportunities"]), s["league_name"] or "", s["id"]))
        with self.lock:
            self.analyses = analyses
            self.public = {
                "updated_at": now.isoformat(), "n_live": len(fixtures), "n_opportunities": len(opps),
                "fixtures": summaries, "opportunities": opps, "invalidated": inval,
                "message": None if fixtures else "Nessuna partita live in questo momento secondo API-Football.",
                "filters": {"min_odds": self.s.min_odds, "min_ev": self.s.min_ev, "min_edge": self.s.min_edge},
            }
        self.cycle_count += 1
        self.last_cycle_at = now
        self.last_cycle_ms = int((time.monotonic() - t0) * 1000)

    # ------------------------------------------------------------------ storage
    def _store_fixtures(self, fixtures: dict[int, LiveFixture], now: dt.datetime) -> None:
        with session() as db:
            live_ids = set(fixtures)
            for f in fixtures.values():
                row = db.get(Fixture, f.id)
                if row is None:
                    row = Fixture(id=f.id, home_name=f.home_name, away_name=f.away_name)
                    db.add(row)
                for k in ("league_id", "league_name", "country", "season", "round", "home_id", "home_name",
                          "away_id", "away_name", "kickoff", "status", "elapsed", "extra", "home_goals",
                          "away_goals", "ht_home", "ht_away"):
                    setattr(row, k, getattr(f, k))
                row.is_live = True
                row.last_seen_live = now
                score = (f.home_goals, f.away_goals)
                if self._last_score.get(f.id) not in (None, score):
                    self._score_change_at[f.id] = now
                self._last_score[f.id] = score
                db.add(StatSnapshot(fixture_id=f.id, ts=now, status=f.status, elapsed=f.elapsed, extra=f.extra,
                                    home_goals=f.home_goals, away_goals=f.away_goals,
                                    stats=f.stats or {}))
                if f.events:
                    existing = set(db.scalars(select(MatchEvent.signature).where(MatchEvent.fixture_id == f.id)))
                    for e in f.events:
                        sig = e.signature()[:256]
                        if sig not in existing:
                            db.add(MatchEvent(fixture_id=f.id, minute=e.minute, extra=e.extra, side=e.side,
                                              type=e.type[:32], detail=(e.detail or "")[:64],
                                              player=(e.player or "")[:128], signature=sig))
                            existing.add(sig)
            # fixtures that dropped out of the live list
            for row in db.scalars(select(Fixture).where(Fixture.is_live.is_(True))):
                if row.id not in live_ids:
                    row.is_live = False
                    self._pending_final.setdefault(row.id, 0.0)
            db.commit()

    def _store_odds(self, quotes: list[OddsQuote], now: dt.datetime) -> None:
        if not quotes:
            return
        with session() as db:
            known = {r for (r,) in db.execute(select(Fixture.id)).all()}
            for q in quotes:
                if q.fixture_id not in known:
                    continue
                k = (q.fixture_id, q.source, q.bookmaker, q.market, q.pick, q.line)
                if self._odds_cache.get(k) == (q.odds, q.suspended):
                    continue
                self._odds_cache[k] = (q.odds, q.suspended)
                db.add(OddsSnapshot(fixture_id=q.fixture_id, ts=now, source=q.source, bookmaker=q.bookmaker,
                                    market=q.market, pick=q.pick, line=q.line, odds=q.odds, suspended=q.suspended,
                                    provider_update=q.updated, raw_market=q.raw_market[:128]))
            db.commit()

    def _refresh_forms(self, fixtures: dict[int, LiveFixture]) -> None:
        """Fetch team form (last 10 matches) for a few fixtures per cycle to respect quotas."""
        budget = 4
        try:
            rem = int(self.af.quota.get("requests_remaining_day") or 10 ** 6)
        except (TypeError, ValueError):
            rem = 10 ** 6
        if rem < 150:
            return
        now = utcnow()
        with session() as db:
            for f in fixtures.values():
                if budget <= 0:
                    break
                row = db.get(Fixture, f.id)
                fetched = _aware(row.form_fetched_at) if row else None
                if row is None or (fetched and (now - fetched).total_seconds() < self.s.form_cache_hours * 3600):
                    continue
                form = {}
                for side, tid in (("home", f.home_id), ("away", f.away_id)):
                    if tid is None:
                        continue
                    try:
                        tf = self.af.team_form(tid, 10)
                        budget -= 1
                    except ProviderError:
                        tf = None
                    form[side] = tf.__dict__ if tf else None
                row.form = form
                row.form_fetched_at = now
            db.commit()

    # ------------------------------------------------------------------ analysis
    def _fixture_summary(self, f: LiveFixture) -> dict:
        return {"id": f.id, "league_id": f.league_id, "league_name": f.league_name, "country": f.country,
                "round": f.round, "home": f.home_name, "away": f.away_name, "status": f.status, "elapsed": f.elapsed,
                "extra": f.extra, "home_goals": f.home_goals, "away_goals": f.away_goals,
                "kickoff": f.kickoff.isoformat() if f.kickoff else None}

    def _history(self, fid: int) -> list[Snap]:
        with session() as db:
            rows = db.scalars(select(StatSnapshot).where(StatSnapshot.fixture_id == fid)
                              .order_by(StatSnapshot.ts.desc()).limit(120)).all()
        return [Snap(r.status, r.elapsed, r.extra, r.home_goals, r.away_goals, r.stats or None) for r in rows[::-1]]

    def _analyse(self, f: LiveFixture, quotes: list[OddsQuote], now: dt.datetime) -> dict:
        out: dict = {"fixture": self._fixture_summary(f), "analysable": False, "evaluations": [], "_evals": []}
        st = f.stats
        avail = {}
        for k in ("shots", "sot", "shots_off", "blocked", "corners", "possession", "fouls", "yellow", "red", "saves",
                  "xg"):
            avail[k] = st is not None and st["home"].get(k) is not None and st["away"].get(k) is not None
        out["stats"] = st
        out["availability"] = {
            "provided": [k for k, v in avail.items() if v],
            "missing": [k for k, v in avail.items() if not v] + list(NOT_PROVIDED),
            "not_provided_by_source": NOT_PROVIDED,
        }
        out["events"] = [e.__dict__ for e in f.events][-40:]
        with session() as db:
            row = db.get(Fixture, f.id)
            form = (row.form or {}) if row else {}
        out["form"] = form
        if f.status not in ANALYSABLE:
            out["not_analysable_reason"] = f"Stato partita {f.status}: analisi sospesa"
            return out
        if self.bundle is None:
            out["not_analysable_reason"] = "Modello non disponibile"
            return out
        cur = Snap(f.status, f.elapsed, f.extra, f.home_goals, f.away_goals, st)
        history = self._history(f.id)
        reds_ev = {"home": 0, "away": 0}
        last_red = None
        for e in f.events:
            if e.type.lower() == "card" and (e.detail or "").lower() in ("red card", "second yellow card"):
                if e.side in reds_ev:
                    reds_ev[e.side] += 1
                    last_red = float((e.minute or 0) + (e.extra or 0))
        state, windows = build_origin(cur, history, form.get("home"), form.get("away"), self.bundle.mu_goals,
                                      self.bundle.prior_pseudo_matches, reds_ev["home"], reds_ev["away"])
        has_stats = avail["shots"] and avail["sot"]
        has_xg = avail["xg"]
        goal_model = "goals_xg" if (has_stats and has_xg) else ("goals_stats" if has_stats else "goals_context")
        window_cov = windows.get("coverage_min") if windows.get("w10") is not None else None
        dq = DataQuality(has_stats=has_stats, has_corners=avail["corners"], has_xg=has_xg,
                         window_minutes=window_cov, prior_home_n=state.home_prior.n_matches,
                         prior_away_n=state.away_prior.n_matches, goal_model=goal_model)
        window_starts = sorted({q.line for q in quotes if q.market == "goal_window" and q.line is not None})
        fc = forecast(self.bundle, state, goal_model=goal_model, n_draws=self.s.n_param_draws,
                      seed=f.id % 10_000, with_corners=avail["corners"], windows=window_starts)
        minutes_left = float(np.sum(fc.grid.weight)) if fc.grid is not None else 0.0
        out["analysable"] = True
        out["_state"] = state
        out["windows"] = windows
        out["intensity"] = intensity(state)
        fair_odds = lambda p: (1.0 / p) if p > 1e-6 else None  # noqa: E731
        p_more = 1.0 - float(fc.p_next_none.mean())
        core = {
            "goal_model": goal_model, "minutes_left_est": minutes_left,
            "exp_goals_home": float(fc.exp_goals_home.mean()), "exp_goals_away": float(fc.exp_goals_away.mean()),
            "p_more_goals": p_more, "p_next_home": float(fc.p_next_home.mean()),
            "p_next_away": float(fc.p_next_away.mean()), "p_next_none": float(fc.p_next_none.mean()),
            "p_goal_next10": float(fc.p_goal_next10.mean()), "fair_odds_goal_next10": fair_odds(float(fc.p_goal_next10.mean())),
            "corners_expected_rest": float((fc.corners_home + fc.corners_away).mean()) if fc.corners_home is not None
            else None,
        }
        # model probabilities for the main markets regardless of odds availability (fair odds shown)
        main = []
        tot = f.home_goals + f.away_goals
        for sel in [Selection("total_goals", "over", tot + 0.5), Selection("total_goals", "over", tot + 1.5),
                    Selection("btts", "yes"), Selection("1x2", "home"), Selection("1x2", "draw"),
                    Selection("1x2", "away"), Selection("team_goals_home", "over", f.home_goals + 0.5),
                    Selection("team_goals_away", "over", f.away_goals + 0.5)]:
            op = outcome_probs(fc, sel, state.period, (f.ht_home or 0, f.ht_away or 0))
            if op is None:
                continue
            p = float(op.p_effective().mean())
            main.append({"key": sel.key(), "label": sel.label(f.home_name, f.away_name), "p_model": p,
                         "p_low": float(np.quantile(op.p_effective(), 0.1)),
                         "p_high": float(np.quantile(op.p_effective(), 0.9)), "fair_odds": fair_odds(p)})
        core["main_markets"] = main
        out["model"] = core
        if not quotes:
            out["note"] = "Nessuna quota live disponibile per questa partita dalle fonti configurate."
            return out
        # group for de-vigging
        groups: dict[tuple, dict[str, float]] = defaultdict(dict)
        for q in quotes:
            if not q.suspended:
                groups[(q.source, q.bookmaker, q.market, q.line)][q.pick] = q.odds
        margins = self.bundle.validation.get("family_margins", {})
        evals: list[Evaluation] = []
        ht = (f.ht_home or 0, f.ht_away or 0) if f.ht_home is not None else None
        last_change = self._score_change_at.get(f.id)
        for q in quotes:
            sel = Selection(q.market, q.pick, q.line)
            op = outcome_probs(fc, sel, state.period, ht)
            if op is None:
                continue
            fair = fair_probabilities(groups.get((q.source, q.bookmaker, q.market, q.line), {}), q.market)
            p_fair = fair[0].get(q.pick) if fair else None
            ev = evaluate_selection(sel, sel.label(f.home_name, f.away_name), op, q.odds, q.source, q.bookmaker,
                                    margins, self.s.conservative_quantile, p_fair, fair[1] if fair else None)
            upd = _aware(q.updated)
            ev.odds_age_s = (now - upd).total_seconds() if upd else None
            fails = []
            if q.suspended:
                fails.append("Mercato sospeso / bloccato dal bookmaker")
            if q.odds < self.s.min_odds:
                fails.append(f"Quota {q.odds:.2f} inferiore alla soglia {self.s.min_odds:.2f}")
            if ev.odds_age_s is None:
                fails.append("Timestamp della quota assente: freschezza non verificabile")
            elif ev.odds_age_s > self.s.odds_max_age_s:
                fails.append(f"Quota non aggiornata da {ev.odds_age_s:.0f}s (max {self.s.odds_max_age_s}s)")
            if q.feed_home_goals is not None and (q.feed_home_goals, q.feed_away_goals) != (f.home_goals, f.away_goals):
                fails.append("Risultato nel feed quote diverso da quello del feed partita (evento in corso)")
            if q.source == "the_odds_api" and last_change is not None and (upd is None or upd < last_change + dt.timedelta(seconds=30)):
                fails.append("Quota precedente all'ultimo gol osservato")
            if not has_stats and q.market != "total_corners":
                fails.append("Statistiche live (tiri/tiri in porta) non disponibili: dati insufficienti")
            if q.market == "total_corners" and not avail["corners"]:
                fails.append("Corner live non disponibili")
            if f.status == "1H" and (f.elapsed or 0) < self.s.min_minute:
                fails.append(f"Prima del {self.s.min_minute}' l'informazione in-play è insufficiente")
            if f.status == "2H" and (f.elapsed or 0) > self.s.max_minute_h2:
                fails.append(f"Oltre l'{self.s.max_minute_h2}': quote instabili / frequenti sospensioni")
            if ev.p_market_fair is not None:
                gap = ev.p_model / max(1e-9, 1 - ev.p_push) - ev.p_market_fair
                if abs(gap) > self.s.max_model_market_gap:
                    fails.append(f"Anomalia: modello e mercato differiscono di {100 * gap:+.0f} pp "
                                 "(probabile informazione mancante nei dati)")
            if ev.p_high - ev.p_low > 0.25:
                fails.append("Incertezza del modello troppo ampia")
            if ev.ev_cons < self.s.min_ev:
                fails.append(f"EV prudenziale {ev.ev_cons:+.1%} sotto la soglia {self.s.min_ev:+.1%}")
            if ev.edge < self.s.min_edge:
                fails.append(f"Vantaggio prudenziale {100 * ev.edge:+.1f} pp sotto la soglia {100 * self.s.min_edge:.1f} pp")
            ev.fail_reasons = fails
            ev.passed = not fails
            ev.confidence = confidence_score(ev, dq, minutes_left, q.feed_home_goals is not None)
            ev.confidence_label = confidence_label(ev.confidence)
            ev.rank_score = ev.ev_cons * (0.5 + ev.confidence / 200.0)
            if ev.passed:
                ev.reasons = fixture_reasons(q.market, q.pick, state, fc, f.home_name, f.away_name, ev)
                ev.risks = risk_factors(ev, state, dq, minutes_left, f.round, q.feed_home_goals is not None, last_red)
            evals.append(ev)
        evals.sort(key=lambda e: (not e.passed, -e.ev_cons))
        out["_evals"] = evals
        out["evaluations"] = [e.to_dict() for e in evals[:80]]
        out["data_quality"] = dq.__dict__
        return out

    # ------------------------------------------------------------------ opportunities
    def _opp_payload(self, ev: Evaluation, a: dict) -> dict:
        fx = a["fixture"]
        return {**ev.to_dict(), "fixture": fx, "model": {k: a["model"][k] for k in
                ("goal_model", "exp_goals_home", "exp_goals_away", "p_more_goals", "minutes_left_est")},
                "data_quality": a.get("data_quality")}

    def _update_opportunities(self, passing: dict, evaluated: dict, fixtures: dict[int, LiveFixture],
                              now: dt.datetime) -> None:
        with session() as db:
            active = db.scalars(select(Opportunity).where(Opportunity.status == "active")).all()
            active_keys = {}
            for o in active:
                active_keys[(o.fixture_id, o.market, o.pick, o.line)] = o
            for k, (ev, a) in passing.items():
                fx = a["fixture"]
                score = f"{fx['home_goals']}-{fx['away_goals']}"
                o = active_keys.get(k)
                self._fail_streak.pop(k, None)
                if o is not None and o.score_at_detection != score:
                    o.status = "invalidated"
                    o.invalidated_at = now
                    o.invalidation_reason = f"Risultato cambiato ({o.score_at_detection} → {score})"
                    o.closing_odds = o.last_odds
                    o = None
                if o is None:
                    o = Opportunity(fixture_id=k[0], market=k[1], pick=k[2], line=k[3], label=ev.label,
                                    status="active", first_seen=now, last_seen=now,
                                    minute_at_detection=fx["elapsed"], period_at_detection=1 if fx["status"] == "1H" else 2,
                                    score_at_detection=score, odds_at_detection=ev.odds, bookmaker=ev.bookmaker,
                                    p_model_at_detection=ev.p_model, p_cons_at_detection=ev.p_cons,
                                    ev_cons_at_detection=ev.ev_cons, confidence_at_detection=ev.confidence_label)
                    db.add(o)
                o.last_seen = now
                o.last_odds = ev.odds
                o.best_odds = max(o.best_odds or 0, ev.odds)
                o.last_p_model = ev.p_model
                o.last_ev_cons = ev.ev_cons
                o.last_payload = self._opp_payload(ev, a)
            for k, o in active_keys.items():
                if k in passing:
                    continue
                fid = k[0]
                ev = evaluated.get(k)
                f = fixtures.get(fid)
                hard = None
                if f is None or f.status not in ANALYSABLE:
                    hard = "Partita terminata o non più analizzabile" if f is None else f"Stato partita {f.status}"
                elif f"{f.home_goals}-{f.away_goals}" != o.score_at_detection:
                    hard = f"Risultato cambiato ({o.score_at_detection} → {f.home_goals}-{f.away_goals})"
                elif ev is None:
                    hard = "Quota non più disponibile nel feed"
                elif any(("inferiore alla soglia" in r) or ("sospeso" in r) or ("non aggiornata" in r)
                         for r in ev.fail_reasons):
                    hard = "; ".join(ev.fail_reasons)
                if hard is None:
                    self._fail_streak[k] += 1
                    if self._fail_streak[k] < 2:  # hysteresis on soft failures (EV/edge fluctuations)
                        continue
                    hard = "; ".join(ev.fail_reasons) if ev else "Criteri non più soddisfatti"
                self._fail_streak.pop(k, None)
                o.status = "invalidated"
                o.invalidated_at = now
                o.invalidation_reason = hard
                o.closing_odds = ev.odds if ev is not None else o.last_odds
            db.commit()

    def _active_opportunities(self) -> list[dict]:
        with session() as db:
            rows = db.scalars(select(Opportunity).where(Opportunity.status == "active")).all()
        out = []
        for o in rows:
            p = dict(o.last_payload or {})
            p.update({"id": o.id, "fixture_id": o.fixture_id, "first_seen": _aware(o.first_seen).isoformat(),
                      "last_seen": _aware(o.last_seen).isoformat(), "odds_at_detection": o.odds_at_detection,
                      "minute_at_detection": o.minute_at_detection})
            out.append(p)
        out.sort(key=lambda p: -p.get("rank_score", 0))
        return out

    def _recent_invalidated(self, limit: int = 30) -> list[dict]:
        with session() as db:
            rows = db.scalars(select(Opportunity).where(Opportunity.status != "active")
                              .order_by(Opportunity.invalidated_at.desc()).limit(limit)).all()
            fx = {f.id: f for f in db.scalars(select(Fixture).where(Fixture.id.in_({o.fixture_id for o in rows})))}
        out = []
        for o in rows:
            f = fx.get(o.fixture_id)
            out.append({"id": o.id, "fixture_id": o.fixture_id, "match": f"{f.home_name} - {f.away_name}" if f else "?",
                        "label": o.label, "odds_at_detection": o.odds_at_detection, "closing_odds": o.closing_odds,
                        "invalidated_at": _aware(o.invalidated_at).isoformat() if o.invalidated_at else None,
                        "reason": o.invalidation_reason, "status": o.status, "result": o.result})
        return out

    # ------------------------------------------------------------------ prediction log & settlement
    def _log_predictions(self, analyses: dict[int, dict], now: dt.datetime) -> None:
        t = time.monotonic()
        rows = []
        for fid, a in analyses.items():
            evs: list[Evaluation] = a.get("_evals") or []
            st = a.get("_state")
            if not evs or st is None:
                continue
            if t - self._last_pred_log.get(fid, -1e9) < self.s.prediction_log_every_s and not any(e.passed for e in evs):
                continue
            self._last_pred_log[fid] = t
            fx = a["fixture"]
            seen = set()
            for e in evs:
                k = e.sel.key()
                if k in seen:
                    continue
                seen.add(k)
                rows.append(Prediction(fixture_id=fid, ts=now, elapsed=fx["elapsed"], period=st.period,
                                       home_goals=fx["home_goals"], away_goals=fx["away_goals"], market=e.sel.market,
                                       pick=e.sel.pick, line=e.sel.line, odds=e.odds, p_model=e.p_model,
                                       p_low=e.p_low, p_high=e.p_high, p_cons=e.p_cons, p_market_fair=e.p_market_fair,
                                       ev=e.ev, ev_cons=e.ev_cons, model_version=self.bundle.version,
                                       goal_model=a["model"]["goal_model"], passed=e.passed,
                                       context={"clock": st.clock}))
        if rows:
            with session() as db:
                db.add_all(rows)
                db.commit()

    def _settle_finished(self, live_ids: set[int]) -> None:
        now_m = time.monotonic()
        for fid, last_try in list(self._pending_final.items()):
            if fid in live_ids:
                self._pending_final.pop(fid, None)
                continue
            if now_m - last_try < 300:
                continue
            self._pending_final[fid] = now_m
            try:
                f = self.af.fixture_final(fid)
            except ProviderError:
                continue
            if f is None:
                continue
            if f.status in FINISHED_STATUSES or f.status in VOID_STATUSES:
                with session() as db:
                    row = db.get(Fixture, fid)
                    if row is None:
                        continue
                    row.status = f.status
                    row.finished = True
                    row.is_live = False
                    row.ht_home, row.ht_away = f.ht_home, f.ht_away
                    row.ft_home = f.ft_home if f.ft_home is not None else f.home_goals
                    row.ft_away = f.ft_away if f.ft_away is not None else f.away_goals
                    if f.stats:
                        row.corners_home_final = f.stats["home"].get("corners")
                        row.corners_away_final = f.stats["away"].get("corners")
                    db.commit()
                    settle_fixture(db, row, void=f.status in VOID_STATUSES)
                self._pending_final.pop(fid, None)

    # ------------------------------------------------------------------ queries
    def fixture_detail(self, fid: int) -> dict | None:
        with self.lock:
            a = self.analyses.get(fid)
        if a is None:
            return None
        hist = self._history(fid)
        a = dict(a)
        a["timeline"] = [{"status": h.status, "elapsed": h.elapsed, "extra": h.extra, "home_goals": h.home_goals,
                          "away_goals": h.away_goals,
                          "home": {k: (h.stats or {}).get("home", {}).get(k) for k in ("shots", "sot", "corners", "xg")},
                          "away": {k: (h.stats or {}).get("away", {}).get(k) for k in ("shots", "sot", "corners", "xg")}}
                         for h in hist if h.stats]
        a["market_labels"] = MARKET_LABELS
        return a

    def clock(self, f: LiveFixture) -> float | None:
        return clock_of(f.status, f.elapsed, f.extra)[1]
