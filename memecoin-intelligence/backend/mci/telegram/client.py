"""Minimal Telegram Bot API client (sendMessage + long polling getUpdates)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

log = logging.getLogger(__name__)


class TelegramClient:
    def __init__(self, token: str, chat_ids: set[int], *, http: httpx.AsyncClient | None = None):
        self._token = token  # never logged
        self.chat_ids = chat_ids
        self._http = http or httpx.AsyncClient(timeout=40)
        self._lock = asyncio.Lock()
        self.enabled = bool(token) and bool(chat_ids)
        self.sent = 0
        self.failed = 0

    @property
    def _base(self) -> str:
        return f"https://api.telegram.org/bot{self._token}"

    async def close(self) -> None:
        await self._http.aclose()

    async def send(self, text: str, chat_id: int | None = None) -> bool:
        if not self.enabled:
            log.info("telegram disabled; message not sent: %s", text[:120].replace("\n", " "))
            return False
        targets = [chat_id] if chat_id is not None else sorted(self.chat_ids)
        ok_all = True
        async with self._lock:  # keep under Telegram's per-chat rate limits
            for cid in targets:
                for chunk in _split(text):
                    ok = await self._send_one(cid, chunk)
                    ok_all &= ok
                    await asyncio.sleep(0.4)
        return ok_all

    async def _send_one(self, chat_id: int, text: str) -> bool:
        for attempt in range(3):
            try:
                r = await self._http.post(
                    f"{self._base}/sendMessage",
                    json={"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True},
                )
            except httpx.HTTPError as e:
                log.warning("telegram send error: %s", type(e).__name__)
                await asyncio.sleep(2**attempt)
                continue
            if r.status_code == 429:
                retry = (r.json().get("parameters") or {}).get("retry_after", 3)
                await asyncio.sleep(min(float(retry), 30))
                continue
            if r.status_code == 200:
                self.sent += 1
                return True
            log.warning("telegram send failed: HTTP %s", r.status_code)
            break
        self.failed += 1
        return False

    async def get_updates(self, offset: int | None, timeout: int = 30) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"timeout": timeout, "allowed_updates": '["message"]'}
        if offset is not None:
            params["offset"] = offset
        try:
            r = await self._http.get(f"{self._base}/getUpdates", params=params, timeout=timeout + 10)
        except httpx.HTTPError:
            await asyncio.sleep(5)
            return []
        if r.status_code != 200:
            await asyncio.sleep(5)
            return []
        return r.json().get("result") or []


def _split(text: str, limit: int = 3900) -> list[str]:
    if len(text) <= limit:
        return [text]
    parts, cur = [], ""
    for line in text.split("\n"):
        if len(cur) + len(line) + 1 > limit:
            parts.append(cur)
            cur = ""
        cur += line + "\n"
    if cur:
        parts.append(cur)
    return parts
