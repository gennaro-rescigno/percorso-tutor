"""Optional social sources.

* X/Twitter: NOT implemented on purpose - since Feb 2026 the X API is pay-per-use
  (no free tier for new developers). ``XCollector`` always reports "unavailable".
* Reddit: app-only OAuth (client_credentials) with the user's own free Reddit app,
  100 QPM, non-commercial use only. Disabled unless credentials are configured.
* Telegram: public channel preview pages (t.me/<channel>) expose a member count.
  Fragile HTML parsing, disabled by default.
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from mci.utils.http import fnum


class XCollector:
    available = False
    reason = "X API a pagamento dal 2026 (pay-per-use): non utilizzata per mantenere il sistema gratuito"

    async def mentions(self, query: str) -> None:
        return None


class RedditCollector:
    TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
    API = "https://oauth.reddit.com"

    def __init__(self, client_id: str, client_secret: str, user_agent: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent
        self._token: str | None = None
        self._token_exp = 0.0
        self._http = httpx.AsyncClient(timeout=15, headers={"User-Agent": user_agent})

    @property
    def available(self) -> bool:
        return bool(self.client_id and self.client_secret)

    async def close(self) -> None:
        await self._http.aclose()

    async def _auth(self) -> str | None:
        if self._token and time.time() < self._token_exp - 60:
            return self._token
        r = await self._http.post(
            self.TOKEN_URL, data={"grant_type": "client_credentials"}, auth=(self.client_id, self.client_secret)
        )
        if r.status_code != 200:
            return None
        body = r.json()
        self._token = body.get("access_token")
        self._token_exp = time.time() + float(body.get("expires_in") or 3600)
        return self._token

    async def mentions(self, query: str, hours: int = 24) -> dict[str, Any] | None:
        """Count posts mentioning ``query`` in the last ``hours`` and their distinct authors."""
        if not self.available:
            return None
        token = await self._auth()
        if not token:
            return None
        r = await self._http.get(
            f"{self.API}/search",
            params={"q": query, "sort": "new", "limit": 100, "t": "day" if hours <= 24 else "week"},
            headers={"Authorization": f"bearer {token}"},
        )
        if r.status_code != 200:
            return None
        cutoff = datetime.now(timezone.utc).timestamp() - hours * 3600
        posts = [c.get("data") or {} for c in ((r.json().get("data") or {}).get("children") or [])]
        recent = [p for p in posts if (fnum(p.get("created_utc")) or 0) >= cutoff]
        authors = {p.get("author") for p in recent if p.get("author")}
        return {
            "posts": len(recent),
            "unique_authors": len(authors),
            "subreddits": len({p.get("subreddit") for p in recent}),
            "avg_score": (sum(fnum(p.get("score")) or 0 for p in recent) / len(recent)) if recent else 0.0,
        }


_MEMBERS_RE = re.compile(r"([\d\s.,]+)\s*(members|subscribers|iscritti|membri)", re.I)


def parse_telegram_members(html: str) -> int | None:
    m = _MEMBERS_RE.search(html or "")
    if not m:
        return None
    digits = re.sub(r"[^\d]", "", m.group(1))
    return int(digits) if digits else None


async def telegram_members(channel_url: str, timeout: float = 10.0) -> int | None:
    handle = channel_url.rstrip("/").split("/")[-1].lstrip("@")
    if not handle or not re.fullmatch(r"[A-Za-z0-9_]{4,64}", handle):
        return None
    async with httpx.AsyncClient(timeout=timeout) as c:
        try:
            r = await c.get(f"https://t.me/{handle}")
        except httpx.HTTPError:
            return None
    return parse_telegram_members(r.text) if r.status_code == 200 else None
