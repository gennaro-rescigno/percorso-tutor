"""Database schema (SQLAlchemy 2.x). SQLite by default, PostgreSQL via DATABASE_URL."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from sqlalchemy import (JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint,
                        create_engine, event)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from .config import get_settings


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class Base(DeclarativeBase):
    pass


class Fixture(Base):
    __tablename__ = "fixtures"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # provider fixture id (API-Football)
    provider: Mapped[str] = mapped_column(String(32), default="api_football")
    league_id: Mapped[int | None] = mapped_column(Integer, index=True)
    league_name: Mapped[str | None] = mapped_column(String(128))
    country: Mapped[str | None] = mapped_column(String(64))
    season: Mapped[int | None] = mapped_column(Integer)
    round: Mapped[str | None] = mapped_column(String(64))
    home_id: Mapped[int | None] = mapped_column(Integer)
    home_name: Mapped[str] = mapped_column(String(128))
    away_id: Mapped[int | None] = mapped_column(Integer)
    away_name: Mapped[str] = mapped_column(String(128))
    kickoff: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str | None] = mapped_column(String(8), index=True)
    elapsed: Mapped[int | None] = mapped_column(Integer)
    extra: Mapped[int | None] = mapped_column(Integer)
    home_goals: Mapped[int | None] = mapped_column(Integer)
    away_goals: Mapped[int | None] = mapped_column(Integer)
    ht_home: Mapped[int | None] = mapped_column(Integer)
    ht_away: Mapped[int | None] = mapped_column(Integer)
    ft_home: Mapped[int | None] = mapped_column(Integer)  # regulation-time result (settlement)
    ft_away: Mapped[int | None] = mapped_column(Integer)
    corners_home_final: Mapped[int | None] = mapped_column(Integer)
    corners_away_final: Mapped[int | None] = mapped_column(Integer)
    is_live: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    finished: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    last_seen_live: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    form: Mapped[dict | None] = mapped_column(JSON)  # cached team form / priors
    form_fetched_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))


class StatSnapshot(Base):
    __tablename__ = "stat_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.id"), index=True)
    ts: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    status: Mapped[str | None] = mapped_column(String(8))
    elapsed: Mapped[int | None] = mapped_column(Integer)
    extra: Mapped[int | None] = mapped_column(Integer)
    home_goals: Mapped[int] = mapped_column(Integer, default=0)
    away_goals: Mapped[int] = mapped_column(Integer, default=0)
    stats: Mapped[dict] = mapped_column(JSON)  # {"home": {...}, "away": {...}} normalized, None = missing
    __table_args__ = (Index("ix_snap_fixture_ts", "fixture_id", "ts"),)


class MatchEvent(Base):
    __tablename__ = "match_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.id"), index=True)
    minute: Mapped[int | None] = mapped_column(Integer)
    extra: Mapped[int | None] = mapped_column(Integer)
    side: Mapped[str | None] = mapped_column(String(4))  # home / away
    type: Mapped[str] = mapped_column(String(32))
    detail: Mapped[str | None] = mapped_column(String(64))
    player: Mapped[str | None] = mapped_column(String(128))
    signature: Mapped[str] = mapped_column(String(256))
    __table_args__ = (UniqueConstraint("fixture_id", "signature", name="uq_event_sig"),)


class OddsSnapshot(Base):
    """Only *changes* are stored: a row is written when price/suspension differs from the last one."""

    __tablename__ = "odds_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.id"), index=True)
    ts: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    source: Mapped[str] = mapped_column(String(32))
    bookmaker: Mapped[str | None] = mapped_column(String(64))
    market: Mapped[str] = mapped_column(String(32))
    pick: Mapped[str] = mapped_column(String(16))
    line: Mapped[float | None] = mapped_column(Float)
    odds: Mapped[float] = mapped_column(Float)
    suspended: Mapped[bool] = mapped_column(Boolean, default=False)
    provider_update: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    raw_market: Mapped[str | None] = mapped_column(String(128))
    __table_args__ = (Index("ix_odds_fixture_key", "fixture_id", "market", "pick", "line"),)


class Prediction(Base):
    """Periodic log of model probabilities for every priced market (calibration / error analysis)."""

    __tablename__ = "predictions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.id"), index=True)
    ts: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    elapsed: Mapped[int | None] = mapped_column(Integer)
    period: Mapped[int | None] = mapped_column(Integer)
    home_goals: Mapped[int] = mapped_column(Integer)
    away_goals: Mapped[int] = mapped_column(Integer)
    market: Mapped[str] = mapped_column(String(32))
    pick: Mapped[str] = mapped_column(String(16))
    line: Mapped[float | None] = mapped_column(Float)
    odds: Mapped[float | None] = mapped_column(Float)
    p_model: Mapped[float] = mapped_column(Float)
    p_low: Mapped[float] = mapped_column(Float)
    p_high: Mapped[float] = mapped_column(Float)
    p_cons: Mapped[float] = mapped_column(Float)
    p_market_fair: Mapped[float | None] = mapped_column(Float)
    ev: Mapped[float | None] = mapped_column(Float)
    ev_cons: Mapped[float | None] = mapped_column(Float)
    model_version: Mapped[str] = mapped_column(String(64))
    goal_model: Mapped[str] = mapped_column(String(32))
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    result: Mapped[str | None] = mapped_column(String(12))  # filled at settlement
    context: Mapped[dict | None] = mapped_column(JSON)  # e.g. ht score / goals timeline for settlement


class Opportunity(Base):
    __tablename__ = "opportunities"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.id"), index=True)
    market: Mapped[str] = mapped_column(String(32))
    pick: Mapped[str] = mapped_column(String(16))
    line: Mapped[float | None] = mapped_column(Float)
    label: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(16), index=True)  # active | invalidated | settled
    first_seen: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    invalidated_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    invalidation_reason: Mapped[str | None] = mapped_column(Text)
    # snapshot at detection (this is the "pick" used for backtesting)
    minute_at_detection: Mapped[int | None] = mapped_column(Integer)
    period_at_detection: Mapped[int | None] = mapped_column(Integer)
    score_at_detection: Mapped[str] = mapped_column(String(16))
    odds_at_detection: Mapped[float] = mapped_column(Float)
    bookmaker: Mapped[str | None] = mapped_column(String(64))
    p_model_at_detection: Mapped[float] = mapped_column(Float)
    p_cons_at_detection: Mapped[float] = mapped_column(Float)
    ev_cons_at_detection: Mapped[float] = mapped_column(Float)
    confidence_at_detection: Mapped[str] = mapped_column(String(8))
    # latest values
    last_odds: Mapped[float | None] = mapped_column(Float)
    best_odds: Mapped[float | None] = mapped_column(Float)
    last_p_model: Mapped[float | None] = mapped_column(Float)
    last_ev_cons: Mapped[float | None] = mapped_column(Float)
    last_payload: Mapped[dict | None] = mapped_column(JSON)
    closing_odds: Mapped[float | None] = mapped_column(Float)
    # settlement
    result: Mapped[str | None] = mapped_column(String(12))
    profit: Mapped[float | None] = mapped_column(Float)
    settled_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (Index("ix_opp_key", "fixture_id", "market", "pick", "line"),)


class ProviderLog(Base):
    """Proof-of-data: every provider call with HTTP status, result count and quota headers."""

    __tablename__ = "provider_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    provider: Mapped[str] = mapped_column(String(32))
    endpoint: Mapped[str] = mapped_column(String(256))
    http_status: Mapped[int | None] = mapped_column(Integer)
    results: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    quota: Mapped[dict | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)


_engine = None
_Session = None


def get_engine():
    global _engine, _Session
    if _engine is None:
        url = get_settings().database_url
        kwargs = {}
        if url.startswith("sqlite"):
            path = url.split("sqlite:///", 1)[-1]
            if path and path != ":memory:":
                Path(path).parent.mkdir(parents=True, exist_ok=True)
            kwargs["connect_args"] = {"check_same_thread": False}
        _engine = create_engine(url, pool_pre_ping=True, **kwargs)
        if url.startswith("sqlite"):
            @event.listens_for(_engine, "connect")
            def _pragma(dbapi_conn, _):  # noqa: ANN001
                cur = dbapi_conn.cursor()
                cur.execute("PRAGMA journal_mode=WAL")
                cur.execute("PRAGMA synchronous=NORMAL")
                cur.close()
        Base.metadata.create_all(_engine)
        _Session = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def session():
    get_engine()
    return _Session()


def reset_engine_for_tests() -> None:
    global _engine, _Session
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _Session = None
