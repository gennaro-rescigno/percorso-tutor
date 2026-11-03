"""Persistence of the free chain-stream data, point-in-time feature snapshots and outcome labels.

* launches / early trades / 1-minute stream candles (``candles`` table, currency "sol", source "stream");
* feature snapshots of EVERY launch at t+1m, t+5m, t+15m (including the ones that die: no survivorship bias);
* labels computed only after the outcome window (240 min) has fully elapsed, from the stream candles. Windows
  overlapping a stream outage are marked ``incomplete`` and excluded from the research statistics.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import bindparam, delete, insert, select, update

from mci.database.models import CandleRow, FeatureSnapshot, PumpLaunch, PumpTradeRow, TokenEvent, WalletProfile
from mci.database.session import session_scope
from mci.domain import TokenSnapshot, utcnow
from mci.onchain.curve_features import FEATURE_VERSION, MIN_COVERAGE, curve_features
from mci.onchain.launches import EXTRA_HORIZONS, LaunchState, LaunchTracker, interval_coverage
from mci.onchain.wallets import deployer_history
from mci.scoring.risk_opportunity import opportunity_index, risk_index

log = logging.getLogger(__name__)

LABEL_WINDOW_MIN = 240
STREAM_CURRENCY = "sol"


def _aware(d: datetime | None) -> datetime | None:
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def persist_stream(rows: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    """Write what ``LaunchTracker.drain()`` returned. Idempotent on restarts (existing keys are skipped)."""
    out = {"launches": 0, "launch_updates": 0, "stats": 0, "trades": 0, "bars": 0, "events": 0}
    with session_scope() as s:
        launches = rows.get("launches") or []
        if launches:
            mints = [r["mint"] for r in launches]
            existing = set(s.scalars(select(PumpLaunch.mint).where(PumpLaunch.mint.in_(mints))).all())
            new = [r for r in {r["mint"]: r for r in launches}.values() if r["mint"] not in existing]
            if new:
                s.execute(insert(PumpLaunch), new)
            out["launches"] = len(new)
            s.flush()
        ups = rows.get("launch_updates") or []
        if ups:
            t = PumpLaunch.__table__
            cols = ("created_at", "slot", "signature", "creator", "name", "symbol", "uri", "mayhem", "token_program",
                    "quote_mint", "source")
            stmt = update(t).where(t.c.mint == bindparam("b_mint")).values(**{c: bindparam(f"b_{c}") for c in cols})
            s.execute(stmt, [{"b_mint": r["mint"], **{f"b_{c}": r[c] for c in cols}} for r in ups])
            out["launch_updates"] = len(ups)
        stats = rows.get("stats") or []
        if stats:
            t = PumpLaunch.__table__
            stmt = (update(t).where(t.c.mint == bindparam("b_mint"))
                    .values(stats=bindparam("b_stats"), complete_at=bindparam("b_complete")))
            s.execute(stmt, [{"b_mint": r["mint"], "b_stats": r["stats"], "b_complete": r["complete_at"]} for r in stats])
            out["stats"] = len(stats)
        trades = rows.get("trades") or []
        if trades:
            s.execute(insert(PumpTradeRow), trades)
            out["trades"] = len(trades)
        bars = rows.get("bars") or []
        if bars:
            pools = {b["mint"] for b in bars}
            lo, hi = min(b["ts"] for b in bars), max(b["ts"] for b in bars)
            have = set(s.execute(select(CandleRow.pool, CandleRow.ts).where(
                CandleRow.pool.in_(pools), CandleRow.timeframe == "1m", CandleRow.currency == STREAM_CURRENCY,
                CandleRow.ts >= lo, CandleRow.ts <= hi)).all())
            new_bars = [{"token_address": b["mint"], "pool": b["mint"], "timeframe": "1m", "currency": STREAM_CURRENCY,
                         "ts": b["ts"], "open": b["open"], "high": b["high"], "low": b["low"], "close": b["close"],
                         "volume": b["volume"], "source": "stream"}
                        for b in bars if (b["mint"], b["ts"]) not in have]
            if new_bars:
                s.execute(insert(CandleRow), new_bars)
            out["bars"] = len(new_bars)
        events = rows.get("events") or []
        if events:
            s.execute(insert(TokenEvent), events)
            out["events"] = len(events)
    return out


def _mini_snapshot(st: LaunchState, at: float, f: dict[str, Any]) -> TokenSnapshot:
    snap = TokenSnapshot(chain="solana", token_address=st.mint, observed_at=datetime.fromtimestamp(at, tz=timezone.utc),
                         symbol=st.symbol, name=st.name, dex_id="pumpfun", bonding_curve=True, deployer=st.creator,
                         created_at=datetime.fromtimestamp(st.created_ts, tz=timezone.utc))
    snap.mayhem = st.mayhem
    snap.price_native = f.get("price")
    return snap


def write_feature_snapshots(items: list[tuple[LaunchState, str, float]], tracker: LaunchTracker) -> int:
    if not items:
        return 0
    rows = []
    for st, horizon, at in items:
        f = curve_features(st, at, tracker)
        if horizon in EXTRA_HORIZONS and (f.get("n_trades", 0) < 5 or f.get("mayhem") or not f.get("quote_native", True)):
            continue  # extra decision points only where a trade could be considered at all
        snap = _mini_snapshot(st, at, f)
        dep = None
        try:
            dep = _deployer_cached(st, snap)
        except Exception:
            log.exception("deployer history failed")
        if dep is not None:
            f["deployer_launches_24h"] = dep["launches_24h"] if dep["observed_days"] >= 1 else None
            f["deployer_launches_30d"] = dep["launches_30d"]
            f["deployer_rug_share"] = dep["rug_share"]
            f["deployer_observed_days"] = dep["observed_days"]
        f["source"] = st.source
        r = risk_index(snap, f, None, dep)
        o = opportunity_index(snap, f, None)
        rows.append({"token_address": st.mint, "observed_at": snap.observed_at, "horizon": horizon,
                     "version": FEATURE_VERSION, "price": f.get("price"), "features": f,
                     "risk": {"value": r.value, "coverage": r.coverage, "shadow_hits": r.shadow_hits,
                              "blocking": r.blocking},
                     "opportunity": {"value": o.value, "coverage": o.coverage}})
    with session_scope() as s:
        keys = {(r["token_address"], r["horizon"]) for r in rows}
        have = set(s.execute(select(FeatureSnapshot.token_address, FeatureSnapshot.horizon).where(
            FeatureSnapshot.token_address.in_({k[0] for k in keys}))).all())
        new = [r for r in rows if (r["token_address"], r["horizon"]) not in have]
        if new:
            s.execute(insert(FeatureSnapshot), new)
    return len(new)


_DEP_CACHE: dict[str, tuple[float, Any]] = {}


def _deployer_cached(st: LaunchState, snap: TokenSnapshot) -> Any:
    """The creator's record changes slowly: one database query per launch every 15 minutes is enough."""
    import time as _t

    hit = _DEP_CACHE.get(st.mint)
    if hit is not None and _t.time() - hit[0] < 900:
        return hit[1]
    dep = deployer_history(st.creator, snap.created_at, exclude_mint=st.mint)
    if len(_DEP_CACHE) > 20_000:
        _DEP_CACHE.clear()
    _DEP_CACHE[st.mint] = (_t.time(), dep)
    return dep


