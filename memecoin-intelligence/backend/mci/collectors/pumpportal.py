"""PumpPortal real-time data (unofficial third-party API for Pump.fun, free, rate limited).

WebSocket ``wss://pumpportal.fun/api/data``; messages to send:
* ``{"method": "subscribeNewToken"}``
* ``{"method": "subscribeMigration"}``
* ``{"method": "subscribeTokenTrade", "keys": [mint, ...]}``

PumpPortal asks clients to use ONE connection and add subscriptions on it, so this
listener multiplexes everything over a single socket and reconnects with backoff.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from mci.domain import TokenSnapshot, utcnow
from mci.utils.http import fnum

log = logging.getLogger(__name__)

# Pump.fun bonding curve constants (approximate, from public program parameters - verify):
PUMP_INITIAL_VIRTUAL_SOL = 30.0
PUMP_INITIAL_VIRTUAL_TOKENS = 1_073_000_000.0
PUMP_TOTAL_SUPPLY = 1_000_000_000.0

Handler = Callable[[dict[str, Any]], Awaitable[None]]


def estimate_curve_sol_reserve(market_cap_sol: float) -> float:
    """Virtual SOL reserve implied by a market cap on the constant-product bonding curve.

    k = x*y = 30 * 1.073e9 ; price = x/y ; mcap = price * 1e9 -> x = sqrt(k * mcap / 1e9)
    """
    k = PUMP_INITIAL_VIRTUAL_SOL * PUMP_INITIAL_VIRTUAL_TOKENS
    return (k * max(market_cap_sol, 0.0) / PUMP_TOTAL_SUPPLY) ** 0.5


def event_to_snapshot(ev: dict[str, Any], observed_at: datetime | None = None) -> TokenSnapshot | None:
    mint = ev.get("mint")
    if not mint:
        return None
    snap = TokenSnapshot(
        chain="solana",
        token_address=mint,
        observed_at=observed_at or utcnow(),
        symbol=ev.get("symbol"),
        name=ev.get("name"),
        dex_id="pumpfun" if (ev.get("pool") in (None, "pump")) else str(ev.get("pool")),
        bonding_curve=True,
    )
    if ev.get("txType") == "create":
        snap.created_at = snap.observed_at
        snap.deployer = ev.get("traderPublicKey")
        if isinstance(ev.get("is_mayhem_mode"), bool):
            snap.mayhem = ev["is_mayhem_mode"]
    mc_sol = fnum(ev.get("marketCapSol"))
    vsol = fnum(ev.get("vSolInBondingCurve"))
    vtok = fnum(ev.get("vTokensInBondingCurve"))
    if vsol and vtok:
        snap.v_sol_in_curve = vsol
        snap.liquidity_quote = vsol
        snap.price_native = vsol / vtok
    elif mc_sol:
        snap.liquidity_quote = estimate_curve_sol_reserve(mc_sol)
    if mc_sol is not None:
        snap.social_metrics["market_cap_sol"] = mc_sol
    snap.sources["realtime"] = "pumpportal"
    return snap


class PumpPortalListener:
    def __init__(self, url: str, on_event: Handler):
        self.url = url
        self.on_event = on_event
        self._ws: Any = None
        self._trade_keys: set[str] = set()
        self._stop = asyncio.Event()
        self.connected = False
        self.last_message_at: datetime | None = None

    async def subscribe_trades(self, mints: list[str]) -> None:
        new = [m for m in mints if m not in self._trade_keys]
        if not new:
            return
        self._trade_keys.update(new)
        if self._ws is not None:
            await self._ws.send(json.dumps({"method": "subscribeTokenTrade", "keys": new}))

    async def unsubscribe_trades(self, mints: list[str]) -> None:
        old = [m for m in mints if m in self._trade_keys]
        if not old:
            return
        self._trade_keys.difference_update(old)
        if self._ws is not None:
            await self._ws.send(json.dumps({"method": "unsubscribeTokenTrade", "keys": old}))

    def stop(self) -> None:
        self._stop.set()

    async def run(self) -> None:
        import websockets  # local import keeps module importable without the dependency

        backoff = 2.0
        while not self._stop.is_set():
            try:
                async with websockets.connect(self.url, ping_interval=20, ping_timeout=20) as ws:
                    self._ws = ws
                    self.connected = True
                    backoff = 2.0
                    await ws.send(json.dumps({"method": "subscribeNewToken"}))
                    await ws.send(json.dumps({"method": "subscribeMigration"}))
                    if self._trade_keys:
                        await ws.send(json.dumps({"method": "subscribeTokenTrade", "keys": sorted(self._trade_keys)}))
                    async for raw in ws:
                        if self._stop.is_set():
                            break
                        try:
                            msg = json.loads(raw)
                        except ValueError:
                            continue
                        if isinstance(msg, dict) and (msg.get("mint") or msg.get("txType")):
                            self.last_message_at = utcnow()
                            try:
                                await self.on_event(msg)
                            except Exception:  # handler errors must not kill the socket
                                log.exception("pumpportal handler error")
            except Exception as e:  # network errors -> reconnect
                log.warning("pumpportal disconnected: %s", e)
            finally:
                self._ws = None
                self.connected = False
            if self._stop.is_set():
                break
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 120)
