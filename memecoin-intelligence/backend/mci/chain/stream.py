"""Free real-time pump.fun data from the public Solana WebSocket (``logsSubscribe`` on the pump program).

Measured on mainnet (Nov 2026): ~300 messages/s, ~380 KB/s, ~1,900 trades/min; ~80-88% of the messages are
failed transactions, skipped without JSON parsing. Every successful transaction's logs carry the official
pump.fun events (TradeEvent / CreateEvent / CompleteEvent), decoded with the public IDL layout.

The public endpoint drops long subscriptions: in the rehearsal (Nov 3, 2026) every connection was closed after
~15-25 s with an invalid close code (``1002 invalid status code``). Therefore:

* several REDUNDANT connections run side by side (staggered start) and every transaction is de-duplicated by
  signature: data are missing only when ALL connections are down at the same time;
* a connection that delivered data reconnects after 1 s; repeated refusals back off up to 60 s;
* the "stream up/down" state reported to the launch tracker is the aggregate (up while at least one is up),
  so the tracker measures the real coverage of every time window.

When everything is down, launches still arrive from PumpPortal (free ``subscribeNewToken``) and the trade-based
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
SEEN_MAX = 50_000  # signatures remembered for de-duplication across connections
PRODUCTIVE_SESSION_MSGS = 100


class PumpStream:
    def __init__(self, ws_url: str, on_events: Callable[[list[Any]], None], program: str = PUMP_PROGRAM_ID,
                 commitment: str = "confirmed", on_state: Callable[[bool], None] | None = None,
                 connections: int = 1, stagger_s: float = 7.0):
        self.ws_url = ws_url
        self.on_events = on_events
        self.on_state = on_state  # called with True when the first connection is up, False when all are down
        self.program = program
        self.commitment = commitment
        self.n_connections = max(1, connections)
        self.stagger_s = stagger_s
        self._stop = asyncio.Event()
        self._up: set[int] = set()
        self.connected_since: float | None = None
        self.last_message_at = None
        self.last_error: str | None = None
        self._seen: set[str] = set()
        self._seen_order: deque = deque()
        self.sessions: deque = deque(maxlen=50)  # (connection, seconds, messages, reason) of recent sessions
        self.stats: dict[str, int] = {"messages": 0, "skipped_failed": 0, "decoded_tx": 0, "duplicates": 0,
                                      "trades": 0, "creates": 0, "completes": 0, "reconnects": 0,
                                      "handler_errors": 0, "bad_messages": 0}

    @property
    def connected(self) -> bool:
        return bool(self._up)

    def stop(self) -> None:
        self._stop.set()

    def _is_new(self, sig: str | None) -> bool:
        if not sig:
            return True
        if sig in self._seen:
            return False
        self._seen.add(sig)
        self._seen_order.append(sig)
        if len(self._seen_order) > SEEN_MAX:
            self._seen.discard(self._seen_order.popleft())
        return True

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
        if not self._is_new(value.get("signature")):
            self.stats["duplicates"] += 1  # same transaction already received on another connection
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

    def _set_up(self, conn: int, up: bool) -> None:
        was = bool(self._up)
        (self._up.add if up else self._up.discard)(conn)
        now = bool(self._up)
        if now != was:
            self.connected_since = time.monotonic() if now else None
            if self.on_state:
                try:
                    self.on_state(now)
                except Exception:
                    log.exception("stream state callback failed")

    def health(self) -> dict[str, Any]:
        recent = list(self.sessions)
        return {
            "connected": self.connected,
            "connections_up": len(self._up),
            "connections": self.n_connections,
            "connected_for_s": round(time.monotonic() - self.connected_since) if self.connected_since else None,
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
            "last_error": self.last_error,
            "avg_session_s": round(sum(s[1] for s in recent) / len(recent), 1) if recent else None,
            **self.stats,
        }

    async def run(self) -> None:
        tasks = [asyncio.create_task(self._connection(i)) for i in range(self.n_connections)]
        try:
            await asyncio.gather(*tasks)
        finally:
            for t in tasks:
                t.cancel()

    async def _sleep(self, seconds: float) -> None:
        try:
            await asyncio.wait_for(self._stop.wait(), timeout=seconds)
        except asyncio.TimeoutError:
            pass

    async def _connection(self, conn: int) -> None:
        import websockets

        if conn:
            await self._sleep(self.stagger_s * conn)  # desynchronize the drops of the redundant connections
        backoff = 1.0
        sub = {"jsonrpc": "2.0", "id": 1, "method": "logsSubscribe",
               "params": [{"mentions": [self.program]}, {"commitment": self.commitment}]}
        while not self._stop.is_set():
            started, received, reason = time.monotonic(), 0, "chiusa"
            try:
                async with websockets.connect(self.ws_url, ping_interval=20, ping_timeout=30, open_timeout=20,
                                              max_size=2**22, max_queue=8192, close_timeout=5) as ws:
                    await ws.send(json.dumps(sub))
                    self._set_up(conn, True)
                    log.info("pump stream connesso (connessione %s)", conn + 1)
                    async for raw in ws:
                        if self._stop.is_set():
                            break
                        received += 1
                        self.handle_raw(raw)
            except asyncio.CancelledError:
                raise
            except Exception as e:  # network / protocol errors -> reconnect
                reason = f"{type(e).__name__}: {str(e)[:160]}"
                self.last_error = reason
                log.info("pump stream: connessione %s chiusa dopo %.0f s (%s)", conn + 1,
                         time.monotonic() - started, reason)
            finally:
                self._set_up(conn, False)
            self.sessions.append((conn, round(time.monotonic() - started, 1), received, reason[:80]))
            if self._stop.is_set():
                break
            self.stats["reconnects"] += 1
            # a productive session (the node simply dropped us) -> reconnect at once; refusals -> back off
            backoff = 1.0 if received >= PRODUCTIVE_SESSION_MSGS else min(backoff * 2, 60.0)
            await self._sleep(backoff)
