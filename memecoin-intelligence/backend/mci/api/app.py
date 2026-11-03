"""Dashboard REST API (FastAPI). Also serves the built React frontend."""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from dataclasses import fields
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import desc, select

from mci.analytics import performance as perf
from mci.api.auth import check_login, issue_token, require_user
from mci.config import get_settings
from mci.database import repo
from mci.database.models import BacktestRun, Event, Position, SignalRow, Token, TokenSnapshotRow
from mci.database.session import init_engine, session_scope
from mci.domain import to_utc, utcnow
from mci.risk_management.exits import EXIT_POLICIES
from mci.risk_management.profiles import PROFILES, get_profile
from mci.strategies.library import STRATEGIES

log = logging.getLogger(__name__)


class LoginBody(BaseModel):
    username: str
    password: str


class BacktestBody(BaseModel):
    name: str = "backtest"
    strategies: list[str] = Field(default_factory=lambda: ["B"])
    profile: str = "moderate"
    exit_policy: str = "ladder_trailing"
    capital_sol: float = 2.0
    start: str | None = None
    end: str | None = None
    timeframe: str = "1m"
    dataset: str = "recorded"  # recorded | imported | synthetic
    strategy_params: dict[str, dict[str, Any]] = Field(default_factory=dict)
    exit_overrides: dict[str, Any] = Field(default_factory=dict)
    profile_overrides: dict[str, Any] = Field(default_factory=dict)


def _iso(d: datetime | None) -> str | None:
    return to_utc(d).isoformat() if d else None


def _worker_status(s) -> dict[str, Any]:
    st = repo.get_state(s, "worker_status") or {}
    hb = st.get("heartbeat")
    age = (utcnow() - datetime.fromisoformat(hb)).total_seconds() if hb else None
    st["heartbeat_age_s"] = age
    st["worker_alive"] = age is not None and age < 600
    return st


def _mode(s) -> str:
    return (repo.get_state(s, "worker_status") or {}).get("mode") or "paper"


def _run_backtest_job(run_id: int, body: BacktestBody) -> None:
    from mci.backtesting.datasource import dataset_from_db
    from mci.backtesting.engine import BacktestConfig, run_backtest
    from mci.backtesting.report import render_report
    from mci.backtesting.synthetic import scenario_dataset

    try:
        with session_scope() as s:
            s.get(BacktestRun, run_id).status = "running"
        now = datetime.now(timezone.utc)
        if body.dataset == "synthetic":
            ds = scenario_dataset(["rug", "pnd", "grind", "dead", "noise", "grind", "rug", "pnd"])
        elif body.dataset == "imported":
            from mci.backtesting.data import load_dataset

            files = sorted(Path(get_settings().data_dir).glob("universe_*.json"))
            if not files:
                raise ValueError("nessun dataset importato: esegui prima 'mci import-universe'")
            ds = load_dataset(files[-1])
        else:
            start = datetime.fromisoformat(body.start) if body.start else now - timedelta(days=90)
            end = datetime.fromisoformat(body.end) if body.end else now
            start = start if start.tzinfo else start.replace(tzinfo=timezone.utc)
            end = end if end.tzinfo else end.replace(tzinfo=timezone.utc)
            ds = dataset_from_db(start, end, body.timeframe)
        cfg = BacktestConfig(
            strategy_codes=[c.upper() for c in body.strategies], strategy_params=body.strategy_params,
            profile=body.profile, profile_overrides=body.profile_overrides, exit_policy=body.exit_policy,
            exit_overrides=body.exit_overrides, initial_capital_sol=body.capital_sol,
        )
        res = run_backtest(ds, cfg)
        d = res.to_dict()
        md = render_report(f"Backtest {body.name}", {body.name: res})
        with session_scope() as s:
            r = s.get(BacktestRun, run_id)
            r.status, r.metrics, r.equity_curve = "done", d["metrics"], d["equity_curve"]
            r.trades, r.data_info, r.warnings, r.report_md = d["trades"], d["data_info"], d["warnings"], md
            repo.log_event(s, "param", f"backtest #{run_id} completato", data={"config": d["config"]})
    except Exception as e:
        log.exception("backtest job failed")
        with session_scope() as s:
            r = s.get(BacktestRun, run_id)
            r.status, r.error = "failed", f"{type(e).__name__}: {e}"


