"""Free daily candles of EVERY Binance spot USDT pair, delisted ones included (data.binance.vision, public archive).

Point-in-time universe: at each date only the pairs that traded then exist, so coins that later collapsed or were
delisted (LUNA, FTT, ...) are in the data with their real losses (no survivorship bias).
"""

from __future__ import annotations

import concurrent.futures as cf
import io
import re
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

from common import DATA, UA

BUCKET = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
FILES = "https://data.binance.vision"
STABLE = {"USDC", "BUSD", "TUSD", "FDUSD", "DAI", "USDP", "PAX", "UST", "USTC", "SUSD", "EUR", "GBP", "AUD", "BRL",
          "TRY", "RUB", "NGN", "UAH", "BIDR", "IDRT", "BVND", "AEUR", "EURI", "USDE", "USD1", "XUSD", "BFUSD", "PAXG",
          "WBTC", "WBETH", "BETH", "USDS", "PYUSD", "RLUSD", "U"}
LEVERAGED = re.compile(r"(UP|DOWN|BULL|BEAR)$")


def _get(url: str, retries: int = 4) -> bytes:
    for k in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read()
        except Exception:
            if k == retries - 1:
                raise
            time.sleep(2 ** k)
    return b""


def list_prefixes(prefix: str) -> list[str]:
    out, marker = [], ""
    while True:
        xml = _get(f"{BUCKET}?delimiter=/&prefix={urllib.parse.quote(prefix)}&marker={urllib.parse.quote(marker)}").decode()
        found = re.findall(r"<Prefix>([^<]+)</Prefix>", xml)
        keys = re.findall(r"<Key>([^<]+)</Key>", xml)
        out += [p for p in found if p != prefix]
        out += keys
        if "<IsTruncated>true</IsTruncated>" not in xml:
            return out
        nm = re.findall(r"<NextMarker>([^<]+)</NextMarker>", xml)
        marker = nm[0] if nm else (out[-1] if out else "")


def usdt_symbols() -> list[str]:
    syms = [p.rstrip("/").split("/")[-1] for p in list_prefixes("data/spot/monthly/klines/")]
    keep = []
    for s in syms:
        if not s.endswith("USDT"):
            continue
        base = s[:-4]
        if base in STABLE or LEVERAGED.search(base) or not base:
            continue
        keep.append(s)
    return sorted(set(keep))


def _symbol_daily(sym: str) -> pd.DataFrame | None:
    try:
        return _symbol_daily_raw(sym)
    except Exception as e:  # one broken pair must not stop the download
        print(f"  {sym!r}: saltata ({type(e).__name__})", flush=True)
        return None


def _symbol_daily_raw(sym: str) -> pd.DataFrame | None:
    keys = [k for k in list_prefixes(f"data/spot/monthly/klines/{sym}/1d/") if k.endswith(".zip")]
    frames = []
    for k in keys:
        try:
            z = zipfile.ZipFile(io.BytesIO(_get(f"{FILES}/{urllib.parse.quote(k)}")))
            with z.open(z.namelist()[0]) as f:
                df = pd.read_csv(f, header=None, usecols=range(8))
        except Exception:
            continue
        if not str(df.iloc[0, 0]).isdigit():  # some files carry a header line
            df = df.iloc[1:]
        frames.append(df)
    if not frames:
        return None
    df = pd.concat(frames, ignore_index=True)
    df.columns = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume"]
    df = df.astype({"open_time": "int64", "open": float, "high": float, "low": float, "close": float,
                    "volume": float, "quote_volume": float})
    ot = df.open_time.where(df.open_time < 10**14, df.open_time // 1000)  # 2025+ files are in microseconds
    df["date"] = pd.to_datetime(ot, unit="ms", utc=True).dt.normalize()
    df["symbol"] = sym
    return df[["symbol", "date", "open", "high", "low", "close", "quote_volume"]].drop_duplicates("date")


def load_daily(max_workers: int = 24, only: list[str] | None = None) -> pd.DataFrame:
    """All USDT pairs (or only the given ones), daily, cached as one parquet file."""
    out = DATA / ("binance_daily.parquet" if not only else "binance_daily_" + "_".join(sorted(only))[:80] + ".parquet")
    if out.exists():
        return pd.read_parquet(out)
    DATA.mkdir(parents=True, exist_ok=True)
    syms = sorted(only) if only else usdt_symbols()
    print(f"coppie USDT (senza stablecoin né token a leva): {len(syms)}", flush=True)
    frames = []
    with cf.ThreadPoolExecutor(max_workers=max_workers) as ex:
        for i, df in enumerate(ex.map(_symbol_daily, syms)):
            if df is not None:
                frames.append(df)
            if i % 50 == 0:
                print(f"  {i}/{len(syms)}", flush=True)
    data = pd.concat(frames, ignore_index=True).sort_values(["symbol", "date"])
    data.to_parquet(out)
    return data
