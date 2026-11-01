"""Portable state export/import and static dashboard export.

Used by the GitHub Actions deployment, where the database lives in the Actions cache:
* ``export_state`` writes the essential state (paper portfolio, positions, orders, fills,
  signals, equity, recent events, alert dedupe, control flags) to one JSON file that is also
  published on the ``bot-state`` branch as a backup;
* ``import_state`` restores it into an EMPTY database if the cache was evicted;
* ``export_static`` calls the real API endpoints in-process and writes their JSON responses,
  so the React dashboard can be served as a read-only static site (GitHub Pages).
"""

from __future__ import annotations

import json
import os
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import DateTime, desc, select

from mci.database.models import (
    AlertLog,
    EquitySnapshot,
    Event,
    FillRow,
    Order,
    Position,
    SignalRow,
    SystemState,
)
from mci.database.session import session_scope

# table -> (model, max rows kept, order column)
# Order matters for import: referenced tables first (signals -> positions -> orders -> fills).
STATE_TABLES: dict[str, tuple[Any, int | None, Any]] = {
    "system_state": (SystemState, None, None),
    "signals": (SignalRow, 2000, SignalRow.id),
    "positions": (Position, None, Position.id),
    "orders": (Order, 5000, Order.id),
    "fills": (FillRow, 5000, FillRow.id),
    "equity_snapshots": (EquitySnapshot, 5000, EquitySnapshot.id),
    "events": (Event, 1000, Event.id),
    "alert_log": (AlertLog, None, None),
}

# foreign key column -> table it references (rows outside the exported window are dropped/nulled)
FOREIGN_KEYS: dict[str, dict[str, str]] = {
    "positions": {"signal_id": "signals"},
    "orders": {"signal_id": "signals", "position_id": "positions"},
    "fills": {"order_id": "orders"},
}


def _secret_values() -> list[str]:
    from mci.config import get_settings

    s = get_settings()
    vals = [s.telegram_bot_token, s.jupiter_api_key, s.dune_api_key, s.reddit_client_secret,
            s.dashboard_password, s.api_secret_key]
    return [v.get_secret_value() for v in vals if len(v.get_secret_value()) >= 8]


def scrub(text: str, secrets_: list[str] | None = None) -> str:
    """Defence in depth: remove any secret value that might have leaked into stored text
    (e.g. an exception message containing a URL) before publishing files."""
    for v in secrets_ if secrets_ is not None else _secret_values():
        text = text.replace(v, "***")
    return text


def _row_to_dict(row: Any) -> dict[str, Any]:
    out = {}
    for col in row.__table__.columns:
        v = getattr(row, col.key)
        out[col.key] = v.isoformat() if isinstance(v, datetime) else v
    return out


def export_state(path: str | Path) -> dict[str, int]:
    data: dict[str, Any] = {"version": 1}
    counts = {}
    with session_scope() as s:
        for name, (model, limit, order) in STATE_TABLES.items():
            q = select(model)
            if order is not None and limit:
                q = q.order_by(desc(order)).limit(limit)
            rows = [_row_to_dict(r) for r in s.scalars(q).all()]
            if order is not None:
                rows.sort(key=lambda r: r.get(order.key) or 0)
            data[name] = rows
            counts[name] = len(rows)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    from mci.database.session import json_serializer

    p.write_text(scrub(json_serializer(data)))
    return counts


def import_state(path: str | Path, only_if_empty: bool = True) -> dict[str, int]:
    data = json.loads(Path(path).read_text())
    counts: dict[str, int] = {}
    with session_scope() as s:
        if only_if_empty and s.scalar(select(SystemState).limit(1)) is not None:
            return {"skipped": 1}
        imported: dict[str, set] = {}
        for name, (model, _, _) in STATE_TABLES.items():
            rows = data.get(name) or []
            cols = {c.key: c for c in model.__table__.columns}
            ids: set = set()
            n = 0
            for r in rows:
                kw = {}
                for k, v in r.items():
                    if k not in cols:
                        continue
                    if v is not None and isinstance(cols[k].type, DateTime) and isinstance(v, str):
                        v = datetime.fromisoformat(v)
                    kw[k] = v
                skip = False
                for fk, target in FOREIGN_KEYS.get(name, {}).items():
                    if kw.get(fk) is not None and kw[fk] not in imported.get(target, set()):
                        if cols[fk].nullable:
                            kw[fk] = None  # referenced row is older than the exported window
                        else:
                            skip = True
                if skip:
                    continue
                s.merge(model(**kw))
                if "id" in kw:
                    ids.add(kw["id"])
                n += 1
            imported[name] = ids
            counts[name] = n
            s.flush()
    return counts


def export_static(out_dir: str | Path, max_tokens: int = 30, candle_points: int = 360) -> int:
    """Write the JSON answers of the dashboard API as static files (read-only public dashboard)."""
    import warnings

    warnings.filterwarnings("ignore", category=DeprecationWarning)
    from fastapi.testclient import TestClient

    from mci.config import reset_settings_cache

    hidden = _secret_values()  # real secrets, captured before the temporary password is set
    password = secrets.token_urlsafe(24)
    os.environ["MCI_DASHBOARD_PASSWORD"] = password
    os.environ.setdefault("MCI_API_SECRET_KEY", secrets.token_hex(32))
    reset_settings_cache()
    from mci.api.app import create_app

    client = TestClient(create_app())
    tok = client.post("/api/auth/login", json={"username": "admin", "password": password}).json()["token"]
    h = {"Authorization": f"Bearer {tok}"}
    out = Path(out_dir)
    (out / "tokens").mkdir(parents=True, exist_ok=True)
    n = 0

    def save(api_path: str, file: str, transform=None) -> Any:
        nonlocal n
        r = client.get(f"/api{api_path}", headers=h)
        if r.status_code != 200:
            return None
        body = r.json()
        if transform:
            body = transform(body)
        (out / file).write_text(scrub(json.dumps(body, default=str), hidden + [password]))
        n += 1
        return body

    save("/overview", "overview.json")
    scanner = save("/scanner?sort=score&limit=300&include_excluded=true", "scanner.json") or {"tokens": []}
    positions = save("/positions?status=all", "positions.json") or {"positions": []}
    for name in ("performance", "risk", "signals", "logs?limit=500", "config/options", "backtests"):
        save(f"/{name}", name.split("?")[0].replace("/", "_") + ".json")
    wanted = [t["address"] for t in scanner["tokens"] if t.get("status") != "excluded"][:max_tokens]
    wanted += [p["token"] for p in positions["positions"]]

    def trim(body: dict) -> dict:
        body["candles"] = (body.get("candles") or [])[-candle_points:]
        body["history"] = (body.get("history") or [])[-200:]
        return body

    for addr in dict.fromkeys(wanted):
        save(f"/tokens/{addr}", f"tokens/{addr}.json", trim)
    (out / "meta.json").write_text(json.dumps({"generated_at": datetime.utcnow().isoformat() + "Z", "static": True}))
    return n
