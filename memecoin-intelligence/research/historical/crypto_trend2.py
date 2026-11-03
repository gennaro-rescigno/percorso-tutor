"""Study 'crypto_trend2': is the trend filter a general effect or BTC's luck? Robustness checks.

crypto_trend found that holding BTC only above its N-day average beat BTC buy & hold out of sample (2022-2026) for
N = 50, 100 and 200, with half the drawdown, while every altcoin strategy lost. Written before running:
  * the same rule (hold the coin while its close is above its N-day average, else cash; N = 50, 100, 200) on each
    major with a long history: BTC, ETH, SOL, BNB, XRP, ADA, DOGE, each against its own buy & hold;
  * a portfolio of BTC, ETH and SOL, one third each (rebalanced monthly), every third with its own filter;
  * execution one full day late (signal of day t traded at the close of t+1) and costs doubled (0.30% per side);
  * same split as before: 2018-2021 in sample, 2022-01-01 .. end of data out of sample (SOL from its listing);
  * an effect is called "general" only if the filter beats buy & hold out of sample (higher CAGR AND smaller maximum
    drawdown) on at least 5 of the 7 coins for the N chosen in sample on BTC, and survives the late execution.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import crypto_trend as ct
from common import Report
from crypto_data import load_daily

COINS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT"]
NS = (50, 100, 200)


def filt(close: pd.Series, n: int, lag: int) -> pd.Series:
    sig = (close > close.rolling(n, min_periods=n).mean()).astype(float)
    return sig.shift(lag).fillna(0.0) if lag else sig


def run_one(close: pd.DataFrame, ret: pd.DataFrame, weights: pd.DataFrame, cost: float) -> pd.Series:
    w = weights.fillna(0.0)
    held = w.shift(1).fillna(0.0)
    gross = (held * ret[w.columns].fillna(0.0)).sum(axis=1)
    return gross - cost * (w - held).abs().sum(axis=1)


def main() -> None:
    r = Report("crypto_trend2")
    r("# Il filtro di trend è un effetto generale? Verifiche di robustezza (Binance, 2018-2026)")
    r("\n```\n" + __doc__.split("\n\n", 1)[1].strip() + "\n```")
    d = load_daily(only=COINS)
    close = d.pivot(index="date", columns="symbol", values="close").sort_index()
    close = close[[c for c in COINS if c in close.columns]]
    ret = close.pct_change(fill_method=None)
    rows = []
    for cost, lag, label in ((0.0015, 0, "base"), (0.0030, 0, "costi doppi"), (0.0015, 1, "un giorno di ritardo")):
        for c in close.columns:
            px = close[c]
            bh = pd.DataFrame({c: px.notna().astype(float)})
            series = {"compra e tieni": run_one(close, ret, bh, cost)}
            for n in NS:
                series[f"filtro {n}"] = run_one(close, ret, pd.DataFrame({c: filt(px, n, lag)}), cost)
            for name, x in series.items():
                x = x[(x.index >= ct.START) & px.reindex(x.index).notna()]
                ins, oos = x[x.index < ct.SPLIT], x[x.index >= ct.SPLIT]
                si, so = ct.stats(ins), ct.stats(oos)
                lo, hi = ct.sharpe_ci(oos)
                rows.append({"scenario": label, "moneta": c.replace("USDT", ""), "regola": name,
                             "IS_CAGR_%": si.get("CAGR_%"), "IS_maxDD_%": si.get("maxDD_%"),
                             "OOS_CAGR_%": so.get("CAGR_%"), "OOS_Sharpe": so.get("Sharpe"),
                             "OOS_Sharpe_IC95": f"[{lo:.2f}, {hi:.2f}]", "OOS_maxDD_%": so.get("maxDD_%")})
    tab = pd.DataFrame(rows)
    r("\n## Ogni moneta: compra e tieni contro il filtro di trend")
    r.table(tab)
    # chosen N on BTC in sample (base scenario)
    btc = tab[(tab.scenario == "base") & (tab.moneta == "BTC") & tab.regola.str.startswith("filtro")]
    btc_is = []
    for n in NS:
        x = run_one(close, ret, pd.DataFrame({"BTCUSDT": filt(close["BTCUSDT"], n, 0)}), 0.0015)
        x = x[(x.index >= ct.START) & (x.index < ct.SPLIT)]
        btc_is.append((ct.stats(x)["Sharpe"], n))
    n_star = max(btc_is)[1]
    r(f"Media scelta sul solo BTC nel 2018-2021 (miglior Sharpe): **{n_star} giorni**.")
    verdict = []
    for label in ("base", "costi doppi", "un giorno di ritardo"):
        wins = 0
        coins = 0
        for c in close.columns:
            sub = tab[(tab.scenario == label) & (tab.moneta == c.replace("USDT", ""))]
            bh = sub[sub.regola == "compra e tieni"].iloc[0]
            f = sub[sub.regola == f"filtro {n_star}"].iloc[0]
            if pd.isna(bh["OOS_CAGR_%"]):
                continue
            coins += 1
            wins += int(f["OOS_CAGR_%"] > bh["OOS_CAGR_%"] and f["OOS_maxDD_%"] > bh["OOS_maxDD_%"])
        verdict.append({"scenario": label, "monete in cui il filtro batte compra e tieni (rendimento E perdita massima)":
                        f"{wins}/{coins}", "verdetto": "effetto generale" if wins >= 5 else "non generale"})
    r.table(pd.DataFrame(verdict))
    # portfolio BTC/ETH/SOL, one third each, monthly rebalance, each with its own filter
    maj = [c for c in ("BTCUSDT", "ETHUSDT", "SOLUSDT") if c in close.columns]
    month = close.index.to_series().dt.is_month_start
    out = []
    for label, cost, lag in (("base", 0.0015, 0), ("un giorno di ritardo", 0.0015, 1)):
        avail = close[maj].notna().astype(float)
        base_w = avail.div(avail.sum(axis=1).replace(0, np.nan), axis=0).where(month).ffill().fillna(0.0)
        bh = run_one(close, ret, base_w, cost)
        sig = pd.DataFrame({c: filt(close[c], n_star, lag) for c in maj})
        tf = run_one(close, ret, base_w * sig, cost)
        for name, x in (("BTC+ETH+SOL compra e tieni", bh), (f"BTC+ETH+SOL con filtro {n_star}", tf)):
            x = x[x.index >= ct.START]
            so = ct.stats(x[x.index >= ct.SPLIT])
            lo, hi = ct.sharpe_ci(x[x.index >= ct.SPLIT])
            yearly = (1 + x).groupby(x.index.year).prod() - 1
            out.append({"scenario": label, "portafoglio": name, "OOS_CAGR_%": so.get("CAGR_%"),
                        "OOS_Sharpe": so.get("Sharpe"), "OOS_Sharpe_IC95": f"[{lo:.2f}, {hi:.2f}]",
                        "OOS_maxDD_%": so.get("maxDD_%"),
                        **{f"{y}_%": 100 * v for y, v in yearly.items()}})
    r("\n## Portafoglio BTC + ETH + SOL (un terzo ciascuno)")
    r.table(pd.DataFrame(out))
    r.save()


if __name__ == "__main__":
    main()
