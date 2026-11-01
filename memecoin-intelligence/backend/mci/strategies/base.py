"""Strategy interface.

A strategy receives a point-in-time ``MarketContext`` and either returns a buy
``Signal`` or the list of conditions that were not met (logged for analysis).
Strategies never size positions and never place orders: that is the job of the
risk manager and the executor.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, fields, replace
from datetime import datetime
from typing import Any, ClassVar

from mci.domain import Candle, ScoreResult, Signal, TokenSnapshot


@dataclass
class MarketContext:
    now: datetime
    snapshot: TokenSnapshot
    candles: list[Candle]  # closed candles of the strategy timeframe, oldest -> newest
    score: ScoreResult | None
    history: list[TokenSnapshot] = field(default_factory=list)  # older snapshots, oldest first
    timeframe_s: int = 60
    reduced: bool = False  # True when only OHLCV is available (e.g. historical backtest)

    @property
    def price(self) -> float | None:
        if self.candles:
            return self.candles[-1].close
        return self.snapshot.price_native


@dataclass
class Decision:
    signal: Signal | None
    failed: list[str] = field(default_factory=list)
    passed: list[str] = field(default_factory=list)


@dataclass
class StrategyParams:
    min_score: float = 65.0
    min_stop_pct: float = 0.08
    max_stop_pct: float = 0.35

    def with_overrides(self, overrides: dict[str, Any] | None) -> "StrategyParams":
        if not overrides:
            return self
        names = {f.name for f in fields(self)}
        return replace(self, **{k: v for k, v in overrides.items() if k in names})


class Strategy(ABC):
    code: ClassVar[str] = "?"
    name: ClassVar[str] = "base"
    default_timeframe: ClassVar[str] = "1m"
    params_cls: ClassVar[type[StrategyParams]] = StrategyParams

    def __init__(self, params: StrategyParams | dict[str, Any] | None = None):
        if isinstance(params, StrategyParams):
            self.params = params
        else:
            self.params = self.params_cls().with_overrides(params or {})

    @abstractmethod
    def evaluate(self, ctx: MarketContext) -> Decision: ...

    # ---------------------------------------------------------------- helpers
    def _gate_score(self, ctx: MarketContext, d: Decision) -> bool:
        if ctx.reduced:
            d.passed.append("gate di score non applicato (backtest con soli dati OHLCV)")
            return True
        if ctx.score is None:
            d.failed.append("score non disponibile")
            return False
        if ctx.score.excluded:
            d.failed.append("token escluso dai filtri: " + "; ".join(ctx.score.exclusion_reasons[:3]))
            return False
        if ctx.score.total < self.params.min_score:
            d.failed.append(f"score {ctx.score.total:.0f} < {self.params.min_score:.0f}")
            return False
        d.passed.append(f"score {ctx.score.total:.0f}/100")
        return True

    def _clamp_stop(self, price: float, stop: float) -> float:
        lo = price * (1 - self.params.max_stop_pct)
        hi = price * (1 - self.params.min_stop_pct)
        return min(max(stop, lo), hi)

    def _make_signal(self, ctx: MarketContext, stop: float, d: Decision, features: dict[str, Any]) -> Signal:
        price = ctx.price or 0.0
        s = ctx.snapshot
        risks = list(ctx.score.risks) if ctx.score else []
        return Signal(
            strategy=self.code,
            token_address=s.token_address,
            symbol=s.symbol,
            created_at=ctx.now,
            reference_price=price,
            stop_price=self._clamp_stop(price, stop),
            score=ctx.score.total if ctx.score else 0.0,
            reasons=list(d.passed),
            risks=risks,
            features=features,
            reduced_features=ctx.reduced,
            pair_address=s.pair_address,
            dex_id=s.dex_id,
        )
