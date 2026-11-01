"""Secrets the owner sets at runtime from their own Telegram chat (e.g. the free Jupiter API key).

They live only on the server, in ``<data_dir>/secrets/<name>`` with permissions 600: never in the
database, in the logs, in the state/dashboard exports or on GitHub.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from mci.config import Settings

JUPITER_KEY = "jupiter_api_key"
JUPITER_KEY_RE = re.compile(r"[A-Za-z0-9_.:-]{16,200}")


def _path(settings: Settings, name: str) -> Path:
    return Path(settings.data_dir) / "secrets" / name


def read_secret(settings: Settings, name: str) -> str:
    try:
        return _path(settings, name).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def write_secret(settings: Settings, name: str, value: str) -> None:
    p = _path(settings, name)
    p.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(value)
    os.replace(tmp, p)


def jupiter_key(settings: Settings) -> str:
    """Key from the environment (.env) if set, otherwise the one sent with /jupiterkey."""
    return settings.jupiter_api_key.get_secret_value() or read_secret(settings, JUPITER_KEY)
