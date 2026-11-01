"""Executor interface (paper and live implement the same contract)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from mci.domain import Fill


@dataclass
class ExecResult:
    ok: bool
    fill: Fill | None = None
    error: str | None = None
    quote: dict[str, Any] | None = None
    tx_signature: str | None = None
    simulated_failure: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class TradeRequest:
    token: str
    side: str  # buy | sell
    sol_amount: float | None = None  # buy
    qty: float | None = None  # sell (UI units)
    decimals: int | None = None
    reference_price: float | None = None  # SOL per token at decision time
    dex_id: str | None = None
    reserve_sol: float | None = None
    market_cap_usd: float | None = None
    close_account: bool = False  # full exit: ATA rent refunded
    first_buy: bool = True  # ATA creation rent paid
    slippage_bps: int = 300
    client_order_id: str = ""


class Executor(ABC):
    mode: str = "paper"

    @abstractmethod
    async def execute(self, req: TradeRequest) -> ExecResult: ...
