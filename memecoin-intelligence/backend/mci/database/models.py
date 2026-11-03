"""SQLAlchemy ORM models.

Signals, simulated orders and real orders are separate concepts:
* ``signals``  - what a strategy proposed (with the data available at that moment);
* ``orders``   - an order the system decided to place, with ``mode`` = paper | live;
* ``fills``    - what was actually executed (simulated for paper, on-chain for live).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from mci.domain import utcnow


class Base(DeclarativeBase):
    type_annotation_map = {dict: JSON, list: JSON}


class Token(Base):
    __tablename__ = "tokens"
    __table_args__ = (UniqueConstraint("chain", "address", name="uq_token_chain_address"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chain: Mapped[str] = mapped_column(String(16), default="solana")
    address: Mapped[str] = mapped_column(String(64), index=True)
    symbol: Mapped[str | None] = mapped_column(String(64))
    name: Mapped[str | None] = mapped_column(String(128))
    pair_address: Mapped[str | None] = mapped_column(String(64))
    dex_id: Mapped[str | None] = mapped_column(String(32))
    deployer: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    first_seen_source: Mapped[str | None] = mapped_column(String(32))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    status: Mapped[str] = mapped_column(String(16), default="tracking")  # tracking|excluded|dead|archived
    last_score: Mapped[float | None] = mapped_column(Float)
    last_label: Mapped[str | None] = mapped_column(String(32))
    last_price_usd: Mapped[float | None] = mapped_column(Float)
    last_price_native: Mapped[float | None] = mapped_column(Float)
    last_liquidity_usd: Mapped[float | None] = mapped_column(Float)
    last_mcap_usd: Mapped[float | None] = mapped_column(Float)
    last_volume_h1: Mapped[float | None] = mapped_column(Float)
    last_volume_h24: Mapped[float | None] = mapped_column(Float)
    last_change_h1: Mapped[float | None] = mapped_column(Float)
    last_holders: Mapped[int | None] = mapped_column(Integer)
    last_risk_level: Mapped[str | None] = mapped_column(String(16))
    last_signal: Mapped[str | None] = mapped_column(String(64))
    last_snapshot: Mapped[dict | None] = mapped_column(JSON)
    last_score_detail: Mapped[dict | None] = mapped_column(JSON)


class TokenSnapshotRow(Base):
    __tablename__ = "token_snapshots"
    __table_args__ = (Index("ix_snap_token_time", "token_id", "observed_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_id: Mapped[int] = mapped_column(ForeignKey("tokens.id", ondelete="CASCADE"))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    price_usd: Mapped[float | None] = mapped_column(Float)
    price_native: Mapped[float | None] = mapped_column(Float)
    liquidity_usd: Mapped[float | None] = mapped_column(Float)
    market_cap_usd: Mapped[float | None] = mapped_column(Float)
    volume_h1: Mapped[float | None] = mapped_column(Float)
    holders: Mapped[int | None] = mapped_column(Integer)
    score: Mapped[float | None] = mapped_column(Float)
    excluded: Mapped[bool] = mapped_column(Boolean, default=False)
    data: Mapped[dict] = mapped_column(JSON)  # full TokenSnapshot (point-in-time)


class CandleRow(Base):
    __tablename__ = "candles"
    __table_args__ = (UniqueConstraint("pool", "timeframe", "ts", "currency", name="uq_candle"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_address: Mapped[str] = mapped_column(String(64), index=True)
    pool: Mapped[str] = mapped_column(String(64), index=True)
    timeframe: Mapped[str] = mapped_column(String(8))
    currency: Mapped[str] = mapped_column(String(8), default="token")  # token=SOL quote, usd
    ts: Mapped[int] = mapped_column(Integer, index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(16), default="geckoterminal")


class SignalRow(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    token_address: Mapped[str] = mapped_column(String(64), index=True)
    symbol: Mapped[str | None] = mapped_column(String(64))
    strategy: Mapped[str] = mapped_column(String(4))
    mode: Mapped[str] = mapped_column(String(8))
    score: Mapped[float] = mapped_column(Float)
    reference_price: Mapped[float] = mapped_column(Float)
    stop_price: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(24), default="generated")  # generated|accepted|rejected|executed|failed
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    risks: Mapped[list] = mapped_column(JSON, default=list)
    features: Mapped[dict] = mapped_column(JSON, default=dict)
    snapshot: Mapped[dict | None] = mapped_column(JSON)  # data available when the signal was generated
    score_detail: Mapped[dict | None] = mapped_column(JSON)
    # outcome tracking (Fase 14), filled later
    price_15m: Mapped[float | None] = mapped_column(Float)
    price_1h: Mapped[float | None] = mapped_column(Float)
    price_4h: Mapped[float | None] = mapped_column(Float)
    price_24h: Mapped[float | None] = mapped_column(Float)
    max_gain_24h: Mapped[float | None] = mapped_column(Float)
    max_drawdown_24h: Mapped[float | None] = mapped_column(Float)
    outcome_done: Mapped[bool] = mapped_column(Boolean, default=False)


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mode: Mapped[str] = mapped_column(String(8), index=True)
    token_address: Mapped[str] = mapped_column(String(64), index=True)
    symbol: Mapped[str | None] = mapped_column(String(64))
    pair_address: Mapped[str | None] = mapped_column(String(64))
    dex_id: Mapped[str | None] = mapped_column(String(32))
    strategy: Mapped[str] = mapped_column(String(4))
    signal_id: Mapped[int | None] = mapped_column(ForeignKey("signals.id"))
    status: Mapped[str] = mapped_column(String(12), default="open", index=True)  # open|closed
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    entry_price: Mapped[float] = mapped_column(Float)  # SOL per token
    qty_initial: Mapped[float] = mapped_column(Float)
    qty: Mapped[float] = mapped_column(Float)
    token_decimals: Mapped[int | None] = mapped_column(Integer)
    stake_sol: Mapped[float] = mapped_column(Float)
    cost_sol: Mapped[float] = mapped_column(Float)
    proceeds_sol: Mapped[float] = mapped_column(Float, default=0.0)
    stop_price: Mapped[float] = mapped_column(Float)
    initial_stop: Mapped[float] = mapped_column(Float)
    take_profits: Mapped[list] = mapped_column(JSON, default=list)
    last_price: Mapped[float | None] = mapped_column(Float)
    fees_sol: Mapped[float] = mapped_column(Float, default=0.0)
    slippage_sol: Mapped[float] = mapped_column(Float, default=0.0)
    realized_pnl_sol: Mapped[float | None] = mapped_column(Float)
    exit_reason: Mapped[str | None] = mapped_column(Text)
    state: Mapped[dict] = mapped_column(JSON, default=dict)  # PositionState for exit engine
    score: Mapped[float | None] = mapped_column(Float)

    orders: Mapped[list["Order"]] = relationship(back_populates="position")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_order_id: Mapped[str] = mapped_column(String(64), unique=True)  # idempotency key
    mode: Mapped[str] = mapped_column(String(8), index=True)  # paper|live
    side: Mapped[str] = mapped_column(String(4))
    token_address: Mapped[str] = mapped_column(String(64), index=True)
    position_id: Mapped[int | None] = mapped_column(ForeignKey("positions.id"))
    signal_id: Mapped[int | None] = mapped_column(ForeignKey("signals.id"))
    status: Mapped[str] = mapped_column(String(16), default="created")  # created|submitted|filled|failed|cancelled
    requested_sol: Mapped[float | None] = mapped_column(Float)
    requested_qty: Mapped[float | None] = mapped_column(Float)
    reason: Mapped[str | None] = mapped_column(Text)
    quote: Mapped[dict | None] = mapped_column(JSON)
    tx_signature: Mapped[str | None] = mapped_column(String(128))
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    position: Mapped[Position | None] = relationship(back_populates="orders")
    fills: Mapped[list["FillRow"]] = relationship(back_populates="order")


class FillRow(Base):
    __tablename__ = "fills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    side: Mapped[str] = mapped_column(String(4))
    qty: Mapped[float] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float)
    sol_amount: Mapped[float] = mapped_column(Float)
    dex_fee_sol: Mapped[float] = mapped_column(Float)
    network_fee_sol: Mapped[float] = mapped_column(Float)
    rent_sol: Mapped[float] = mapped_column(Float, default=0.0)
    slippage_sol: Mapped[float] = mapped_column(Float)
    price_impact_pct: Mapped[float] = mapped_column(Float)
    quote_source: Mapped[str] = mapped_column(String(16))

    order: Mapped[Order] = relationship(back_populates="fills")


class EquitySnapshot(Base):
    __tablename__ = "equity_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    mode: Mapped[str] = mapped_column(String(8))
    equity_sol: Mapped[float] = mapped_column(Float)
    cash_sol: Mapped[float] = mapped_column(Float)
    exposure_sol: Mapped[float] = mapped_column(Float)
    drawdown_pct: Mapped[float] = mapped_column(Float)
    sol_eur: Mapped[float | None] = mapped_column(Float)
    sol_usd: Mapped[float | None] = mapped_column(Float)


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    level: Mapped[str] = mapped_column(String(8), default="info")
    category: Mapped[str] = mapped_column(String(24), index=True)  # scan|signal|order|trade|error|param|alert|system|risk
    message: Mapped[str] = mapped_column(Text)
    token_address: Mapped[str | None] = mapped_column(String(64))
    data: Mapped[dict | None] = mapped_column(JSON)


class SystemState(Base):
    __tablename__ = "system_state"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    name: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(16), default="queued")  # queued|running|done|failed
    config: Mapped[dict] = mapped_column(JSON)
    metrics: Mapped[dict | None] = mapped_column(JSON)
    equity_curve: Mapped[list | None] = mapped_column(JSON)
    trades: Mapped[list | None] = mapped_column(JSON)
    data_info: Mapped[dict | None] = mapped_column(JSON)
    warnings: Mapped[list | None] = mapped_column(JSON)
    report_md: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)


class AlertLog(Base):
    __tablename__ = "alert_log"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    last_sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ----------------------------------------------------------------------------- on-chain data collection (free)
class PumpLaunch(Base):
    """Every pump.fun launch seen on the public chain stream (or PumpPortal when the stream is down)."""

    __tablename__ = "pump_launches"

    mint: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    slot: Mapped[int | None] = mapped_column(BigInteger)
    signature: Mapped[str | None] = mapped_column(String(100))
    creator: Mapped[str | None] = mapped_column(String(64), index=True)
    name: Mapped[str | None] = mapped_column(String(128))
    symbol: Mapped[str | None] = mapped_column(String(64))
    uri: Mapped[str | None] = mapped_column(String(300))
    mayhem: Mapped[bool | None] = mapped_column(Boolean)
    token_program: Mapped[str | None] = mapped_column(String(64))
    quote_mint: Mapped[str | None] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(String(16), default="stream")
    complete_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stats: Mapped[dict | None] = mapped_column(JSON)  # trades, buyers, volume, peak price... (updated)


class PumpTradeRow(Base):
    """Early trades of each launch (first minutes), decoded from the official pump.fun TradeEvent."""

    __tablename__ = "pump_trades"
    __table_args__ = (Index("ix_pump_trades_mint_ts", "mint", "ts"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mint: Mapped[str] = mapped_column(String(64))
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    slot: Mapped[int | None] = mapped_column(BigInteger)
    signature: Mapped[str | None] = mapped_column(String(100))
    wallet: Mapped[str] = mapped_column(String(64), index=True)
    is_buy: Mapped[bool] = mapped_column(Boolean)
    sol_lamports: Mapped[int] = mapped_column(BigInteger)
    token_amount: Mapped[int] = mapped_column(BigInteger)
    v_sol: Mapped[int | None] = mapped_column(BigInteger)
    v_tokens: Mapped[int | None] = mapped_column(BigInteger)
    mayhem: Mapped[bool | None] = mapped_column(Boolean)


class WalletProfile(Base):
    """What the bot learned about a wallet from public RPC data (cached; facts only)."""

    __tablename__ = "wallet_profiles"

    address: Mapped[str] = mapped_column(String(64), primary_key=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    n_signatures: Mapped[int | None] = mapped_column(Integer)  # capped at the page size
    history_capped: Mapped[bool | None] = mapped_column(Boolean)  # True: older history not fetched
    first_tx_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    funder: Mapped[str | None] = mapped_column(String(64), index=True)
    funded_lamports: Mapped[int | None] = mapped_column(BigInteger)
    funded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_hub: Mapped[bool | None] = mapped_column(Boolean)  # very high activity: exchange / service
    data: Mapped[dict | None] = mapped_column(JSON)


class FeatureSnapshot(Base):
    """Point-in-time feature store: only data available at ``observed_at`` (no look-ahead)."""

    __tablename__ = "feature_snapshots"
    __table_args__ = (UniqueConstraint("token_address", "horizon", name="uq_feature_token_horizon"),
                      Index("ix_feature_time", "observed_at"))

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_address: Mapped[str] = mapped_column(String(64), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    horizon: Mapped[str] = mapped_column(String(16))  # t+1m | t+5m | t+15m (since launch)
    version: Mapped[int] = mapped_column(Integer, default=1)
    price: Mapped[float | None] = mapped_column(Float)  # SOL per token at observed_at
    features: Mapped[dict] = mapped_column(JSON)
    risk: Mapped[dict | None] = mapped_column(JSON)
    opportunity: Mapped[dict | None] = mapped_column(JSON)
    labels: Mapped[dict | None] = mapped_column(JSON)  # filled later by the labeler (future outcome)
    labeled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
