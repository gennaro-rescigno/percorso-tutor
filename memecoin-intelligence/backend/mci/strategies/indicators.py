"""Small, dependency-free technical indicators on lists of candles.

All functions only look at data up to the last element passed in, so callers
control point-in-time correctness by slicing (``candles[: i + 1]``).
"""

from __future__ import annotations

from collections.abc import Sequence

from mci.domain import Candle


def ema(values: Sequence[float], period: int) -> list[float]:
    if not values:
        return []
    k = 2.0 / (period + 1)
    out = [float(values[0])]
    for v in values[1:]:
        out.append(out[-1] + k * (float(v) - out[-1]))
    return out


def sma(values: Sequence[float], period: int) -> float | None:
    if len(values) < period or period <= 0:
        return None
    return sum(values[-period:]) / period


def true_ranges(candles: Sequence[Candle]) -> list[float]:
    trs = []
    prev_close = None
    for c in candles:
        if prev_close is None:
            trs.append(c.high - c.low)
        else:
            trs.append(max(c.high - c.low, abs(c.high - prev_close), abs(c.low - prev_close)))
        prev_close = c.close
    return trs


def atr(candles: Sequence[Candle], period: int = 14) -> float | None:
    if len(candles) < period + 1:
        return None
    trs = true_ranges(candles)
    # Wilder smoothing
    a = sum(trs[1 : period + 1]) / period
    for tr in trs[period + 1 :]:
        a = (a * (period - 1) + tr) / period
    return a


def atr_pct(candles: Sequence[Candle], period: int = 14) -> float | None:
    a = atr(candles, period)
    if a is None or not candles or candles[-1].close <= 0:
        return None
    return a / candles[-1].close


def highest_high(candles: Sequence[Candle], n: int, exclude_last: bool = True) -> float | None:
    seq = candles[:-1] if exclude_last else candles
    if len(seq) < n:
        return None
    return max(c.high for c in seq[-n:])


def lowest_low(candles: Sequence[Candle], n: int, exclude_last: bool = False) -> float | None:
    seq = candles[:-1] if exclude_last else candles
    if len(seq) < n:
        return None
    return min(c.low for c in seq[-n:])


def avg_volume(candles: Sequence[Candle], n: int, exclude_last: bool = True) -> float | None:
    seq = candles[:-1] if exclude_last else candles
    if len(seq) < n:
        return None
    return sum(c.volume for c in seq[-n:]) / n


def pct_change(candles: Sequence[Candle], n: int) -> float | None:
    if len(candles) <= n or candles[-n - 1].close <= 0:
        return None
    return candles[-1].close / candles[-n - 1].close - 1.0


def trend_up(candles: Sequence[Candle], fast: int = 20, slow: int = 50) -> bool | None:
    if len(candles) < slow:
        return None
    closes = [c.close for c in candles]
    return ema(closes, fast)[-1] > ema(closes, slow)[-1]


def resample(candles: Sequence[Candle], factor: int) -> list[Candle]:
    """Aggregate consecutive candles (e.g. 1m -> 5m with factor=5), aligned on ts."""
    if factor <= 1:
        return list(candles)
    out: list[Candle] = []
    bucket: list[Candle] = []
    span = None
    for c in candles:
        if span is None and candles:
            span = (candles[1].ts - candles[0].ts) if len(candles) > 1 else 60
        key = c.ts // (span * factor)
        if bucket and bucket[0].ts // (span * factor) != key:
            out.append(_merge(bucket))
            bucket = []
        bucket.append(c)
    if bucket:
        out.append(_merge(bucket))
    return out


def _merge(b: list[Candle]) -> Candle:
    return Candle(
        ts=b[0].ts,
        open=b[0].open,
        high=max(c.high for c in b),
        low=min(c.low for c in b),
        close=b[-1].close,
        volume=sum(c.volume for c in b),
    )
