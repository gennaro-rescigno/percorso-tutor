"""Repository helpers (all DB access of the worker goes through here)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mci.database.models import (
    AlertLog,
    CandleRow,
    EquitySnapshot,
    Event,
    FillRow,
    Order,
    Position,
    SignalRow,
    SystemState,
    Token,
    TokenSnapshotRow,
)
from mci.domain import Candle, Fill, ScoreResult, Signal, TokenSnapshot, to_utc, utcnow

log = logging.getLogger(__name__)


# ----------------------------------------------------------------------------- state
def get_state(s: Session, key: str, default: Any = None) -> Any:
    row = s.get(SystemState, key)
    return row.value.get("v") if row else default


def set_state(s: Session, key: str, value: Any) -> None:
    row = s.get(SystemState, key)
    if row is None:
        s.add(SystemState(key=key, value={"v": value}))
    else:
        row.value = {"v": value}
        row.updated_at = utcnow()


def log_event(s: Session, category: str, message: str, *, level: str = "info", token: str | None = None,
              data: dict | None = None) -> None:
    s.add(Event(category=category, message=message[:4000], level=level, token_address=token, data=data))
    getattr(log, "warning" if level == "warn" else level if level in ("info", "error", "debug") else "info")(
        "[%s] %s", category, message[:300]
    )


# ----------------------------------------------------------------------------- tokens
def upsert_token(s: Session, snap: TokenSnapshot, source: str, score: ScoreResult | None = None) -> Token:
    tok = s.scalar(select(Token).where(Token.chain == snap.chain, Token.address == snap.token_address))
    now = to_utc(snap.observed_at) or utcnow()
    if tok is None:
        tok = Token(chain=snap.chain, address=snap.token_address, first_seen_at=now, first_seen_source=source)
        s.add(tok)
    tok.symbol = snap.symbol or tok.symbol
    tok.name = snap.name or tok.name
    tok.pair_address = snap.pair_address or tok.pair_address
    tok.dex_id = snap.dex_id or tok.dex_id
    tok.deployer = snap.deployer or tok.deployer
    tok.created_at = snap.created_at or tok.created_at
    tok.last_seen_at = now
    tok.last_price_usd = snap.price_usd if snap.price_usd is not None else tok.last_price_usd
    tok.last_price_native = snap.price_native if snap.price_native is not None else tok.last_price_native
    tok.last_liquidity_usd = snap.liquidity_usd if snap.liquidity_usd is not None else tok.last_liquidity_usd
    tok.last_mcap_usd = snap.market_cap_usd or snap.fdv_usd or tok.last_mcap_usd
    tok.last_volume_h1 = snap.vol("h1") if snap.vol("h1") is not None else tok.last_volume_h1
    tok.last_volume_h24 = snap.vol("h24") if snap.vol("h24") is not None else tok.last_volume_h24
    tok.last_change_h1 = snap.price_change_pct.get("h1")
    tok.last_holders = snap.holders_count if snap.holders_count is not None else tok.last_holders
    tok.last_snapshot = snap.to_dict()
    if score is not None:
        tok.last_score = score.total
        tok.last_label = score.label
        tok.last_score_detail = score.to_dict()
        tok.last_risk_level = "alto" if score.excluded or len(score.risks) >= 3 else "medio" if score.risks else "basso"
        tok.status = "excluded" if score.excluded else "tracking"
    s.flush()
    return tok


def add_snapshot(s: Session, tok: Token, snap: TokenSnapshot, score: ScoreResult | None) -> None:
    s.add(
        TokenSnapshotRow(
            token_id=tok.id,
            observed_at=to_utc(snap.observed_at),
            price_usd=snap.price_usd,
            price_native=snap.price_native,
            liquidity_usd=snap.liquidity_usd,
            market_cap_usd=snap.market_cap_usd or snap.fdv_usd,
            volume_h1=snap.vol("h1"),
            holders=snap.holders_count,
            score=score.total if score else None,
            excluded=bool(score and score.excluded),
            data=snap.to_dict(),
        )
    )


def snapshot_history(s: Session, token_address: str, since: datetime, limit: int = 500) -> list[TokenSnapshot]:
    tok = s.scalar(select(Token).where(Token.address == token_address))
    if not tok:
        return []
    rows = s.scalars(
        select(TokenSnapshotRow)
        .where(TokenSnapshotRow.token_id == tok.id, TokenSnapshotRow.observed_at >= since)
        .order_by(TokenSnapshotRow.observed_at.asc())
        .limit(limit)
    ).all()
    return [TokenSnapshot.from_dict(r.data) for r in rows]


# ----------------------------------------------------------------------------- candles
def upsert_candles(s: Session, token: str, pool: str, timeframe: str, candles: list[Candle],
                   currency: str = "token", source: str = "geckoterminal") -> int:
    if not candles:
        return 0
    existing = set(
        s.scalars(
            select(CandleRow.ts).where(
                CandleRow.pool == pool, CandleRow.timeframe == timeframe, CandleRow.currency == currency,
                CandleRow.ts >= candles[0].ts, CandleRow.ts <= candles[-1].ts,
            )
        ).all()
    )
    n = 0
    for c in candles:
        if c.ts in existing:
            continue
        s.add(CandleRow(token_address=token, pool=pool, timeframe=timeframe, currency=currency, ts=c.ts,
                        open=c.open, high=c.high, low=c.low, close=c.close, volume=c.volume, source=source))
        n += 1
    return n


def load_candles(s: Session, pool: str, timeframe: str, currency: str = "token", since_ts: int = 0) -> list[Candle]:
    rows = s.scalars(
        select(CandleRow)
        .where(CandleRow.pool == pool, CandleRow.timeframe == timeframe, CandleRow.currency == currency,
               CandleRow.ts >= since_ts)
        .order_by(CandleRow.ts.asc())
    ).all()
    return [Candle(r.ts, r.open, r.high, r.low, r.close, r.volume) for r in rows]


# ----------------------------------------------------------------------------- signals / orders
def record_signal(s: Session, sig: Signal, mode: str, snap: TokenSnapshot | None, score: ScoreResult | None) -> SignalRow:
    row = SignalRow(
        created_at=sig.created_at, token_address=sig.token_address, symbol=sig.symbol, strategy=sig.strategy,
        mode=mode, score=sig.score, reference_price=sig.reference_price, stop_price=sig.stop_price,
        reasons=sig.reasons, risks=sig.risks, features=_jsonable(sig.features),
        snapshot=snap.to_dict() if snap else None, score_detail=score.to_dict() if score else None,
    )
    s.add(row)
    s.flush()
    return row


def _jsonable(d: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for k, v in d.items():
        if isinstance(v, (int, float, str, bool)) or v is None:
            out[k] = v
        else:
            out[k] = str(v)
    return out


def find_order(s: Session, client_order_id: str) -> Order | None:
    return s.scalar(select(Order).where(Order.client_order_id == client_order_id))


def add_fill(s: Session, order: Order, f: Fill) -> FillRow:
    row = FillRow(
        order_id=order.id, ts=f.ts, side=f.side, qty=f.qty, price=f.price, sol_amount=f.sol_amount,
        dex_fee_sol=f.dex_fee_sol, network_fee_sol=f.network_fee_sol, rent_sol=f.rent_sol,
        slippage_sol=f.slippage_sol, price_impact_pct=f.price_impact_pct, quote_source=f.quote_source,
    )
    s.add(row)
    return row


def open_positions(s: Session, mode: str) -> list[Position]:
    return list(s.scalars(select(Position).where(Position.mode == mode, Position.status == "open")).all())


def closed_positions(s: Session, mode: str, since: datetime | None = None) -> list[Position]:
    q = select(Position).where(Position.mode == mode, Position.status == "closed")
    if since:
        q = q.where(Position.closed_at >= since)
    return list(s.scalars(q.order_by(Position.closed_at.asc())).all())


def add_equity_snapshot(s: Session, mode: str, equity: float, cash: float, exposure: float, dd: float,
                        sol_eur: float | None, sol_usd: float | None) -> None:
    s.add(EquitySnapshot(mode=mode, equity_sol=equity, cash_sol=cash, exposure_sol=exposure, drawdown_pct=dd,
                         sol_eur=sol_eur, sol_usd=sol_usd))


# ----------------------------------------------------------------------------- alerts dedupe
def should_alert(s: Session, key: str, cooldown_minutes: int) -> bool:
    row = s.get(AlertLog, key)
    now = utcnow()
    if row and to_utc(row.last_sent_at) > now - timedelta(minutes=cooldown_minutes):
        return False
    if row is None:
        s.add(AlertLog(key=key, last_sent_at=now))
    else:
        row.last_sent_at = now
    return True


def count_tokens(s: Session) -> int:
    return s.scalar(select(func.count(Token.id))) or 0
