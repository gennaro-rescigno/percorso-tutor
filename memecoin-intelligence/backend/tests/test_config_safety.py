"""Guard: the public example config must never contain real secrets."""

import re
from pathlib import Path

SECRET_KEYS = ("MCI_TELEGRAM_BOT_TOKEN", "MCI_TELEGRAM_CHAT_IDS", "MCI_DASHBOARD_PASSWORD", "MCI_API_SECRET_KEY",
               "MCI_JUPITER_API_KEY", "MCI_DUNE_API_KEY", "MCI_REDDIT_CLIENT_SECRET", "MCI_LIVE_WALLET_KEYFILE")
TELEGRAM_TOKEN = re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{30,}\b")


def test_env_example_has_no_secrets():
    text = (Path(__file__).resolve().parents[2] / ".env.example").read_text()
    values = dict(line.split("=", 1) for line in text.splitlines() if "=" in line and not line.startswith("#"))
    for key in SECRET_KEYS:
        assert values.get(key, "").strip() == "", f"{key} must stay empty in .env.example (use secrets/.env)"
    assert not TELEGRAM_TOKEN.search(text), "a Telegram bot token is written in .env.example"
