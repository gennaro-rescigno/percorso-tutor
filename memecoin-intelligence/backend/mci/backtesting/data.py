"""Backtest dataset structures and loaders.

A ``TokenSeries`` holds, for one token/pool:
* candles in **SOL per token** (GeckoTerminal ``currency=token`` on SOL-quoted pools),
  volume in USD;
* optional point-in-time snapshots recorded by the live scanner (holders, security,
  buyers...). When absent the backtest runs in *reduced* (OHLCV-only) mode and says so.

Survivorship bias: the universe must be built from tokens *as they were discovered*
(our recorded ``tokens`` table, or a complete launch list such as a Dune export), never
from today's trending lists. ``DatasetInfo`` documents how a dataset was built.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mci.domain import Candle, TokenSnapshot


@dataclass
class TokenSeries:
    token: str
    symbol: str | None
    pool: str | None
    dex_id: str | None
    created_at: datetime | None
    first_seen_at: datetime | None
    candles: list[Candle]
    timeframe_s: int
    reserve_sol0: float | None = None  # quote-side reserve at first candle (if known)
    sol_usd: float | None = None
    snapshots: list[TokenSnapshot] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def start_ts(self) -> int:
        return self.candles[0].ts if self.candles else 0

    @property
    def end_ts(self) -> int:
        return self.candles[-1].ts if self.candles else 0


@dataclass
class DatasetInfo:
    source: str  # "recorded" | "gecko_pools_file" | "synthetic" | ...
    universe_method: str
    survivorship_free: bool
    point_in_time_features: bool
    n_tokens: int = 0
    start: str | None = None
    end: str | None = None
    notes: list[str] = field(default_factory=list)


@dataclass
class Dataset:
    series: list[TokenSeries]
    info: DatasetInfo

    def __post_init__(self) -> None:
        self.info.n_tokens = len(self.series)
        if self.series:
            s = min(x.start_ts for x in self.series if x.candles)
            e = max(x.end_ts for x in self.series if x.candles)
            self.info.start = datetime.fromtimestamp(s, tz=timezone.utc).isoformat()
            self.info.end = datetime.fromtimestamp(e, tz=timezone.utc).isoformat()

    def slice(self, start_ts: int, end_ts: int) -> "Dataset":
        """Tokens whose life intersects [start_ts, end_ts). Candles are NOT cut at end_ts
        so positions opened inside the window can be closed with real subsequent data."""
        out = [s for s in self.series if s.candles and s.end_ts >= start_ts and s.start_ts < end_ts]
        return Dataset(out, DatasetInfo(**{**asdict(self.info), "notes": list(self.info.notes)}))


# ----------------------------------------------------------------------------- files
def save_dataset(ds: Dataset, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "info": asdict(ds.info),
        "series": [
            {
                **{k: v for k, v in asdict(s).items() if k not in ("candles", "snapshots", "created_at", "first_seen_at")},
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "first_seen_at": s.first_seen_at.isoformat() if s.first_seen_at else None,
                "candles": [[c.ts, c.open, c.high, c.low, c.close, c.volume] for c in s.candles],
                "snapshots": [x.to_dict() for x in s.snapshots],
            }
            for s in ds.series
        ],
    }
    p.write_text(json.dumps(payload))


def load_dataset(path: str | Path) -> Dataset:
    raw = json.loads(Path(path).read_text())
    series = []
    for s in raw["series"]:
        series.append(
            TokenSeries(
                token=s["token"],
                symbol=s.get("symbol"),
                pool=s.get("pool"),
                dex_id=s.get("dex_id"),
                created_at=datetime.fromisoformat(s["created_at"]) if s.get("created_at") else None,
                first_seen_at=datetime.fromisoformat(s["first_seen_at"]) if s.get("first_seen_at") else None,
                candles=[Candle(*row) for row in s["candles"]],
                timeframe_s=s["timeframe_s"],
                reserve_sol0=s.get("reserve_sol0"),
                sol_usd=s.get("sol_usd"),
                snapshots=[TokenSnapshot.from_dict(x) for x in s.get("snapshots") or []],
                meta=s.get("meta") or {},
            )
        )
    return Dataset(series, DatasetInfo(**raw["info"]))
