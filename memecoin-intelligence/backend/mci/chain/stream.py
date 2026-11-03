"""Free real-time pump.fun data from the public Solana WebSocket (``logsSubscribe`` on the pump program).

Measured on mainnet (Nov 2026): ~300 messages/s, ~380 KB/s, ~1,900 trades/min; ~88% of the messages are
failed transactions, skipped without JSON parsing. Every successful transaction's logs carry the official
pump.fun events (TradeEvent / CreateEvent / CompleteEvent), decoded with the public IDL layout.

The public endpoint can refuse or drop connections (seen from shared CI runners): reconnects use exponential
backoff (2 s .. 5 min) and every condition is counted, so the dashboard shows whether the stream is healthy.
When it is down, launches still arrive from PumpPortal (free ``subscribeNewToken``) and the trade-based
features stay "non disponibile" (never invented).
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import deque
from collections.abc import Callable
from typing import Any

from mci.chain.pump import PUMP_PROGRAM_ID, events_from_logs
from mci.domain import utcnow

log = logging.getLogger(__name__)

OK_MARKERS = ('"err":null', '"err": null')  # Solana nodes send compact JSON; tolerate a formatter too


class PumpStream:
    def __init__(self, ws_url: str, on_events: Callable[[list[Any]], None], program: str = PUMP_PROGRAM_ID,
                 commitment: str = "confirmed", on_state: Callable[[bool], None] | None = None):
        self.ws_url = ws_url
        self.on_events = on_events
        self.on_state = on_state  # called with True on (re)connection, False on disconnection
        self.program = program
        self.commitment = commitment
        self._stop = asyncio.Event()
        self.connected = False
        self.connected_since: float | None = None
        self.last_message_at = None
        self.last_error: str | None = None
        self._rate: deque = deque(maxlen=120)  # (minute, trades)
        self.stats: dict[str, int] = {"messages": 0, "skipped_failed": 0, "decoded_tx": 0, "trades": 0,
                                      "creates": 0, "completes": 0, "reconnects": 0, "handler_errors": 0,
                                      "bad_messages": 0}

    def stop(self) -> None:
        self._stop.set()

    def handle_raw(self, raw: str | bytes) -> list[Any]:
        """Process one WebSocket message (public for tests)."""
        self.stats["messages"] += 1
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", "replace")
        if not any(m in raw for m in OK_MARKERS):
            # failed transactions (or subscription acks): no events, no JSON parsing
            self.stats["skipped_failed"] += 1
            return []
        try:
            msg = json.loads(raw)
            res = msg["params"]["result"]
            value = res["value"]
            slot = (res.get("context") or {}).get("slot")
        except (ValueError, KeyError, TypeError):
            self.stats["bad_messages"] += 1
            return []
        if value.get("err") is not None:
            self.stats["skipped_failed"] += 1
            return []
        events = events_from_logs(value.get("logs"), value.get("signature"), slot)
        if not events:
            return []
        self.stats["decoded_tx"] += 1
        for ev in events:
            kind = type(ev).__name__
            if kind == "TradeEvent":
                self.stats["trades"] += 1
            elif kind == "CreateEvent":
                self.stats["creates"] += 1
            elif kind == "CompleteEvent":
                self.stats["completes"] += 1
        self.last_message_at = utcnow()
        try:
            self.on_events(events)
        except Exception:  # a handler bug must never kill the stream
            self.stats["handler_errors"] += 1
            log.exception("pump stream handler error")
        return events

    def _notify(self, up: bool) -> None:
        if self.on_state:
            try:
                self.on_state(up)
            except Exception:
                log.exception("stream state callback failed")

    def health(self) -> dict[str, Any]:
        return {
            "connected": self.connected,
            "connected_for_s": round(time.monotonic() - self.connected_since) if self.connected_since else None,
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
            "last_error": self.last_error,
            **self.stats,
        }

    async def run(self) -> None:
        import websockets

        backoff = 2.0
        sub = {"jsonrpc": "2.0", "id": 1, "method": "logsSubscribe",
               "params": [{"mentions": [self.program]}, {"commitment": self.commitment}]}
        while not self._stop.is_set():
            try:
                async with websockets.connect(self.ws_url, ping_interval=20, ping_timeout=30, open_timeout=20,
                                              max_size=2**22, max_queue=8192, close_timeout=5) as ws:
                    await ws.send(json.dumps(sub))
                    self.connected, self.connected_since = True, time.monotonic()
                    self._notify(True)
                    log.info("pump stream connesso")
                    async for raw in ws:
                        if self._stop.is_set():
                            break
                        self.handle_raw(raw)
                        if time.monotonic() - (self.connected_since or 0) > 60:
                            backoff = 2.0  # stable connection: reset the backoff
            except asyncio.CancelledError:
                raise
            except Exception as e:  # network / protocol errors -> reconnect with backoff
                self.last_error = f"{type(e).__name__}: {str(e)[:160]}"
                log.warning("pump stream disconnesso: %s", self.last_error)
            finally:
                if self.connected:
                    self._notify(False)
                self.connected, self.connected_since = False, None
            if self._stop.is_set():
                break
            self.stats["reconnects"] += 1
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=backoff)
            except asyncio.TimeoutError:
                pass
            backoff = min(backoff * 2, 300.0)
