"""Wash-trading and coordination heuristics computed from a list of trades.

Inputs are normalized trades ``{"ts": datetime, "wallet": str, "side": "buy"|"sell", "usd": float}``.
The heuristics follow the indicators used in public analyses (trades per trader,
wallets trading both sides, round-trip volume, volume concentration) - see
RESEARCH_REPORT H3. Thresholds are priors to be calibrated with recorded data.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any


def _clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


@dataclass
class WashMetrics:
    n_trades: int
    unique_traders: int
    trades_per_trader: float
    two_sided_share: float  # share of traders who both bought and sold
    round_trip_volume_share: float  # share of USD volume that is offset by the same wallet
    top5_volume_share: float
    wash_score: float  # 0 clean .. 1 heavy wash trading
    volume_discount: float  # multiply raw volume by this before using it
    sufficient: bool

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def wash_metrics(trades: list[dict[str, Any]], min_trades: int = 20) -> WashMetrics:
    trades = [t for t in trades if t.get("wallet") and t.get("side") in ("buy", "sell")]
    n = len(trades)
    by_wallet: dict[str, dict[str, float]] = defaultdict(lambda: {"buy": 0.0, "sell": 0.0, "n": 0})
    total = 0.0
    for t in trades:
        w = by_wallet[t["wallet"]]
        usd = float(t.get("usd") or 0.0)
        w[t["side"]] += usd
        w["n"] += 1
        total += usd
    u = len(by_wallet)
    if n < min_trades or u == 0 or total <= 0:
        return WashMetrics(n, u, n / u if u else 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, False)
    tpt = n / u
    two_sided = sum(1 for w in by_wallet.values() if w["buy"] > 0 and w["sell"] > 0) / u
    rt = sum(2 * min(w["buy"], w["sell"]) for w in by_wallet.values()) / total
    vols = sorted((w["buy"] + w["sell"] for w in by_wallet.values()), reverse=True)
    top5 = sum(vols[:5]) / total
    f_tpt = _clip((tpt - 2.0) / 8.0)
    f_conc = _clip((top5 - 0.30) / 0.50)
    score = _clip(0.35 * f_tpt + 0.45 * _clip(rt) + 0.20 * f_conc)
    return WashMetrics(
        n_trades=n,
        unique_traders=u,
        trades_per_trader=tpt,
        two_sided_share=two_sided,
        round_trip_volume_share=_clip(rt),
        top5_volume_share=top5,
        wash_score=score,
        volume_discount=_clip(1.0 - rt, 0.0, 1.0),
        sufficient=True,
    )


def early_buyer_concentration(
    created_at: datetime,
    trades: list[dict[str, Any]],
    window_s: int = 10,
    total_supply: float = 1_000_000_000.0,
) -> dict[str, Any]:
    """Share of supply bought in the first ``window_s`` seconds (sniper/bundle proxy).

    ``trades`` here are PumpPortal trade events normalized with ``token_amount``.
    Same-window buying by many wallets right at creation is the typical bundle pattern.
    """
    end = created_at + timedelta(seconds=window_s)
    early = [t for t in trades if t.get("side") == "buy" and created_at <= t["ts"] <= end]
    amount = sum(float(t.get("token_amount") or 0.0) for t in early)
    wallets = {t.get("wallet") for t in early if t.get("wallet")}
    return {
        "early_buys": len(early),
        "early_wallets": len(wallets),
        "early_supply_pct": 100.0 * amount / total_supply if total_supply else None,
    }


def coordinated_selling(
    trades: list[dict[str, Any]], top_holders: set[str], window_s: int = 600, min_wallets: int = 3
) -> bool:
    """True if >= ``min_wallets`` top holders sold within any ``window_s`` window (H12)."""
    sells = sorted((t for t in trades if t.get("side") == "sell" and t.get("wallet") in top_holders),
                   key=lambda t: t["ts"])
    for i, t in enumerate(sells):
        wallets = {t["wallet"]}
        for u in sells[i + 1 :]:
            if (u["ts"] - t["ts"]).total_seconds() > window_s:
                break
            wallets.add(u["wallet"])
        if len(wallets) >= min_wallets:
            return True
    return False
