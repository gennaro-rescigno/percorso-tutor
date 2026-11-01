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
