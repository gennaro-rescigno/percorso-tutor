"""Event study on the lifecycle journal: what tends to happen AFTER each kind of on-chain fact.

Descriptive only (no signal, no score). For every journal event of a classic (non-mayhem) launch the reference
price is the close of the minute in which the fact happened (what a bot could still get after seeing it), then the
stream candles of the next 60 minutes give the maximum, minimum and final move, plus whether the curve completed
(migration) in that hour. Windows in which the chain stream was down are excluded, never read as "no activity".
The same numbers for ordinary moments of the same age come from the feature snapshots (t+1m / t+5m / t+15m),
so each event can be compared with a baseline.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
from sqlalchemy import select

from mci.database.models import CandleRow, FeatureSnapshot, PumpLaunch, Token, TokenEvent, TokenSnapshotRow
from mci.database.session import session_scope
from mci.domain import utcnow
from mci.onchain.curve_features import MIN_COVERAGE
from mci.onchain.launches import interval_coverage
from mci.research.feature_store import STREAM_CURRENCY

WINDOW_MIN = 60
MAX_PER_KIND = 3000
MIN_GROUP = 30
CHUNK = 400


def _aware(d: datetime) -> datetime:
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def group_key(kind: str, value: float | None, detail: dict | None) -> str:
    detail = detail or {}
    if kind == "reserve":
        return f"riserva >= {value:g} SOL"
    if kind == "drawdown":
        return f"calo dal massimo >= {value:g}%"
    if kind == "dev_sell":
        return "il creatore vende tutto" if detail.get("sold_all") else "il creatore vende in parte"
    if kind == "dev_buy":
        return "primo acquisto del creatore" if detail.get("first") else "il creatore ricompra"
    if kind == "block0":
        n = value or 0
        return "blocco 0: nessun altro acquirente" if n == 0 else (
            "blocco 0: 1-2 acquirenti" if n <= 2 else "blocco 0: 3-5 acquirenti" if n <= 5 else "blocco 0: > 5 acquirenti")
    if kind == "copy":
        return "nome già usato (copia)"
    names = {"listed": "token quotato visto per la prima volta", "price_jump": "prezzo +50% tra due controlli",
             "price_drop": "prezzo -40% tra due controlli", "liquidity_drop": "liquidità -30% tra due controlli",
             "boost_on": "promozione DexScreener attivata", "migrated": "migrazione vista dallo scanner",
             "holders_jump": "holder +50% tra due controlli",
             "whale_buy": "acquisto >= 2 SOL", "whale_sell": "vendita >= 2 SOL", "wash_atomic": "wash trade atomico",
             "volume_spike": "picco di acquisti", "complete": "diploma (migrazione)", "dead": "30 minuti senza scambi",
             "create": "lancio"}
    return names.get(kind, kind)


def forward(p0: float, bars: list[tuple[int, float, float, float]]) -> tuple[float, float, float]:
    """(max, min, end) return in % over the bars after the event minute; no bar = nobody traded (0, 0, 0)."""
    if not bars:
        return 0.0, 0.0, 0.0
    hi = max(b[1] for b in bars)
    lo = min(b[2] for b in bars)
    return (hi / p0 - 1) * 100, (lo / p0 - 1) * 100, (bars[-1][3] / p0 - 1) * 100


def summarize(rows: list[tuple[float, float, float, bool, float]]) -> dict[str, Any]:
    a = np.array([r[:3] for r in rows], float)
    mig = np.array([r[3] for r in rows], bool)
    ages = np.array([r[4] for r in rows], float)
    return {"n": len(rows), "end_median_pct": round(float(np.median(a[:, 2])), 1),
            "end_mean_pct": round(float(np.mean(np.clip(a[:, 2], -100, 1000))), 1),
            "p_up_100": round(float((a[:, 0] >= 100).mean()), 3), "p_down_50": round(float((a[:, 1] <= -50).mean()), 3),
            "p_migrated": round(float(mig.mean()), 3), "age_median_min": round(float(np.median(ages)) / 60, 1)}


def _bars_by_token(s, tokens: list[str], lo: int, hi: int) -> dict[str, list[tuple[int, float, float, float]]]:
    out: dict[str, list] = defaultdict(list)
    for i in range(0, len(tokens), CHUNK):
        for pool, ts, h, low, c in s.execute(select(CandleRow.pool, CandleRow.ts, CandleRow.high, CandleRow.low,
                                                    CandleRow.close).where(
                CandleRow.pool.in_(tokens[i:i + CHUNK]), CandleRow.timeframe == "1m",
                CandleRow.currency == STREAM_CURRENCY, CandleRow.ts >= lo, CandleRow.ts <= hi)
                .order_by(CandleRow.ts.asc())):
            out[pool].append((ts, h, low, c))
    return out


def event_study(days: int = 7, gaps: list[tuple[float, float]] | None = None,
                now: datetime | None = None) -> dict[str, Any]:
    now = now or utcnow()
    gaps = gaps or []
    since, until = now - timedelta(days=days), now - timedelta(minutes=WINDOW_MIN + 2)
    with session_scope() as s:
        kinds = list(s.scalars(select(TokenEvent.kind).distinct()).all())
        events = []
        for k in kinds:
            events += s.execute(select(TokenEvent.token_address, TokenEvent.ts, TokenEvent.kind, TokenEvent.value,
                                       TokenEvent.price, TokenEvent.age_s, TokenEvent.detail).where(
                TokenEvent.kind == k, TokenEvent.ts >= since, TokenEvent.ts <= until, TokenEvent.source == "stream")
                .order_by(TokenEvent.ts.desc()).limit(MAX_PER_KIND)).all()
        tokens = sorted({e[0] for e in events})
        launches = {}
        for i in range(0, len(tokens), CHUNK):
            for mint, mayhem, complete_at, created_at in s.execute(select(
                    PumpLaunch.mint, PumpLaunch.mayhem, PumpLaunch.complete_at, PumpLaunch.created_at).where(
                    PumpLaunch.mint.in_(tokens[i:i + CHUNK]))):
                launches[mint] = (mayhem, complete_at and _aware(complete_at), created_at and _aware(created_at))
        tokens = [t for t in tokens if t in launches and not launches[t][0]]
        bars = _bars_by_token(s, tokens, int(since.timestamp()) - 60, int(now.timestamp()))
        base = baseline(s, since, until, gaps)
        listed = listed_study(s, since, until)

    groups: dict[str, list] = defaultdict(list)
    skipped = {"mayhem_or_unknown": 0, "stream_gap": 0, "no_price": 0}
    for mint, ts, kind, value, price, age, detail in events:
        if mint not in launches or launches[mint][0]:
            skipped["mayhem_or_unknown"] += 1
            continue
        ets = int(_aware(ts).timestamp())
        if interval_coverage(ets, ets + WINDOW_MIN * 60, gaps) < MIN_COVERAGE:
            skipped["stream_gap"] += 1
            continue
        tb = bars.get(mint, [])
        minute = ets // 60 * 60
        cur = [b for b in tb if b[0] == minute]
        p0 = cur[0][3] if cur else price
        if not p0 or p0 <= 0:
            skipped["no_price"] += 1
            continue
        after = [b for b in tb if minute < b[0] < ets + WINDOW_MIN * 60]
        mx, mn, end = forward(p0, after)
        ca = launches[mint][1]
        migrated = bool(ca and _aware(ts) < ca <= _aware(ts) + timedelta(minutes=WINDOW_MIN))
        groups[group_key(kind, value, detail)].append((mx, mn, end, migrated, age or 0.0))

    table = []
    for key, rows in groups.items():
        if kind_of(key) == "complete" or len(rows) < MIN_GROUP:
            continue  # after the migration the curve candles stop: a pool study is needed (not yet available)
        st = summarize(rows)
        st["event"] = key
        st["baseline"] = "t+1m" if st["age_median_min"] < 3 else "t+5m" if st["age_median_min"] < 10 else "t+15m"
        table.append(st)
    table.sort(key=lambda r: -r["n"])
    return {"generated_at": now.isoformat(), "days": days, "window_min": WINDOW_MIN, "events": table, "listed": listed,
            "baseline": base, "skipped": skipped, "small_groups": sorted(k for k, v in groups.items() if len(v) < MIN_GROUP),
            "note": "Studio descrittivo: cosa è successo nei 60 minuti DOPO ogni fatto, dal prezzo di chiusura del minuto "
                    "in cui è avvenuto. Non è una previsione e non include i costi; serve a capire, non a comprare."}


def kind_of(key: str) -> str:
    return "complete" if key.startswith("diploma") else key


def baseline(s, since: datetime, until: datetime, gaps: list[tuple[float, float]]) -> dict[str, Any]:
    """Same statistics for ordinary moments: the labelled feature snapshots of non-mayhem launches."""
    out = {}
    for h in ("t+1m", "t+5m", "t+15m"):
        rows = s.execute(select(FeatureSnapshot.labels, FeatureSnapshot.features, FeatureSnapshot.observed_at,
                                FeatureSnapshot.token_address).where(
            FeatureSnapshot.horizon == h, FeatureSnapshot.observed_at >= since, FeatureSnapshot.observed_at <= until,
            FeatureSnapshot.labels.is_not(None)).order_by(FeatureSnapshot.observed_at.desc()).limit(MAX_PER_KIND * 3)).all()
        mints = list({r[3] for r in rows})
        comp = {}
        for i in range(0, len(mints), CHUNK):
            comp.update({m: c for m, c in s.execute(select(PumpLaunch.mint, PumpLaunch.complete_at).where(
                PumpLaunch.mint.in_(mints[i:i + CHUNK])))})
        vals = []
        for lab, feat, at, mint in rows:
            if not lab or lab.get("incomplete") or lab.get("no_price") or (feat or {}).get("mayhem"):
                continue
            if "ret_end_60m" not in lab:
                continue
            ca = comp.get(mint)
            mig = bool(ca and _aware(at) < _aware(ca) <= _aware(at) + timedelta(minutes=WINDOW_MIN))
            vals.append((lab["ret_max_60m"], lab["ret_min_60m"], lab["ret_end_60m"], mig, (feat or {}).get("age_s") or 0))
        if len(vals) >= MIN_GROUP:
            out[h] = summarize(vals)
    return out


def listed_study(s, since: datetime, until: datetime) -> list[dict[str, Any]]:
    """Same question for tokens followed on a DEX: price path from the scanner's own snapshots after the fact."""
    rows = s.execute(select(TokenEvent.token_address, TokenEvent.ts, TokenEvent.kind, TokenEvent.value,
                            TokenEvent.price, TokenEvent.age_s, TokenEvent.detail).where(
        TokenEvent.source == "scanner", TokenEvent.ts >= since, TokenEvent.ts <= until, TokenEvent.price.is_not(None))
        .order_by(TokenEvent.ts.desc()).limit(MAX_PER_KIND * 3)).all()
    if not rows:
        return []
    addrs = sorted({r[0] for r in rows})
    ids = {}
    for i in range(0, len(addrs), CHUNK):
        ids.update({a: t for a, t in s.execute(select(Token.address, Token.id).where(Token.address.in_(addrs[i:i + CHUNK])))})
    hist: dict[int, list[tuple[datetime, float]]] = defaultdict(list)
    tids = sorted(set(ids.values()))
    for i in range(0, len(tids), CHUNK):
        for tid, at, p in s.execute(select(TokenSnapshotRow.token_id, TokenSnapshotRow.observed_at,
                                           TokenSnapshotRow.price_native).where(
                TokenSnapshotRow.token_id.in_(tids[i:i + CHUNK]), TokenSnapshotRow.observed_at >= since,
                TokenSnapshotRow.price_native.is_not(None)).order_by(TokenSnapshotRow.observed_at.asc())):
            hist[tid].append((_aware(at), p))
    groups: dict[str, list] = defaultdict(list)
    for addr, ts, kind, value, price, age, detail in rows:
        tid = ids.get(addr)
        t0 = _aware(ts)
        after = [p for at, p in hist.get(tid, []) if t0 < at <= t0 + timedelta(minutes=WINDOW_MIN)]
        if not after or not price or price <= 0:
            continue  # no later observation: nothing can be said (never read as "no movement")
        mx, mn, end = (max(after) / price - 1) * 100, (min(after) / price - 1) * 100, (after[-1] / price - 1) * 100
        groups[group_key(kind, value, detail)].append((mx, mn, end, False, age or 0.0))
    out = []
    for key, g in groups.items():
        if len(g) >= MIN_GROUP:
            st = summarize(g)
            st.pop("p_migrated", None)
            st["event"] = key
            out.append(st)
    out.sort(key=lambda r: -r["n"])
    return out
