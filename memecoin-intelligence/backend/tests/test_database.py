"""Database edge cases that SQLite does not enforce but PostgreSQL does."""

from conftest import good_snapshot

from mci.database import repo
from mci.database.session import session_scope
from mci.domain import Signal, utcnow
from mci.scoring.scorer import score_token


def test_very_long_token_names_do_not_break_recording(db):
    long = "🚀" * 40 + "THE MOST AMAZING MEMECOIN EVER " * 10
    snap = good_snapshot(name=long, symbol=long, dex_id="x" * 80)
    with session_scope() as s:
        tok = repo.upsert_token(s, snap, "test", score_token(snap))
        repo.add_snapshot(s, tok, snap, None)
        sig = Signal(strategy="A", token_address=snap.token_address, symbol=long, created_at=utcnow(),
                     reference_price=1.0, stop_price=0.8, score=80, reasons=[], risks=[])
        repo.record_signal(s, sig, "paper", snap, None)
    with session_scope() as s:
        assert repo.count_tokens(s) == 1


def test_non_finite_numbers_are_not_stored_in_json(db):
    snap = good_snapshot()
    snap.social_metrics["weird"] = float("nan")
    with session_scope() as s:
        tok = repo.upsert_token(s, snap, "test", None)
        repo.add_snapshot(s, tok, snap, None)


def test_duplicate_candle_timestamps_are_ignored(db):
    from mci.domain import Candle

    c = [Candle(60, 1, 1, 1, 1, 1), Candle(60, 1, 1, 1, 1, 2), Candle(120, 1, 1, 1, 1, 1)]
    with session_scope() as s:
        assert repo.upsert_candles(s, "T", "P", "1m", c) == 2
        assert repo.upsert_candles(s, "T", "P", "1m", c) == 0


def test_one_bad_token_does_not_block_recording_of_others(db, monkeypatch):
    from mci.config import get_settings
    from mci.scanner.service import Scanner, TrackedToken

    sc = Scanner(get_settings(), None, None, None, None, None)  # type: ignore[arg-type]
    good = good_snapshot(token_address="GoodOne")
    bad = good_snapshot(token_address="BadOne")
    sc.tokens = {"GoodOne": TrackedToken("GoodOne", good, utcnow(), "t"), "BadOne": TrackedToken("BadOne", bad, utcnow(), "t")}
    real = repo.upsert_token

    def flaky(s, snap, source, score=None):
        if snap.token_address == "BadOne":
            raise ValueError("boom")
        return real(s, snap, source, score)

    monkeypatch.setattr(repo, "upsert_token", flaky)
    sc._record([])
    with session_scope() as s:
        assert repo.count_tokens(s) == 1
        from sqlalchemy import select

        from mci.database.models import Event

        ev = s.scalars(select(Event).where(Event.category == "error")).all()
        assert ev and "BadOne"[:8] in ev[0].message or "boom" in ev[0].message
