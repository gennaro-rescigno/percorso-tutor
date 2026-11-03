"""Study 'crypto_trend': strategies with an economic logic on established cryptocurrencies, 2018-2026.

Data: daily candles of every Binance spot USDT pair, delisted pairs included (crypto_data.py).

PRE-REGISTERED (written before looking at any result):
  * universe at each date: the most traded pairs by 30-day average USDT volume known the day before (top 10 for the
    trend baskets, top 30 for momentum), at least 60 days of history; stablecoins and leveraged tokens excluded;
    a pair that stops trading is exited at its last price;
  * timing: a signal computed on the close of day t is held from the close of day t to the close of day t+1;
  * costs: 0.15% per side on every change of weight (0.10% fee + 0.05% slippage); cash earns nothing;
  * benchmarks: BTC buy & hold; equal-weight top 10, rebalanced monthly;
  * strategies:
      TF-BTC-N   BTC only while its close is above its N-day average (N = 50, 100, 200), otherwise cash;
      TF-10-N    top 10, each with a 1/10 slot held while the coin is above its own N-day average;
      XM-L       every Monday the 5 coins of the top 30 with the best L-day return (L = 7, 28, 90), equal weight;
      XMF-L      XM-L, only coins with a positive L-day return, and only while BTC is above its 100-day average;
      DON        top 10 Donchian: enter above the 50-day high, exit below the 20-day low, 1/10 slots;
  * walk-forward: each family's parameter is chosen on 2018-2021 (best Sharpe), and judged on 2022-01-01 .. the
    end of the data, never seen when choosing; every parameter's out-of-sample result is shown anyway;
  * statistics: CAGR, volatility, Sharpe (365 days), maximum drawdown, yearly returns; 95% interval of the
    out-of-sample Sharpe by block bootstrap (20-day blocks); verdict "regge" only when the chosen parameter has a
    positive out-of-sample CAGR with the Sharpe interval above zero.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from common import Report
from crypto_data import load_daily

COST = 0.0015
SPLIT = pd.Timestamp("2022-01-01", tz="UTC")
START = pd.Timestamp("2018-01-01", tz="UTC")
RNG = np.random.default_rng(42)


def panels(d: pd.DataFrame):
    close = d.pivot(index="date", columns="symbol", values="close").sort_index()
    vol = d.pivot(index="date", columns="symbol", values="quote_volume").reindex(close.index)
    ret = close.pct_change(fill_method=None)
    alive = close.notna()
    hist = alive.cumsum()
    adv = vol.rolling(30, min_periods=20).mean().shift(1)  # known the day before
    adv = adv.where(hist.shift(1) >= 60)
    return close, ret, adv


def top_mask(adv: pd.DataFrame, k: int) -> pd.DataFrame:
    rank = adv.rank(axis=1, ascending=False, method="first")
    return rank <= k


def run(weights: pd.DataFrame, ret: pd.DataFrame) -> pd.Series:
    """Daily net returns: weights decided at the close of t-1 earn the return of t; costs on weight changes."""
    w = weights.fillna(0.0)
    r = ret.reindex_like(w).fillna(0.0)
    held = w.shift(1).fillna(0.0)
    gross = (held * r).sum(axis=1)
    # drift of the weights inside the day is ignored for the turnover (small at daily rebalancing)
    turnover = (w - held).abs().sum(axis=1)
    return gross - COST * turnover


def stats(x: pd.Series) -> dict:
    x = x.dropna()
    if len(x) < 30:
        return {}
    eq = (1 + x).cumprod()
    years = len(x) / 365
    cagr = eq.iloc[-1] ** (1 / years) - 1 if eq.iloc[-1] > 0 else -1.0
    vol = x.std() * np.sqrt(365)
    sharpe = x.mean() / x.std() * np.sqrt(365) if x.std() > 0 else np.nan
    dd = (eq / eq.cummax() - 1).min()
    return {"CAGR_%": 100 * cagr, "vol_%": 100 * vol, "Sharpe": sharpe, "maxDD_%": 100 * dd,
            "finale_x": eq.iloc[-1]}


def sharpe_ci(x: pd.Series, block: int = 20, reps: int = 1000) -> tuple[float, float]:
    v = x.dropna().to_numpy()
    n = len(v)
    if n < 200:
        return np.nan, np.nan
    out = []
    for _ in range(reps):
        idx = np.concatenate([np.arange(s, s + block) % n for s in RNG.integers(0, n, n // block + 1)])[:n]
        s = v[idx]
        out.append(s.mean() / s.std() * np.sqrt(365) if s.std() > 0 else 0)
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def strategies(close, ret, adv) -> dict[str, pd.Series]:
    out: dict[str, pd.Series] = {}
    btc = "BTCUSDT"
    top10, top30 = top_mask(adv, 10), top_mask(adv, 30)
    # benchmarks
    w = pd.DataFrame(0.0, index=close.index, columns=close.columns)
    w[btc] = close[btc].notna().astype(float)
    out["BH-BTC"] = run(w, ret)
    month_start = close.index.to_series().dt.is_month_start
    m10 = top10.where(month_start, np.nan).ffill().fillna(False).astype(bool)
    wbh = m10.astype(float).div(m10.sum(axis=1).replace(0, np.nan), axis=0)
    out["BH-TOP10"] = run(wbh.where(close.notna(), 0.0), ret)
    # trend following
    for n in (50, 100, 200):
        sma = close.rolling(n, min_periods=n).mean()
        above = close > sma
        wb = pd.DataFrame(0.0, index=close.index, columns=close.columns)
        wb[btc] = above[btc].astype(float)
        out[f"TF-BTC-{n}"] = run(wb, ret)
        wt = (m10 & above).astype(float) / 10.0
        out[f"TF-10-{n}"] = run(wt.where(close.notna(), 0.0), ret)
    # cross-sectional momentum, weekly
    monday = close.index.to_series().dt.dayofweek == 0
    btc_up = close[btc] > close[btc].rolling(100, min_periods=100).mean()
    for lb in (7, 28, 90):
        past = close / close.shift(lb) - 1
        score = past.where(top30)
        rank = score.rank(axis=1, ascending=False, method="first")
        pick = (rank <= 5)
        w5 = pick.astype(float).div(pick.sum(axis=1).replace(0, np.nan), axis=0)
        w5 = w5.where(monday, np.nan).ffill().fillna(0.0)
        out[f"XM-{lb}"] = run(w5.where(close.notna(), 0.0), ret)
        pickf = pick & (score > 0)
        wf = pickf.astype(float).div(pickf.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
        wf = wf.mul(btc_up.astype(float), axis=0)
        wf = wf.where(monday, np.nan).ffill().fillna(0.0)
        out[f"XMF-{lb}"] = run(wf.where(close.notna(), 0.0), ret)
    # Donchian on the top 10
    hi50 = close.rolling(50, min_periods=50).max().shift(1)
    lo20 = close.rolling(20, min_periods=20).min().shift(1)
    state = pd.DataFrame(0.0, index=close.index, columns=close.columns)
    cur = np.zeros(close.shape[1])
    c, h, low, mem = close.to_numpy(), hi50.to_numpy(), lo20.to_numpy(), m10.to_numpy()
    for i in range(len(close)):
        enter = (c[i] > h[i]) & mem[i]
        exit_ = (c[i] < low[i]) | ~mem[i] | np.isnan(c[i])
        cur = np.where(enter, 1.0, np.where(exit_, 0.0, cur))
        state.iloc[i] = cur
    out["DON"] = run(state / 10.0, ret)
    return out


FAMILIES = {"TF-BTC": ["TF-BTC-50", "TF-BTC-100", "TF-BTC-200"], "TF-10": ["TF-10-50", "TF-10-100", "TF-10-200"],
            "XM": ["XM-7", "XM-28", "XM-90"], "XMF": ["XMF-7", "XMF-28", "XMF-90"], "DON": ["DON"]}


def main() -> None:
    r = Report("crypto_trend")
    r("# Studio storico: strategie con una logica sulle crypto affermate (Binance, 2018-2026)")
    r("\nPre-registrazione (testo originale):\n\n```\n" + __doc__.split("PRE-REGISTERED")[1].strip() + "\n```")
    d = load_daily()
    r(f"Dati: {d.symbol.nunique():,} coppie USDT, dal {d.date.min():%Y-%m-%d} al {d.date.max():%Y-%m-%d} "
      f"({len(d):,} candele giornaliere).")
    close, ret, adv = panels(d)
    res = strategies(close, ret, adv)
    rows = []
    for name, x in res.items():
        x = x[x.index >= START]
        ins, oos = x[x.index < SPLIT], x[x.index >= SPLIT]
        si, so = stats(ins), stats(oos)
        lo, hi = sharpe_ci(oos)
        rows.append({"strategia": name, "IS_CAGR_%": si.get("CAGR_%"), "IS_Sharpe": si.get("Sharpe"),
                     "IS_maxDD_%": si.get("maxDD_%"), "OOS_CAGR_%": so.get("CAGR_%"), "OOS_Sharpe": so.get("Sharpe"),
                     "OOS_Sharpe_IC95": f"[{lo:.2f}, {hi:.2f}]", "OOS_maxDD_%": so.get("maxDD_%"),
                     "OOS_vol_%": so.get("vol_%"), "OOS_finale_x": so.get("finale_x"),
                     "_lo": lo})
    tab = pd.DataFrame(rows)
    r("\n## Tutte le strategie: dentro il campione (2018-2021) e fuori campione (2022 - fine dati)")
    r.table(tab.drop(columns=["_lo"]))
    r("## Walk-forward: il parametro scelto solo sul 2018-2021, giudicato dopo")
    chosen = []
    for fam, names in FAMILIES.items():
        sub = tab[tab.strategia.isin(names)]
        best = sub.sort_values("IS_Sharpe", ascending=False).iloc[0]
        ok = bool(best["OOS_CAGR_%"] > 0 and best["_lo"] > 0)
        chosen.append({"famiglia": fam, "scelto": best.strategia, "OOS_CAGR_%": best["OOS_CAGR_%"],
                       "OOS_Sharpe": best.OOS_Sharpe, "OOS_Sharpe_IC95": best.OOS_Sharpe_IC95,
                       "OOS_maxDD_%": best["OOS_maxDD_%"], "verdetto": "regge" if ok else "non regge"})
    for b in ("BH-BTC", "BH-TOP10"):
        row = tab[tab.strategia == b].iloc[0]
        chosen.append({"famiglia": "riferimento", "scelto": b, "OOS_CAGR_%": row["OOS_CAGR_%"],
                       "OOS_Sharpe": row.OOS_Sharpe, "OOS_Sharpe_IC95": row.OOS_Sharpe_IC95,
                       "OOS_maxDD_%": row["OOS_maxDD_%"], "verdetto": "-"})
    r.table(pd.DataFrame(chosen))
    r("## Rendimento anno per anno (%)")
    yearly = pd.DataFrame({k: (1 + v[v.index >= START]).groupby(v[v.index >= START].index.year).prod() - 1
                           for k, v in res.items()}).T * 100
    yearly.insert(0, "strategia", yearly.index)
    r.table(yearly.reset_index(drop=True))
    r.save()


if __name__ == "__main__":
    main()
