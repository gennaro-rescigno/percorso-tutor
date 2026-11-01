"""Dashboard authentication: single user, password from env, HMAC-signed bearer tokens,
login rate limiting. No password configured => the API refuses every login."""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import secrets
import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from mci.config import Settings, get_settings

log = logging.getLogger(__name__)
_bearer = HTTPBearer(auto_error=False)
_fallback_key = secrets.token_bytes(32)
_failures: dict[str, deque] = defaultdict(lambda: deque(maxlen=20))
MAX_FAILURES = 5
WINDOW_S = 15 * 60


def _key(s: Settings) -> bytes:
    k = s.api_secret_key.get_secret_value()
    if not k:
        return _fallback_key  # tokens become invalid on restart; set MCI_API_SECRET_KEY in production
    return hashlib.sha256(k.encode()).digest()


def issue_token(s: Settings, username: str) -> tuple[str, int]:
    exp = int(time.time()) + s.api_token_ttl_hours * 3600
    payload = f"{username}|{exp}".encode()
    sig = hmac.new(_key(s), payload, hashlib.sha256).digest()
    enc = base64.urlsafe_b64encode
    return f"{enc(payload).decode()}.{enc(sig).decode()}", exp


def verify_token(s: Settings, token: str) -> str | None:
    try:
        p64, s64 = token.split(".", 1)
        payload = base64.urlsafe_b64decode(p64.encode())
        sig = base64.urlsafe_b64decode(s64.encode())
    except Exception:
        return None
    expected = hmac.new(_key(s), payload, hashlib.sha256).digest()
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        user, exp = payload.decode().split("|")
    except ValueError:
        return None
    if int(exp) < time.time():
        return None
    return user


def check_login(s: Settings, ip: str, username: str, password: str) -> bool:
    q = _failures[ip]
    now = time.time()
    while q and now - q[0] > WINDOW_S:
        q.popleft()
    if len(q) >= MAX_FAILURES:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "troppi tentativi: riprova più tardi")
    configured = s.dashboard_password.get_secret_value()
    if not configured:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "password della dashboard non configurata")
    ok = hmac.compare_digest(username.encode(), s.dashboard_username.encode()) and hmac.compare_digest(
        password.encode(), configured.encode()
    )
    if not ok:
        q.append(now)
        log.warning("failed dashboard login from %s", ip)
    return ok


def require_user(
    request: Request, creds: HTTPAuthorizationCredentials | None = Depends(_bearer)
) -> str:
    s = get_settings()
    token = creds.credentials if creds else request.query_params.get("token")
    user = verify_token(s, token) if token else None
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "autenticazione richiesta")
    return user