def compute_labels(p0: float | None, observed_ts: int, bars: list[tuple[int, float, float, float]],
                   complete_at: datetime | None, created_at: datetime | None,
                   gaps: list[tuple[float, float]], window_min: int = LABEL_WINDOW_MIN) -> dict[str, Any]:
    """Outcome after the snapshot. ``bars`` = (ts, high, low, close) of the stream candles AFTER observed_ts."""
    end = observed_ts + window_min * 60
    cov = interval_coverage(observed_ts, end, gaps)
    incomplete = cov < MIN_COVERAGE
    lab: dict[str, Any] = {"window_min": window_min, "incomplete": incomplete, "stream_coverage": round(cov, 4),
                           "bars": len(bars)}
    if not p0 or p0 <= 0:
        lab["no_price"] = True
        return lab

    def ret(x: float) -> float:
        return round((x / p0 - 1) * 100, 2)

    for w in (5, 10, 60, window_min):
        sub = [b for b in bars if b[0] < observed_ts + w * 60]
        key = f"{w}m"
        if sub:
            lab[f"ret_max_{key}"] = ret(max(b[1] for b in sub))
            lab[f"ret_min_{key}"] = ret(min(b[2] for b in sub))
            lab[f"ret_end_{key}"] = ret(sub[-1][3])
        else:  # no trade at all: price unchanged but nobody traded (dead)
            lab[f"ret_max_{key}"] = lab[f"ret_min_{key}"] = lab[f"ret_end_{key}"] = 0.0
    first = "neither"
    for _ts, h, low, _c in bars:
        if low <= p0 * 0.5:  # conservative: inside one bar the fall is assumed to come first
            first = "half_first"
            break
        if h >= p0 * 2:
            first = "2x_first"
            break
    lab["first_passage"] = first
    lab["hit_2x_first"] = first == "2x_first"
    lab["rug_60m"] = lab["ret_min_60m"] <= -80.0
    lab["dead_60m"] = not any(observed_ts + 1800 <= b[0] < observed_ts + 3600 for b in bars)
    lab["active_after_60m"] = any(b[0] >= observed_ts + 3600 for b in bars)
    ca, cr = _aware(complete_at), _aware(created_at)
    lab["migrated_4h"] = bool(ca and cr and (ca - cr) <= timedelta(hours=4))
    return lab


