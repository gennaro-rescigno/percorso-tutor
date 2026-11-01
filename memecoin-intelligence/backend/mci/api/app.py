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

    @app.get("/api/tokens/{address}")
    def token_detail(address: str, _: str = Depends(require_user)) -> dict[str, Any]:
        with session_scope() as s:
            t = s.scalar(select(Token).where(Token.address == address))
            if not t:
                raise HTTPException(404, "token non trovato")
            snaps = s.scalars(select(TokenSnapshotRow).where(TokenSnapshotRow.token_id == t.id)
                              .order_by(desc(TokenSnapshotRow.observed_at)).limit(400)).all()
            history = [{"ts": _iso(r.observed_at), "price_usd": r.price_usd, "price_sol": r.price_native,
                        "liquidity_usd": r.liquidity_usd, "mcap_usd": r.market_cap_usd, "volume_h1": r.volume_h1,
                        "holders": r.holders, "score": r.score} for r in reversed(snaps)]
            candles = []
            if t.pair_address:
                since = int((utcnow() - timedelta(hours=24)).timestamp())
                candles = [{"ts": c.ts, "o": c.open, "h": c.high, "l": c.low, "c": c.close, "v": c.volume}
                           for c in repo.load_candles(s, t.pair_address, "1m", since_ts=since)]
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
