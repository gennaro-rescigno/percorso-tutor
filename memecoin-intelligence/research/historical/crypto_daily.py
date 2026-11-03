"""Study 'crypto_daily': short trades (held 1 to 3 days) on MANY coins, memecoins included, Binance 2018-2026.

The user asked for daily operations held at most 3 days, on very many coins and memecoins, entering on hype.
Free historical social data does not exist, so hype is measured where it shows: abnormal volume and price.

PRE-REGISTERED (written before looking at any result):
  * universe each day: the 100 most traded USDT pairs by 30-day average volume known the day before (memecoins
    such as DOGE, SHIB, PEPE, WIF, BONK, FLOKI included whenever they are in it), >= 60 days of history,
    stablecoins and leveraged tokens excluded, delisted pairs included with their real losses;
  * entries at the daily close (00:00 UTC) after the signal; exit at the close 1, 2 or 3 days later, or earlier at
    a -15% stop on the daily low (filled at the stop, or at the open if the day opens below it);
  * rules:
      H1 hype burst: day return >= +10% and volume >= 3x its 30-day average;
      H2 H1 only while BTC is above its 50-day average;
      P1 pullback in an uptrend: coin above its 50-day average and day return <= -7%;
      B1 breakout: close above the previous 20-day high, volume >= 2x average, BTC above its 50-day average;
      S1 short-term strength: the 5 best 3-day returns of the top 50, BTC above its 50-day average;
      M1 model: gradient-boosted trees on 15 daily features (returns 1/3/7/30 days, volume vs average,
         distance from the 20/50/200-day averages, 14-day volatility, age, liquidity rank, BTC's return and
         trend), trained on the past only (expanding window, retrained every 90 days from 2021-01-01), entering
         the 5 best predictions of the day when the prediction is above zero;
  * portfolio: at most 10 positions at once, 10% of equity each, a new signal is skipped when full (strongest
    first); costs per side: 0.10% fee + slippage 0.05% (top 30) or 0.20% (rank 31-100);
  * periods: 2018-2021 (in sample) and 2022-01-01 .. end (out of sample); verdict "regge" only with a positive
    out-of-sample CAGR, a 95% interval of the daily Sharpe above zero and positive results in both periods.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import crypto_trend as ct
from common import Report
from crypto_data import load_daily

TOP, SLOTS, STOP = 100, 10, 0.15
HOLDS = (1, 2, 3)


def build(d: pd.DataFrame) -> dict[str, pd.DataFrame]:
    p = {k: d.pivot(index="date", columns="symbol", values=k).sort_index() for k in
         ("open", "high", "low", "close", "quote_volume")}
    c, v = p["close"], p["quote_volume"]
    hist = c.notna().cumsum()
    adv = v.rolling(30, min_periods=20).mean().shift(1).where(hist.shift(1) >= 60)
    rank = adv.rank(axis=1, ascending=False, method="first")
    p["rank"] = rank
    p["universe"] = rank <= TOP
    p["r1"] = c.pct_change(fill_method=None)
    p["r3"] = c / c.shift(3) - 1
    p["volx"] = v / v.rolling(30, min_periods=20).mean().shift(1)
    p["ma20"], p["ma50"], p["ma200"] = (c.rolling(n, min_periods=n).mean() for n in (20, 50, 200))
    p["hi20"] = c.rolling(20, min_periods=20).max().shift(1)
    btc = c["BTCUSDT"]
    p["btc_up"] = btc > btc.rolling(50, min_periods=50).mean()
    return p


def rows_where(df: pd.DataFrame, s: pd.Series) -> pd.DataFrame:
    """Keep whole rows (days) where s is True (a DataFrame.where with a Series would align on the columns)."""
    m = s.reindex(df.index).fillna(False).astype(bool).to_numpy()[:, None]
    return df.where(np.broadcast_to(m, df.shape))


def signals(p: dict[str, pd.DataFrame], rule: str) -> pd.DataFrame:
    """Score per coin-day (higher = stronger), NaN = no entry."""
    u, c = p["universe"], p["close"]
    btc_up = p["btc_up"]
    if rule == "H1":
        m = (p["r1"] >= 0.10) & (p["volx"] >= 3)
        return p["volx"].where(m & u)
    if rule == "H2":
        m = (p["r1"] >= 0.10) & (p["volx"] >= 3)
        return rows_where(p["volx"].where(m & u), btc_up)
    if rule == "P1":
        m = (c > p["ma50"]) & (p["r1"] <= -0.07)
        return (-p["r1"]).where(m & u)
    if rule == "B1":
        m = (c > p["hi20"]) & (p["volx"] >= 2)
        return rows_where(p["volx"].where(m & u), btc_up)
    if rule == "S1":
        sc = p["r3"].where(p["rank"] <= 50)
        rk = sc.rank(axis=1, ascending=False, method="first")
        return rows_where(sc.where(rk <= 5), btc_up)
    raise ValueError(rule)


def model_scores(p: dict[str, pd.DataFrame], hold: int) -> pd.DataFrame:
    from sklearn.ensemble import HistGradientBoostingRegressor

    c = p["close"]
    feats = {
        "r1": p["r1"], "r3": p["r3"], "r7": c / c.shift(7) - 1, "r30": c / c.shift(30) - 1, "volx": p["volx"],
        "d20": c / p["ma20"] - 1, "d50": c / p["ma50"] - 1, "d200": c / p["ma200"] - 1,
        "vol14": p["r1"].rolling(14, min_periods=10).std(), "age": c.notna().cumsum(), "rank": p["rank"],
    }
    btc_r1 = p["r1"]["BTCUSDT"]
    btc_d50 = (c["BTCUSDT"] / p["ma50"]["BTCUSDT"] - 1)
    fwd = c.shift(-hold) / c - 1
    u = p["universe"]
    long = pd.DataFrame({k: v.where(u).stack() for k, v in feats.items()})
    long["btc_r1"] = long.index.get_level_values(0).map(btc_r1)
    long["btc_d50"] = long.index.get_level_values(0).map(btc_d50)
    long["y"] = fwd.where(u).stack().reindex(long.index)
    long = long.dropna(subset=["y"])
    long["y"] = long.y.clip(-0.5, 1.0)
    cols = [k for k in long.columns if k != "y"]
    dates = long.index.get_level_values(0)
    out = []
    start = pd.Timestamp("2021-01-01", tz="UTC")
    edges = list(pd.date_range(start, dates.max() + pd.Timedelta(days=1), freq="90D", tz="UTC"))
    for a, b in zip(edges[:-1], edges[1:]):
        tr = long[dates < a - pd.Timedelta(days=hold)]  # the target of the last training rows is already known
        te = long[(dates >= a) & (dates < b)]
        if len(tr) < 5000 or te.empty:
            continue
        m = HistGradientBoostingRegressor(max_iter=200, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=200,
                                          l2_regularization=1.0, random_state=0).fit(tr[cols], tr.y)
        out.append(pd.Series(m.predict(te[cols]), index=te.index))
    if not out:
        return pd.DataFrame(index=c.index, columns=c.columns)
    s = pd.concat(out).unstack()
    s = s.reindex(index=c.index, columns=c.columns)
    rk = s.rank(axis=1, ascending=False, method="first")
    return s.where((rk <= 5) & (s > 0))


def simulate(p: dict[str, pd.DataFrame], score: pd.DataFrame, hold: int) -> tuple[pd.Series, pd.DataFrame]:
    o, h, low, c, rank = (p[k].to_numpy() for k in ("open", "high", "low", "close", "rank"))
    sc = score.to_numpy()
    idx = p["close"].index
    cols = p["close"].columns
    eq, cash = 1.0, 1.0
    pos: list[dict] = []
    daily, trades = [], []
    for t in range(len(idx)):
        # mark and exits at today's prices
        keep = []
        for q in pos:
            j = q["j"]
            if np.isnan(c[t, j]):  # delisted: out at the last price
                cash += q["units"] * q["last"] * (1 - q["cost"])
                trades.append({**q["rec"], "exit": q["last"], "days": t - q["t0"], "why": "fine dati"})
                continue
            stop = q["entry"] * (1 - STOP)
            if low[t, j] <= stop:
                px = min(o[t, j], stop)
                cash += q["units"] * px * (1 - q["cost"])
                trades.append({**q["rec"], "exit": px, "days": t - q["t0"], "why": "stop"})
                continue
            q["last"] = c[t, j]
            if t - q["t0"] >= hold:
                cash += q["units"] * c[t, j] * (1 - q["cost"])
                trades.append({**q["rec"], "exit": c[t, j], "days": t - q["t0"], "why": "tempo"})
                continue
            keep.append(q)
        pos = keep
        eq = cash + sum(q["units"] * q["last"] for q in pos)
        daily.append(eq)
        # entries at today's close, strongest first
        free = SLOTS - len(pos)
        if free > 0:
            row = sc[t]
            cand = [(row[j], j) for j in np.where(~np.isnan(row))[0] if not any(q["j"] == j for q in pos)]
            for s_, j in sorted(cand, reverse=True)[:free]:
                if np.isnan(c[t, j]) or c[t, j] <= 0:
                    continue
                cost = 0.0010 + (0.0005 if rank[t, j] <= 30 else 0.0020)
                stake = eq / SLOTS
                if stake > cash:
                    break
                cash -= stake
                units = stake * (1 - cost) / c[t, j]
                pos.append({"j": j, "t0": t, "entry": c[t, j], "units": units, "last": c[t, j], "cost": cost,
                            "rec": {"date": idx[t], "coin": cols[j], "entry_px": c[t, j], "stake": stake,
                                    "cost": cost}})
    ser = pd.Series(daily, index=idx).pct_change().fillna(0.0)
    tr = pd.DataFrame(trades)
    if not tr.empty:
        tr["ret"] = tr.exit / tr.entry_px * (1 - tr.cost) ** 2 - 1
    return ser, tr


def main() -> None:
    r = Report("crypto_daily")
    r("# Studio storico: operazioni brevi (1-3 giorni) su moltissime monete, memecoin comprese (Binance 2018-2026)")
    r("\nPre-registrazione (testo originale):\n\n```\n" + __doc__.split("PRE-REGISTERED")[1].strip() + "\n```")
    d = load_daily()
    p = build(d)
    memes = [s for s in ("DOGEUSDT", "SHIBUSDT", "PEPEUSDT", "WIFUSDT", "BONKUSDT", "FLOKIUSDT", "BOMEUSDT",
                         "1000SATSUSDT", "MEMEUSDT", "TRUMPUSDT") if s in p["universe"].columns]
    share = p["universe"][memes].sum(axis=1)
    r(f"Universo: le 100 più scambiate di ogni giorno; memecoin presenti in media {share[share.index >= ct.START].mean():.1f} "
      f"al giorno ({', '.join(m.replace('USDT', '') for m in memes)}).")
    rows = []
    for rule in ("H1", "H2", "P1", "B1", "S1", "M1"):
        for hold in HOLDS:
            score = model_scores(p, hold) if rule == "M1" else signals(p, rule)
            ser, tr = simulate(p, score, hold)
            ser = ser[ser.index >= ct.START]
            ins, oos = ser[ser.index < ct.SPLIT], ser[ser.index >= ct.SPLIT]
            si, so = ct.stats(ins), ct.stats(oos)
            lo, hi = ct.sharpe_ci(oos)
            tro = tr[tr.date >= ct.SPLIT] if not tr.empty else tr
            ok = bool(so.get("CAGR_%", -1) > 0 and lo > 0 and si.get("CAGR_%", -1) > 0)
            rows.append({"regola": rule, "giorni": hold, "IS_CAGR_%": si.get("CAGR_%"), "IS_maxDD_%": si.get("maxDD_%"),
                         "OOS_CAGR_%": so.get("CAGR_%"), "OOS_Sharpe": so.get("Sharpe"),
                         "OOS_Sharpe_IC95": f"[{lo:.2f}, {hi:.2f}]", "OOS_maxDD_%": so.get("maxDD_%"),
                         "OOS_operazioni": len(tro), "OOS_media_op_%": 100 * tro.ret.mean() if len(tro) else np.nan,
                         "OOS_vincenti_%": 100 * (tro.ret > 0).mean() if len(tro) else np.nan,
                         "verdetto": "regge" if ok else "non regge"})
            print(rows[-1], flush=True)
    r.table(pd.DataFrame(rows))
    r.save()


if __name__ == "__main__":
    main()