def label_due(gaps: list[tuple[float, float]], batch: int = 400, now: datetime | None = None) -> int:
    now = now or utcnow()
    cutoff = now - timedelta(minutes=LABEL_WINDOW_MIN + 2)
    n = 0
    with session_scope() as s:
        rows = s.scalars(select(FeatureSnapshot).where(FeatureSnapshot.labels.is_(None),
                                                        FeatureSnapshot.observed_at <= cutoff)
                         .order_by(FeatureSnapshot.observed_at.asc()).limit(batch)).all()
        launches = {l.mint: l for l in s.scalars(select(PumpLaunch).where(
            PumpLaunch.mint.in_({r.token_address for r in rows}))).all()} if rows else {}
        for r in rows:
            ots = int(_aware(r.observed_at).timestamp())
            bars = s.execute(select(CandleRow.ts, CandleRow.high, CandleRow.low, CandleRow.close).where(
                CandleRow.pool == r.token_address, CandleRow.timeframe == "1m", CandleRow.currency == STREAM_CURRENCY,
                CandleRow.ts >= ots // 60 * 60 + 60, CandleRow.ts < ots + LABEL_WINDOW_MIN * 60)
                .order_by(CandleRow.ts.asc())).all()
            la = launches.get(r.token_address)
            r.labels = compute_labels(r.price, ots, [tuple(b) for b in bars], la.complete_at if la else None,
                                      la.created_at if la else None, gaps)
            r.labeled_at = now
            n += 1
    return n


def retention(now: datetime | None = None) -> dict[str, int]:
    """Tiered retention: raw early trades 3 days, stream candles 10 days, wallet profiles and journal events 30 days,
    launches and labelled feature snapshots 90 days (the research dataset)."""
    now = now or utcnow()
    out = {}
    with session_scope() as s:
        out["pump_trades"] = s.execute(delete(PumpTradeRow).where(PumpTradeRow.ts < now - timedelta(days=3))).rowcount
        out["stream_candles"] = s.execute(delete(CandleRow).where(
            CandleRow.source == "stream", CandleRow.ts < int((now - timedelta(days=10)).timestamp()))).rowcount
        out["wallet_profiles"] = s.execute(delete(WalletProfile).where(
            WalletProfile.checked_at < now - timedelta(days=30))).rowcount
        out["feature_snapshots"] = s.execute(delete(FeatureSnapshot).where(
            FeatureSnapshot.observed_at < now - timedelta(days=90))).rowcount
        out["feature_snapshots_extra"] = s.execute(delete(FeatureSnapshot).where(
            FeatureSnapshot.horizon.in_(sorted(EXTRA_HORIZONS)),
            FeatureSnapshot.observed_at < now - timedelta(days=21))).rowcount
        out["pump_launches"] = s.execute(delete(PumpLaunch).where(
            PumpLaunch.created_at < now - timedelta(days=90))).rowcount
        out["token_events"] = s.execute(delete(TokenEvent).where(TokenEvent.ts < now - timedelta(days=30))).rowcount
    return out


def recent_launch_names(days: int = 7, limit: int = 200_000) -> list[str | None]:
    with session_scope() as s:
        return list(s.scalars(select(PumpLaunch.name).where(PumpLaunch.created_at >= utcnow() - timedelta(days=days))
                              .order_by(PumpLaunch.created_at.asc()).limit(limit)).all())


def dataset_counts() -> dict[str, Any]:
    from sqlalchemy import func

    with session_scope() as s:
        def count(model, *where):
            q = select(func.count()).select_from(model)
            for w in where:
                q = q.where(w)
            return s.scalar(q) or 0

        return {
            "launches": count(PumpLaunch),
            "launches_24h": count(PumpLaunch, PumpLaunch.created_at >= utcnow() - timedelta(hours=24)),
            "early_trades": count(PumpTradeRow),
            "feature_snapshots": count(FeatureSnapshot),
            "labeled": count(FeatureSnapshot, FeatureSnapshot.labels.is_not(None)),
            "wallet_profiles": count(WalletProfile),
            "stream_candles": count(CandleRow, CandleRow.source == "stream"),
            "token_events": count(TokenEvent),
        }
