"""Domain objects shared by scanner, scoring, strategies, backtester and paper engine.

Design rule: a field that a source did not provide stays ``None``. Nothing downstream
is allowed to treat ``None`` as a favourable value.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

WINDOWS = ("m5", "m15", "h1", "h6", "h24")
WINDOW_MINUTES = {"m5": 5, "m15": 15, "m30": 30, "h1": 60, "h6": 360, "h24": 1440}

SOL_MINT = "So11111111111111111111111111111111111111112"
LAMPORTS_PER_SOL = 1_000_000_000


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def to_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def is_num(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(float(x))


class TradingMode(str, Enum):
    PAPER = "paper"
    LIVE = "live"
    BACKTEST = "backtest"


@dataclass
class Candle:
    ts: int  # epoch seconds, candle open time
    open: float
    high: float
    low: float
    close: float
    volume: float  # quote-currency (USD) volume

    def is_valid(self) -> bool:
        vals = (self.open, self.high, self.low, self.close)
        if not all(is_num(v) and v > 0 for v in vals):
            return False
        if not is_num(self.volume) or self.volume < 0:
            return False
        return self.low <= min(self.open, self.close) and self.high >= max(self.open, self.close)


@dataclass
class TokenSnapshot:
    """Point-in-time view of a token. Every field is optional except identity + time."""

    chain: str
    token_address: str
    observed_at: datetime
    symbol: str | None = None
    name: str | None = None
    pair_address: str | None = None
    dex_id: str | None = None
    quote_symbol: str | None = None
    created_at: datetime | None = None
    deployer: str | None = None

    # market
    price_usd: float | None = None
    price_native: float | None = None  # price in quote token (SOL when quote is SOL)
    market_cap_usd: float | None = None
    fdv_usd: float | None = None
    liquidity_usd: float | None = None
    liquidity_quote: float | None = None  # quote-side reserve (SOL) if known
    volume_usd: dict[str, float | None] = field(default_factory=dict)
    buys: dict[str, int | None] = field(default_factory=dict)
    sells: dict[str, int | None] = field(default_factory=dict)
    buyers: dict[str, int | None] = field(default_factory=dict)  # unique wallets
    sellers: dict[str, int | None] = field(default_factory=dict)
    price_change_pct: dict[str, float | None] = field(default_factory=dict)

    # on-chain / holders
    holders_count: int | None = None
    top1_pct: float | None = None
    top10_pct: float | None = None  # excluding pools / bonding curve / burn
    dev_pct: float | None = None
    insider_cluster_pct: float | None = None
    early_buyer_cluster_pct: float | None = None
    deployer_token_count: int | None = None

    # security
    mint_authority_revoked: bool | None = None
    freeze_authority_revoked: bool | None = None
    token_program: str | None = None
    dangerous_extensions: list[str] = field(default_factory=list)
    lp_locked_pct: float | None = None
    rugcheck_score_norm: float | None = None  # 0 (good) .. 100 (bad)
    rugcheck_risks: list[dict[str, Any]] = field(default_factory=list)
    rugged_flag: bool | None = None
    # own on-chain checks (mci.chain.tokens): [{code, severity, message, blocking}]
    onchain_findings: list[dict[str, Any]] = field(default_factory=list)
    metadata_mutable: bool | None = None
    mayhem: bool | None = None  # pump.fun "mayhem mode" curve (agent-driven price, not organic)

    # executability (from real quotes)
    sell_route_ok: bool | None = None
    sell_impact_pct: float | None = None
    buy_impact_pct: float | None = None
    quote_probe_sol: float | None = None
    sell_sim_ok: bool | None = None  # on-chain simulation of a real holder's sell (None = not verified)
    sell_sim_detail: str | None = None

    # market quality
    wash_score: float | None = None  # 0 (clean) .. 1 (wash trading)
    trades_per_trader: float | None = None
    price_divergence_pct: float | None = None  # |dexscreener - jupiter| / jupiter

    # pump.fun bonding curve
    bonding_curve: bool | None = None
    bonding_progress_pct: float | None = None
    v_sol_in_curve: float | None = None
    migrated_at: datetime | None = None

    # social
    socials: dict[str, str] = field(default_factory=dict)
    has_profile: bool | None = None
    boosts_active: int | None = None
    social_metrics: dict[str, Any] = field(default_factory=dict)

    # on-chain intelligence from the free chain stream + RPC: {"curve": features, "wallets": analysis,
    # "deployer": history, "risk": index, "opportunity": index}
    onchain: dict[str, Any] = field(default_factory=dict)

    sources: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    # ----------------------------------------------------------------------------
    @property
    def age_minutes(self) -> float | None:
        if self.created_at is None:
            return None
        return max(0.0, (to_utc(self.observed_at) - to_utc(self.created_at)).total_seconds() / 60.0)

    def vol(self, w: str) -> float | None:
        v = self.volume_usd.get(w)
        return float(v) if is_num(v) else None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        for k in ("observed_at", "created_at", "migrated_at"):
            if d.get(k) is not None:
                d[k] = to_utc(d[k]).isoformat()
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TokenSnapshot":
        d = dict(d)
        for k in ("observed_at", "created_at", "migrated_at"):
            if d.get(k):
                d[k] = to_utc(datetime.fromisoformat(d[k]))
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})

    def merge(self, other: "TokenSnapshot") -> "TokenSnapshot":
        """Fill missing fields of self with values from other (self wins when both present)."""
        for fname in self.__dataclass_fields__:
            mine = getattr(self, fname)
            theirs = getattr(other, fname)
            if isinstance(mine, dict):
                merged = dict(theirs or {})
                merged.update({k: v for k, v in mine.items() if v is not None})
                setattr(self, fname, merged)
            elif isinstance(mine, list):
                if not mine and theirs:
                    setattr(self, fname, list(theirs))
            elif mine is None and theirs is not None:
                setattr(self, fname, theirs)
        return self


@dataclass
class ExitPlan:
    stop_price: float
    take_profits: list[tuple[float, float]]  # (price, fraction of initial qty)
    trailing_activation_price: float | None
    trailing_pct: float | None
    max_hold_minutes: int


@dataclass
class Signal:
    strategy: str
    token_address: str
    symbol: str | None
    created_at: datetime
    reference_price: float  # in SOL per token
    stop_price: float
    score: float
    reasons: list[str]
    risks: list[str]
    features: dict[str, Any] = field(default_factory=dict)
    reduced_features: bool = False
    side: str = "buy"
    pair_address: str | None = None
    dex_id: str | None = None

    @property
    def stop_distance_pct(self) -> float:
        if self.reference_price <= 0:
            return 1.0
        return max(0.0, (self.reference_price - self.stop_price) / self.reference_price)


@dataclass
class Fill:
    side: str  # buy | sell
    qty: float  # tokens
    price: float  # SOL per token, effective (after impact, before network fees)
    sol_amount: float  # SOL paid (buy) or received (sell), excl. network fees
    dex_fee_sol: float
    network_fee_sol: float
    slippage_sol: float  # vs reference/mid price
    price_impact_pct: float
    quote_source: str  # jupiter | amm_model | backtest
    ts: datetime = field(default_factory=utcnow)
    rent_sol: float = 0.0  # ATA rent paid (buy) / refunded (sell, as negative)


@dataclass
class ScoreResult:
    total: float
    categories: dict[str, dict[str, Any]]
    coverage: float
    excluded: bool
    exclusion_reasons: list[str]
    explanations: list[str]
    risks: list[str]
    label: str  # e.g. "ALTO POTENZIALE", "OSSERVARE", "SCARTATO"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