def create_app() -> FastAPI:
    settings = get_settings()
    init_engine(settings.database_url)
    app = FastAPI(title="Memecoin Intelligence API", version="0.1.0", docs_url=None, redoc_url=None)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        resp = await call_next(request)
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "no-referrer"
        return resp

    # ------------------------------------------------------------------ public
    @app.get("/api/health")
    def health() -> dict[str, Any]:
        with session_scope() as s:
            st = _worker_status(s)
        return {"ok": True, "worker_alive": st.get("worker_alive"), "heartbeat_age_s": st.get("heartbeat_age_s")}

    @app.post("/api/auth/login")
    def login(body: LoginBody, request: Request) -> dict[str, Any]:
        ip = request.client.host if request.client else "?"
        if not check_login(settings, ip, body.username, body.password):
            raise HTTPException(401, "credenziali non valide")
        token, exp = issue_token(settings, body.username)
        return {"token": token, "expires_at": exp}

    # ------------------------------------------------------------------ overview
    @app.get("/api/overview")
    def overview(_: str = Depends(require_user)) -> dict[str, Any]:
        with session_scope() as s:
            st = _worker_status(s)
            mode = _mode(s)
            summ = perf.summary(s, mode, settings.initial_capital_sol, st.get("sol_eur"))
            from mci.database.models import EquitySnapshot

            eq = s.scalars(select(EquitySnapshot).where(EquitySnapshot.mode == mode)
                           .order_by(desc(EquitySnapshot.ts)).limit(500)).all()
            curve = [{"ts": _iso(r.ts), "equity": r.equity_sol, "drawdown": r.drawdown_pct} for r in reversed(eq)]
            n_tokens = repo.count_tokens(s)
        return {"summary": summ, "worker": st, "equity_curve": curve, "tokens_recorded": n_tokens}

    # ------------------------------------------------------------------ scanner
    @app.get("/api/scanner")
    def scanner(sort: str = "score", limit: int = 200, q: str = "", include_excluded: bool = False,
                _: str = Depends(require_user)) -> dict[str, Any]:
        cols = {"score": Token.last_score, "volume": Token.last_volume_h24, "liquidity": Token.last_liquidity_usd,
                "mcap": Token.last_mcap_usd, "momentum": Token.last_change_h1, "growth": Token.last_change_h1,
                "recent": Token.first_seen_at, "risk": Token.last_risk_level}
        col = cols.get(sort, Token.last_score)
        since = utcnow() - timedelta(hours=48)
        with session_scope() as s:
            stmt = select(Token).where(Token.last_seen_at >= since)
            if not include_excluded:
                stmt = stmt.where(Token.status != "excluded")
            if q:
                stmt = stmt.where((Token.symbol.ilike(f"%{q}%")) | (Token.address == q))
            rows = s.scalars(stmt.order_by(desc(col).nulls_last() if sort != "risk" else col).limit(min(limit, 500))).all()
            out = []
            for t in rows:
                snap = t.last_snapshot or {}
                created = to_utc(t.created_at)
                out.append({
                    "address": t.address, "symbol": t.symbol, "name": t.name, "dex": t.dex_id,
                    "price_usd": t.last_price_usd, "price_sol": t.last_price_native, "mcap_usd": t.last_mcap_usd,
                    "volume_h1": t.last_volume_h1, "volume_h24": t.last_volume_h24,
                    "liquidity_usd": t.last_liquidity_usd, "change_h1": t.last_change_h1, "score": t.last_score,
                    "label": t.last_label, "risk": t.last_risk_level, "holders": t.last_holders,
                    "age_hours": (utcnow() - created).total_seconds() / 3600 if created else None,
                    "social_growth": (snap.get("social_metrics") or {}).get("reddit"),
                    "signal": t.last_signal, "status": t.status, "first_seen_at": _iso(t.first_seen_at),
                    "exclusion": "; ".join(((t.last_score_detail or {}).get("exclusion_reasons") or [])[:2]) or None,
                    "coverage": (t.last_score_detail or {}).get("coverage"),
                })
        return {"tokens": out}

    def _journal(s, address: str) -> list[dict[str, Any]]:
        from mci.database.models import TokenEvent

        rows = s.scalars(select(TokenEvent).where(TokenEvent.token_address == address)
                         .order_by(TokenEvent.ts.asc()).limit(300)).all()
        return [{"ts": _iso(e.ts), "kind": e.kind, "value": e.value, "price": e.price, "age_s": e.age_s,
                 "detail": e.detail or {}} for e in rows]

    def _launch_only_detail(s, address: str) -> dict[str, Any]:
        """A pump.fun launch seen on the chain stream but never tracked by the scanner (e.g. it died early)."""
        from mci.database.models import FeatureSnapshot, PumpLaunch

        launch = s.get(PumpLaunch, address)
        if launch is None:
            raise HTTPException(404, "token non trovato")
        fsnaps = s.scalars(select(FeatureSnapshot).where(FeatureSnapshot.token_address == address)
                           .order_by(FeatureSnapshot.observed_at)).all()
        last = fsnaps[-1] if fsnaps else None
        candles = [{"ts": c.ts, "o": c.open, "h": c.high, "l": c.low, "c": c.close, "v": c.volume, "unit": "SOL"}
                   for c in repo.load_candles(s, address, "1m", currency="sol")]
        snap = {"token_address": address, "symbol": launch.symbol, "mayhem": launch.mayhem, "bonding_curve": True,
                "price_native": (launch.stats or {}).get("last_price"), "sources": {}, "onchain": {}}
        if last is not None:
            snap["onchain"] = {"curve": last.features,
                               "risk": {**(last.risk or {}), "factors": [], "note": "valori dell'istantanea " + last.horizon},
                               "opportunity": {**(last.opportunity or {}), "factors": [], "note": "valori dell'istantanea " + last.horizon}}
        return {
            "token": {"address": address, "symbol": launch.symbol, "name": launch.name, "dex": "pumpfun", "pair": None,
                      "deployer": launch.creator, "created_at": _iso(launch.created_at),
                      "first_seen_at": _iso(launch.created_at), "status": "solo stream"},
            "snapshot": snap, "score": None, "history": [], "candles": candles, "signals": [], "positions": [],
            "launch": {"created_at": _iso(launch.created_at), "creator": launch.creator, "mayhem": launch.mayhem,
                       "source": launch.source, "complete_at": _iso(launch.complete_at), "stats": launch.stats},
            "feature_snapshots": [{"horizon": f.horizon, "observed_at": _iso(f.observed_at), "features": f.features,
                                   "risk": f.risk, "opportunity": f.opportunity, "labels": f.labels} for f in fsnaps],
            "journal": _journal(s, address),
        }

    @app.get("/api/tokens/{address}")
    def token_detail(address: str, _: str = Depends(require_user)) -> dict[str, Any]:
        with session_scope() as s:
            t = s.scalar(select(Token).where(Token.address == address))
            if not t:
                return _launch_only_detail(s, address)
            snaps = s.scalars(select(TokenSnapshotRow).where(TokenSnapshotRow.token_id == t.id)
                              .order_by(desc(TokenSnapshotRow.observed_at)).limit(400)).all()
            history = [{"ts": _iso(r.observed_at), "price_usd": r.price_usd, "price_sol": r.price_native,
                        "liquidity_usd": r.liquidity_usd, "mcap_usd": r.market_cap_usd, "volume_h1": r.volume_h1,
                        "holders": r.holders, "score": r.score} for r in reversed(snaps)]
            candles = []
            since = int((utcnow() - timedelta(hours=24)).timestamp())
            if t.pair_address:
                candles = [{"ts": c.ts, "o": c.open, "h": c.high, "l": c.low, "c": c.close, "v": c.volume}
                           for c in repo.load_candles(s, t.pair_address, "1m", since_ts=since)]
            if not candles:  # bonding-curve tokens: candles from the free chain stream (volume in SOL)
                candles = [{"ts": c.ts, "o": c.open, "h": c.high, "l": c.low, "c": c.close, "v": c.volume, "unit": "SOL"}
                           for c in repo.load_candles(s, address, "1m", currency="sol", since_ts=since)]
            from mci.database.models import FeatureSnapshot, PumpLaunch

            launch = s.get(PumpLaunch, address)
            fsnaps = s.scalars(select(FeatureSnapshot).where(FeatureSnapshot.token_address == address)
                               .order_by(FeatureSnapshot.observed_at)).all()
            sigs = s.scalars(select(SignalRow).where(SignalRow.token_address == address)
                             .order_by(desc(SignalRow.created_at)).limit(20)).all()
            positions = s.scalars(select(Position).where(Position.token_address == address)).all()
            return {
                "token": {"address": t.address, "symbol": t.symbol, "name": t.name, "dex": t.dex_id,
                          "pair": t.pair_address, "deployer": t.deployer, "created_at": _iso(t.created_at),
                          "first_seen_at": _iso(t.first_seen_at), "status": t.status},
                "snapshot": t.last_snapshot, "score": t.last_score_detail, "history": history, "candles": candles,
                "signals": [{"id": r.id, "created_at": _iso(r.created_at), "strategy": r.strategy, "score": r.score,
                             "status": r.status, "reasons": r.reasons, "risks": r.risks,
                             "rejection": r.rejection_reason, "price_1h": r.price_1h,
                             "reference_price": r.reference_price, "max_gain_24h": r.max_gain_24h} for r in sigs],
                "positions": [perf.position_dict(p) for p in positions],
                "launch": None if launch is None else {
                    "created_at": _iso(launch.created_at), "creator": launch.creator, "mayhem": launch.mayhem,
                    "source": launch.source, "complete_at": _iso(launch.complete_at), "stats": launch.stats},
                "feature_snapshots": [{"horizon": f.horizon, "observed_at": _iso(f.observed_at), "features": f.features,
                                       "risk": f.risk, "opportunity": f.opportunity, "labels": f.labels}
                                      for f in fsnaps],
                "journal": _journal(s, address),
            }

    # ------------------------------------------------------------------ positions / signals
    @app.get("/api/positions")
    def positions(status: str = "all", _: str = Depends(require_user)) -> dict[str, Any]:
        with session_scope() as s:
            st = _worker_status(s)
            stmt = select(Position).where(Position.mode == _mode(s))
            if status in ("open", "closed"):
                stmt = stmt.where(Position.status == status)
            rows = s.scalars(stmt.order_by(desc(Position.opened_at)).limit(500)).all()
            return {"positions": [perf.position_dict(p, st.get("sol_eur")) for p in rows]}

    @app.get("/api/signals")
    def signals(limit: int = 100, _: str = Depends(require_user)) -> dict[str, Any]:
        with session_scope() as s:
            rows = s.scalars(select(SignalRow).order_by(desc(SignalRow.created_at)).limit(min(limit, 500))).all()
            return {"signals": [{"id": r.id, "created_at": _iso(r.created_at), "token": r.token_address,
                                 "symbol": r.symbol, "strategy": r.strategy, "mode": r.mode, "score": r.score,
                                 "status": r.status, "rejection": r.rejection_reason, "reasons": r.reasons,
                                 "risks": r.risks, "reference_price": r.reference_price, "price_15m": r.price_15m,
                                 "price_1h": r.price_1h, "price_4h": r.price_4h, "price_24h": r.price_24h,
                                 "max_gain_24h": r.max_gain_24h, "max_drawdown_24h": r.max_drawdown_24h}
                                for r in rows]}

    # ------------------------------------------------------------------ performance
    @app.get("/api/performance")
    def performance(_: str = Depends(require_user)) -> dict[str, Any]:
        with session_scope() as s:
            mode = _mode(s)
            from mci.database.models import EquitySnapshot

            eq = s.scalars(select(EquitySnapshot).where(EquitySnapshot.mode == mode).order_by(EquitySnapshot.ts)).all()
            step = max(1, len(eq) // 1000)
            curve = [{"ts": _iso(r.ts), "equity": r.equity_sol, "drawdown": r.drawdown_pct} for r in eq[::step]]
            closed = repo.closed_positions(s, mode)
            by_dex: dict[str, list[float]] = defaultdict(list)
            for p in closed:
                by_dex[p.dex_id or "n/d"].append(p.realized_pnl_sol or 0.0)
            # signal quality (what happened after signals, Fase 14)
            sig = s.scalars(select(SignalRow).where(SignalRow.price_1h.is_not(None))).all()
            sig_q: dict[str, list[float]] = defaultdict(list)
            for r in sig:
                if r.reference_price:
                    sig_q[r.strategy].append(r.price_1h / r.reference_price - 1)
            return {
                "summary": perf.summary(s, mode, settings.initial_capital_sol),
                "equity_curve": curve,
                "daily": perf.period_pnl(s, mode, "day"),
                "weekly": perf.period_pnl(s, mode, "week"),
                "monthly": perf.period_pnl(s, mode, "month"),
                "by_strategy": perf.by_strategy(s, mode),
                "by_category": [{"category": k, "trades": len(v), "pnl_sol": sum(v)} for k, v in sorted(by_dex.items())],
                "returns": perf.returns_distribution(s, mode),
                "signal_quality": [{"strategy": k, "signals": len(v), "avg_return_1h": sum(v) / len(v),
                                    "positive_share": sum(1 for x in v if x > 0) / len(v)} for k, v in sorted(sig_q.items())],
            }

    # ------------------------------------------------------------------ laboratorio
    @app.get("/api/lab")
    def lab(_: str = Depends(require_user)) -> dict[str, Any]:
        """Virtual portfolio without risk limits, side by side with the main one (per strategy)."""
        from mci.database.models import EquitySnapshot

        with session_scope() as s:
            st = _worker_status(s)
            sol_eur = st.get("sol_eur")
            summ = perf.summary(s, "lab", settings.initial_capital_sol, sol_eur)
            summ["paused"] = False
            eq = s.scalars(select(EquitySnapshot).where(EquitySnapshot.mode == "lab").order_by(EquitySnapshot.ts)).all()
            step = max(1, len(eq) // 1000)
            curve = [{"ts": _iso(r.ts), "equity": r.equity_sol, "drawdown": r.drawdown_pct} for r in eq[::step]]
            rows = s.scalars(select(Position).where(Position.mode == "lab").order_by(Position.opened_at.desc()).limit(500)).all()
            return {
                "enabled": settings.lab_enabled,
                "started_at": repo.get_state(s, "lab_started_at"),
                "summary": summ,
                "equity_curve": curve,
                "by_strategy": perf.strategy_stats(s, "lab"),
                "main_by_strategy": perf.strategy_stats(s, _mode(s)),
                "positions": [perf.position_dict(p, sol_eur) for p in rows],
                "skipped": repo.get_state(s, "lab_skipped") or {},
                "stats": repo.get_state(s, "lab_stats") or {"signals": 0, "by_strategy": {}},
                "last_scan_at": repo.get_state(s, "lab_last_scan_at"),
            }

    # ------------------------------------------------------------------ shadow experiments
    def _virtual_portfolio(s, mode: str, sol_eur: float | None, positions: int = 300) -> dict[str, Any]:
        from mci.database.models import EquitySnapshot
        from mci.paper_trading.lab import state_prefix

        pre = state_prefix(mode)
        summ = perf.summary(s, mode, settings.initial_capital_sol, sol_eur)
        summ["paused"] = False
        eq = s.scalars(select(EquitySnapshot).where(EquitySnapshot.mode == mode).order_by(EquitySnapshot.ts)).all()
        step = max(1, len(eq) // 600)
        rows = s.scalars(select(Position).where(Position.mode == mode).order_by(Position.opened_at.desc())
                         .limit(positions)).all()
        return {
            "mode": mode, "started_at": repo.get_state(s, f"{pre}_started_at"), "summary": summ,
            "equity_curve": [{"ts": _iso(r.ts), "equity": r.equity_sol} for r in eq[::step]],
            "by_strategy": perf.strategy_stats(s, mode),
            "positions": [perf.position_dict(p, sol_eur) for p in rows],
            "skipped": repo.get_state(s, f"{pre}_skipped") or {},
            "stats": repo.get_state(s, f"{pre}_stats") or {"signals": 0, "by_strategy": {}},
            "last_scan_at": repo.get_state(s, f"{pre}_last_scan_at"),
        }

    @app.get("/api/experiments")
    def experiments(_: str = Depends(require_user)) -> dict[str, Any]:
        from mci.paper_trading.experiments import EXPERIMENTS
        from mci.research.promotion import experiment_report
        from mci.scoring.risk_opportunity import RULES

        with session_scope() as s:
            sol_eur = _worker_status(s).get("sol_eur")
            out = []
            for mode, meta in EXPERIMENTS.items():
                d = _virtual_portfolio(s, mode, sol_eur, positions=150)
                d.update(meta)
                d["gate"] = experiment_report(s, mode)
                out.append(d)
            base = perf.summary(s, "lab", settings.initial_capital_sol, sol_eur)
            return {"enabled": settings.experiments_enabled and settings.lab_enabled, "experiments": out,
                    "baseline": {"mode": "lab", "summary": base, "by_strategy": perf.strategy_stats(s, "lab")},
                    "rules": [{"code": r.code, "mode": r.mode, "description": r.description} for r in RULES.values()]}

    # ------------------------------------------------------------------ research / data / system
    @app.get("/api/research")
    def research(_: str = Depends(require_user)) -> dict[str, Any]:
        from mci.research.feature_store import dataset_counts
        from mci.scoring.risk_opportunity import NOTE, RULES

        with session_scope() as s:
            rep = repo.get_state(s, "research_report")
            counts = repo.get_state(s, "dataset_counts")
            events = repo.get_state(s, "event_study")
            rules_lab = repo.get_state(s, "rules_lab")
            copy = {"report": repo.get_state(s, "copy_report"), "leaders": repo.get_state(s, "copy_leaders"),
                    "live": (_worker_status(s).get("copy") or []), "ledger": _worker_status(s).get("wallet_ledger")}
        return {"report": rep, "dataset": counts or dataset_counts(), "index_note": NOTE, "event_study": events,
                "rules_lab": rules_lab, "copy": copy,
                "rules": [{"code": r.code, "mode": r.mode, "description": r.description} for r in RULES.values()]}

    @app.get("/api/launches")
    def launches(limit: int = 150, _: str = Depends(require_user)) -> dict[str, Any]:
        """Most recent pump.fun launches seen on the free chain stream, with their t+5m indices."""
        from mci.database.models import FeatureSnapshot, PumpLaunch

        with session_scope() as s:
            rows = s.scalars(select(PumpLaunch).order_by(desc(PumpLaunch.created_at)).limit(min(limit, 500))).all()
            mints = [r.mint for r in rows]
            fsn = {}
            if mints:
                for f in s.scalars(select(FeatureSnapshot).where(FeatureSnapshot.token_address.in_(mints),
                                                                 FeatureSnapshot.horizon == "t+5m")).all():
                    fsn[f.token_address] = f
            out = []
            for r in rows:
                f = fsn.get(r.mint)
                ff = (f.features if f else None) or {}
                out.append({
                    "mint": r.mint, "symbol": r.symbol, "name": r.name, "created_at": _iso(r.created_at),
                    "creator": r.creator, "mayhem": r.mayhem, "source": r.source, "complete_at": _iso(r.complete_at),
                    "stats": r.stats or {},
                    "t5": None if not f else {
                        "complete": ff.get("complete"), "unique_buyers": ff.get("unique_buyers"),
                        "buy_pressure": ff.get("buy_pressure"), "sniper_pct": ff.get("sniper_pct"),
                        "top10_net_pct": ff.get("top10_net_pct"), "creator_sold": ff.get("creator_sold"),
                        "risk": (f.risk or {}).get("value"), "opportunity": (f.opportunity or {}).get("value"),
                        "labels": f.labels},
                })
            st = _worker_status(s)
        return {"launches": out, "stream": st.get("chain_stream"), "tracker": (st.get("onchain") or {}).get("launches")}

    @app.get("/api/system")
    def system(_: str = Depends(require_user)) -> dict[str, Any]:
        from mci.research.feature_store import dataset_counts

        with session_scope() as s:
            st = _worker_status(s)
            costs = repo.get_state(s, "network_costs")
            db_size = None
            try:
                if settings.database_url.startswith("postgresql"):
                    from sqlalchemy import text

                    db_size = s.execute(text("select pg_database_size(current_database())")).scalar()
                elif settings.database_url.startswith("sqlite"):
                    db_size = Path(settings.database_url.split("///", 1)[-1]).stat().st_size
            except Exception:
                db_size = None
            gaps = repo.get_state(s, "stream_gaps") or []
            counts = repo.get_state(s, "dataset_counts")
            errors = s.scalars(select(Event).where(Event.level == "error").order_by(desc(Event.ts)).limit(20)).all()
        now = utcnow().timestamp()
        oc = st.get("onchain") or {}
        return {
            "worker": {k: st.get(k) for k in ("mode", "started_at", "last_cycle", "cycle", "tracked", "heartbeat",
                                              "worker_alive", "jupiter_key", "pumpportal_connected", "market_state")},
            "sources": st.get("sources") or {},
            "chain_stream": st.get("chain_stream"),
            "launch_tracker": oc.get("launches"),
            "rpc": oc.get("rpc"),
            "wallets": oc.get("wallets"),
            "onchain": {k: oc.get(k) for k in ("security_checks", "curve_reads", "wallet_analyses", "errors",
                                               "rugcheck_disagreements", "sell_sims", "sell_sim_ok", "sell_sim_blocked",
                                               "sell_sim_unverified", "last_sell_sim")},
            "network_costs": costs,
            "costs_in_use": st.get("network_costs"),
            "dataset": counts or dataset_counts(),
            "db_size_bytes": db_size,
            "stream_gaps_24h": [[a, b] for a, b in gaps if b >= now - 86400][-30:],
            "recent_errors": [{"ts": _iso(e.ts), "category": e.category, "message": e.message[:300]} for e in errors],
            "experiments": st.get("experiments"),
        }

    # ------------------------------------------------------------------ risk
    @app.get("/api/risk")
    def risk(_: str = Depends(require_user)) -> dict[str, Any]:
        with session_scope() as s:
            mode = _mode(s)
            state = repo.get_state(s, f"portfolio_{mode}") or {}
            summ = perf.summary(s, mode, settings.initial_capital_sol)
            prof = get_profile(settings.risk_profile)
            equity = state.get("equity", settings.initial_capital_sol)
            exposure = state.get("exposure") or {}
            day_start = state.get("day_start_equity") or equity
            return {
                "mode": mode, "profile": prof.to_dict(), "equity_sol": equity, "cash_sol": state.get("cash", equity),
                "exposure_sol": sum(exposure.values()), "exposure_by_token": exposure,
                "exposure_pct": sum(exposure.values()) / equity if equity else 0,
                "drawdown": summ["drawdown"], "daily_pnl_pct": equity / day_start - 1 if day_start else 0,
                "daily_loss_limit_pct": prof.daily_loss_limit_pct, "open_positions": summ["open_positions"],
                "max_positions": prof.max_positions, "trades_today": state.get("trades_today", 0),
                "consecutive_losses": state.get("consecutive_losses", 0), "paused_until": state.get("paused_until"),
                "kill_switch": state.get("kill_switch", False), "kill_reason": state.get("kill_reason", ""),
                "paused": bool(repo.get_state(s, "control_paused", False)),
                "live_gates": settings.live_gate_failures(),
            }

    @app.post("/api/control/{action}")
    def control(action: str, user: str = Depends(require_user)) -> dict[str, Any]:
        with session_scope() as s:
            if action == "pause":
                repo.set_state(s, "control_paused", True)
            elif action == "resume":
                repo.set_state(s, "control_paused", False)
                repo.set_state(s, "control_resume_request", True)
            elif action == "kill":
                repo.set_state(s, "control_kill", f"attivato dalla dashboard ({user})")
            else:
                raise HTTPException(400, "azione non valida")
            repo.log_event(s, "param", f"controllo '{action}' dalla dashboard", data={"user": user})
        return {"ok": True}

    # ------------------------------------------------------------------ logs
    @app.get("/api/logs")
    def logs(category: str = "", limit: int = 200, _: str = Depends(require_user)) -> dict[str, Any]:
        with session_scope() as s:
            stmt = select(Event)
            if category:
                stmt = stmt.where(Event.category == category)
            rows = s.scalars(stmt.order_by(desc(Event.ts)).limit(min(limit, 1000))).all()
            return {"events": [{"id": e.id, "ts": _iso(e.ts), "level": e.level, "category": e.category,
                                "message": e.message, "token": e.token_address} for e in rows]}

    # ------------------------------------------------------------------ backtest lab
    @app.get("/api/config/options")
    def options(_: str = Depends(require_user)) -> dict[str, Any]:
        strategies = []
        for code, cls in STRATEGIES.items():
            params = cls.params_cls()
            strategies.append({"code": code, "name": cls.name, "timeframe": cls.default_timeframe,
                               "params": {f.name: getattr(params, f.name) for f in fields(params)}})
        return {"strategies": strategies, "exit_policies": {k: v.to_dict() for k, v in EXIT_POLICIES.items()},
                "profiles": {k: v.to_dict() for k, v in PROFILES.items()}}

    @app.get("/api/backtests")
    def backtests(_: str = Depends(require_user)) -> dict[str, Any]:
        with session_scope() as s:
            rows = s.scalars(select(BacktestRun).order_by(desc(BacktestRun.created_at)).limit(100)).all()
            return {"runs": [{"id": r.id, "name": r.name, "status": r.status, "created_at": _iso(r.created_at),
                              "metrics": r.metrics, "data_info": r.data_info, "error": r.error} for r in rows]}

    @app.get("/api/backtests/{run_id}")
    def backtest(run_id: int, _: str = Depends(require_user)) -> dict[str, Any]:
        with session_scope() as s:
            r = s.get(BacktestRun, run_id)
            if not r:
                raise HTTPException(404, "backtest non trovato")
            return {"id": r.id, "name": r.name, "status": r.status, "config": r.config, "metrics": r.metrics,
                    "equity_curve": r.equity_curve, "trades": r.trades, "data_info": r.data_info,
                    "warnings": r.warnings, "report_md": r.report_md, "error": r.error}

    @app.post("/api/backtests")
    def start_backtest(body: BacktestBody, user: str = Depends(require_user)) -> dict[str, Any]:
        bad = [c for c in body.strategies if c.upper() not in STRATEGIES]
        if bad or body.profile not in PROFILES or body.exit_policy not in EXIT_POLICIES:
            raise HTTPException(400, "strategia, profilo o politica di uscita non validi")
        with session_scope() as s:
            run = BacktestRun(name=body.name, status="queued", config=body.model_dump())
            s.add(run)
            s.flush()
            run_id = run.id
            repo.log_event(s, "param", f"backtest #{run_id} avviato da {user}", data=body.model_dump())
        threading.Thread(target=_run_backtest_job, args=(run_id, body), daemon=True).start()
        return {"id": run_id, "status": "queued"}

    # ------------------------------------------------------------------ frontend
    dist = Path(settings.frontend_dist_dir)
    if dist.exists() and (dist / "index.html").exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            if path.startswith("api/"):
                return JSONResponse({"detail": "not found"}, status_code=404)
            f = dist / path
            if path and f.is_file() and dist in f.resolve().parents:
                return FileResponse(f)
            return FileResponse(dist / "index.html")

    return app
