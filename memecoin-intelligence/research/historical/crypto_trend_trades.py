"""Study 'crypto_trend_trades': every single trade of the 50-day trend filter on BTC, ETH and SOL (2018-2026).

Answers "how many operations, and is it valid": round trips (entry when the close goes above its 50-day average,
exit when it goes below), their length, win rate, average and median result, profit concentration in the best
trades, per year, in sample (2018-2021) and out of sample (2022 - end). Costs 0.15% per side, as in the study.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from common import Report
from crypto_data import load_daily

COINS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
N, COST = 50, 0.0015
START, SPLIT = pd.Timestamp("2018-01-01", tz="UTC"), pd.Timestamp("2022-01-01", tz="UTC")


def round_trips(close: pd.Series) -> pd.DataFrame:
    c = close.dropna()
    sig = (c > c.rolling(N, min_periods=N).mean()).to_numpy()
    px, dates = c.to_numpy(), c.index
    out, entry = [], None
    for i in range(len(c)):
        if sig[i] and entry is None:
            entry = i
        elif not sig[i] and entry is not None:
            out.append((dates[entry], dates[i], px[entry], px[i], i - entry))
            entry = None
    if entry is not None:  # still open at the end of the data: valued at the last close
        out.append((dates[entry], dates[-1], px[entry], px[-1], len(c) - 1 - entry))
    t = pd.DataFrame(out, columns=["entrata", "uscita", "px_in", "px_out", "giorni"])
    t["ret"] = t.px_out / t.px_in * (1 - COST) ** 2 - 1
    return t[t.entrata >= START]


def describe(t: pd.DataFrame) -> dict:
    if t.empty:
        return {"operazioni": 0}
    win = t[t.ret > 0]
    gains, losses = win.ret.sum(), -t[t.ret <= 0].ret.sum()
    top = t.ret.sort_values(ascending=False)
    k = max(1, int(round(len(t) * 0.1)))
    return {"operazioni": len(t), "giorni_medi": round(t.giorni.mean(), 1), "giorni_mediani": float(t.giorni.median()),
            "vincenti_%": round(100 * len(win) / len(t), 1), "media_%": round(100 * t.ret.mean(), 2),
            "mediana_%": round(100 * t.ret.median(), 2), "migliore_%": round(100 * t.ret.max(), 1),
            "peggiore_%": round(100 * t.ret.min(), 1),
            "profit_factor": round(gains / losses, 2) if losses > 0 else np.inf,
            "quota_guadagno_dal_10%_migliore": round(100 * top.head(k).clip(lower=0).sum() / gains, 1) if gains > 0 else np.nan,
            "rendimento_composto_%": round(100 * (np.prod(1 + t.ret) - 1), 1)}


def main() -> None:
    r = Report("crypto_trend_trades")
    r("# Ogni operazione del filtro di trend a 50 giorni su BTC, ETH e SOL (Binance, 2018-2026)")
    r("\n" + __doc__.split("\n\n", 1)[1].strip())
    d = load_daily(only=COINS)
    close = d.pivot(index="date", columns="symbol", values="close").sort_index()
    rows, years, alltr = [], [], []
    for c in COINS:
        t = round_trips(close[c])
        t["moneta"] = c.replace("USDT", "")
        alltr.append(t)
        for label, sub in (("2018-2021 (in campione)", t[t.entrata < SPLIT]), ("2022-fine (fuori campione)", t[t.entrata >= SPLIT]),
                           ("tutto", t)):
            rows.append({"moneta": c.replace("USDT", ""), "periodo": label, **describe(sub)})
        for y, g in t.groupby(t.entrata.dt.year):
            years.append({"moneta": c.replace("USDT", ""), "anno": y, "operazioni": len(g),
                          "vincenti": int((g.ret > 0).sum()), "rendimento_composto_%": round(100 * (np.prod(1 + g.ret) - 1), 1)})
    every = pd.concat(alltr)
    for label, sub in (("2018-2021 (in campione)", every[every.entrata < SPLIT]),
                       ("2022-fine (fuori campione)", every[every.entrata >= SPLIT]), ("tutto", every)):
        rows.append({"moneta": "BTC+ETH+SOL", "periodo": label, **describe(sub)})
    r("\n## Riepilogo delle operazioni (andata e ritorno; ogni operazione = un acquisto e la sua vendita)")
    r.table(pd.DataFrame(rows))
    r("## Per anno")
    r.table(pd.DataFrame(years))
    r("## Le 10 operazioni migliori e le 10 peggiori fuori campione")
    oos = every[every.entrata >= SPLIT].sort_values("ret", ascending=False)
    show = pd.concat([oos.head(10), oos.tail(10)])
    show = show.assign(entrata=show.entrata.dt.strftime("%Y-%m-%d"), uscita=show.uscita.dt.strftime("%Y-%m-%d"),
                       ret=(100 * show.ret).round(1))
    r.table(show[["moneta", "entrata", "uscita", "giorni", "ret"]])
    r.save()


if __name__ == "__main__":
    main()
