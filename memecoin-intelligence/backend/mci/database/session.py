"""Engine / session factory. SQLite for development and tests, PostgreSQL in production."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from mci.database.models import Base

_engine: Engine | None = None
_factory: sessionmaker[Session] | None = None


def init_engine(url: str, echo: bool = False) -> Engine:
    global _engine, _factory
    kwargs: dict = {"echo": echo, "pool_pre_ping": True, "future": True}
    if url.startswith("sqlite"):
        path = url.split("///", 1)[-1]
        if path and path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
    _engine = create_engine(url, **kwargs)
    if url.startswith("sqlite"):

        @event.listens_for(_engine, "connect")
        def _pragma(conn, _):  # pragma: no cover - trivial
            cur = conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

    Base.metadata.create_all(_engine)
    _factory = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def get_engine() -> Engine:
    if _engine is None:
        from mci.config import get_settings

        init_engine(get_settings().database_url)
    assert _engine is not None
    return _engine


@contextmanager
def session_scope() -> Iterator[Session]:
    if _factory is None:
        get_engine()
    assert _factory is not None
    s = _factory()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
