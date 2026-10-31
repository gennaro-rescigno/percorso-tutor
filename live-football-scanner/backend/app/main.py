"""FastAPI application: REST + WebSocket API and static dashboard."""
from __future__ import annotations

import asyncio
import contextlib
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select

from .config import get_settings
from .db import Fixture, OddsSnapshot, Opportunity, Prediction, ProviderLog, StatSnapshot, get_engine, session
from .engine.model import ModelBundle
from .services.backtest import metrics
from .services.scanner import Scanner

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("app")

settings = get_settings()


def _load_model() -> ModelBundle | None:
    p = Path(settings.model_path)
    if not p.exists():
        log.warning("model file not found: %s", p)
        return None
    return ModelBundle.load(p)


bundle = _load_model()
scanner = Scanner(settings, bundle)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    get_engine()
    task = None
    if settings.scanner_enabled:
        task = asyncio.create_task(scanner.run())
    yield
    scanner.stop()
    if task:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await task


app = FastAPI(title="Live Football Intelligence Scanner", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
                   allow_methods=["*"], allow_headers=["*"])


@app.get("/api/health")
def health():
    with session() as db:
        counts = {
            "fixtures": db.scalar(select(func.count()).select_from(Fixture)),
            "stat_snapshots": db.scalar(select(func.count()).select_from(StatSnapshot)),
            "odds_snapshots": db.scalar(select(func.count()).select_from(OddsSnapshot)),
            "predictions": db.scalar(select(func.count()).select_from(Prediction)),
            "opportunities": db.scalar(select(func.count()).select_from(Opportunity)),
        }
    return {"status": "ok", "providers": scanner.provider_status(), "db": counts,
            "database": settings.database_url.split("://")[0],
            "filters": {"min_odds": settings.min_odds, "min_ev": settings.min_ev, "min_edge": settings.min_edge,
                        "max_model_market_gap": settings.max_model_market_gap,
                        "odds_max_age_s": settings.odds_max_age_s}}


@app.get("/api/state")
def state():
    return scanner.snapshot()


@app.post("/api/scan")
async def scan_now():
    await asyncio.to_thread(scanner.cycle)
    scanner._publish()
    return scanner.snapshot()


@app.get("/api/fixtures/{fixture_id}")
def fixture_detail(fixture_id: int):
    d = scanner.fixture_detail(fixture_id)
    if d is None:
        raise HTTPException(404, "Partita non presente nell'ultimo ciclo live")
    return JSONResponse(d)


@app.get("/api/opportunities")
def opportunities(status: str | None = None, limit: int = Query(100, le=1000)):
    with session() as db:
        q = select(Opportunity).order_by(Opportunity.first_seen.desc()).limit(limit)
        if status:
            q = q.where(Opportunity.status == status)
        rows = db.scalars(q).all()
        fx = {f.id: f for f in db.scalars(select(Fixture).where(Fixture.id.in_({o.fixture_id for o in rows})))}
    out = []
    for o in rows:
        f = fx.get(o.fixture_id)
        out.append({"id": o.id, "fixture_id": o.fixture_id, "match": f"{f.home_name} - {f.away_name}" if f else "?",
                    "league": f.league_name if f else None, "label": o.label, "market": o.market, "pick": o.pick,
                    "line": o.line, "status": o.status, "first_seen": o.first_seen.isoformat(),
                    "invalidated_at": o.invalidated_at.isoformat() if o.invalidated_at else None,
                    "reason": o.invalidation_reason, "minute": o.minute_at_detection, "score": o.score_at_detection,
                    "odds": o.odds_at_detection, "closing_odds": o.closing_odds, "p_model": o.p_model_at_detection,
                    "p_cons": o.p_cons_at_detection, "ev_cons": o.ev_cons_at_detection,
                    "confidence": o.confidence_at_detection, "result": o.result, "profit": o.profit})
    return out


@app.get("/api/backtest")
def backtest():
    with session() as db:
        return metrics(db)


@app.get("/api/model")
def model_info():
    if bundle is None:
        raise HTTPException(404, "Modello non addestrato: esegui `python -m training.train`")
    glms = {k: {"features": g.features, "meta": g.meta, "dispersion": g.dispersion} for k, g in bundle.glms.items()}
    return {"version": bundle.version, "meta": bundle.meta, "refs": bundle.refs, "mu_goals": bundle.mu_goals,
            "stoppage": bundle.stoppage, "validation": bundle.validation, "glms": glms}


@app.get("/api/provider-log")
def provider_log(limit: int = Query(50, le=500)):
    with session() as db:
        rows = db.scalars(select(ProviderLog).order_by(ProviderLog.ts.desc()).limit(limit)).all()
    return [{"ts": r.ts.isoformat(), "provider": r.provider, "endpoint": r.endpoint, "http_status": r.http_status,
             "results": r.results, "latency_ms": r.latency_ms, "quota": r.quota, "error": r.error} for r in rows]


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    q = scanner.subscribe()
    try:
        await websocket.send_json(scanner.snapshot())
        while True:
            payload = await q.get()
            await websocket.send_json(payload)
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        scanner.unsubscribe(q)


# ----------------------------------------------------------------------- dashboard (built React app)
_dist = Path(settings.frontend_dist)
if _dist.exists():
    app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        target = _dist / path
        if path and target.is_file():
            return FileResponse(target)
        return FileResponse(_dist / "index.html")
