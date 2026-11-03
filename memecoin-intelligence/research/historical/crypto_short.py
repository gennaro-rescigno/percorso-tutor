"""Study 'crypto_short': betting on the FALL (short on perpetual futures), held 1 to 3 days, on many coins and memecoins.

Why: in crypto_daily every rule that BUYS altcoins and memecoins lost money out of sample, including buying the
hype. The mirror question is whether selling them short after the hype earns money once fees, slippage and the
funding paid between longs and shorts are counted. Binance USDT perpetuals cover many Solana memecoins that have
no spot pair (1000BONK, WIF, POPCAT, GOAT, FARTCOIN, MOODENG, PNUT...). Free data: data.binance.vision, delisted
contracts included with their real prices.

PRE-REGISTERED (written before looking at any result):
  * universe each day: the 100 perpetuals with the highest 30-day average volume known the day before, >= 30 days
    of history (new listings have their own rule); quarterly contracts and stablecoins excluded;
  * short entry at the daily close (00:00 UTC) after the signal; exit at the close 1, 2 or 3 days later, or earlier
    at a +15% stop on the daily high (filled at the stop, or at the open if the day opens above it); a position
    cannot lose more than its collateral (no leverage: 1x);
  * funding: the real Binance funding of each day held is credited to the short when positive and charged when
    negative (on the notional at the previous close); days without funding data count as zero;
  * costs per side: 0.05% fee + slippage 0.05% (volume rank 1-30) or 0.20% (rank 31-100 and new listings);
  * rules (strongest signal first, at most 10 positions of 10% of equity):
      SH1 fade the hype: day return >= +10% and volume >= 3x its 30-day average;
      SH2 SH1 only while BTC is below its 50-day average;
      SS1 fade strength: the 5 best 3-day returns of the top 50;
      SN1 new listings: short at the close of the second day of trading (the first day is partial) when that day
          traded >= 20 million USDT;
      SF1 crowded longs: the day's funding >= 0.10% and a positive 3-day return;
      SB1 follow weakness: BTC below its 50-day average, coin below its 50-day average, the 5 worst 7-day
          returns of the top 50;
  * periods: 2020-2021 (in sample; perpetuals on most coins start in 2020) and 2022-01-01 .. end (out of sample);
  * every rule and hold with a positive out-of-sample result is re-run with: costs doubled, entry one day late,
    stop at +25%, funding ignored; plus its results year by year;
  * verdict "regge" only with: positive in both periods, out-of-sample 95% interval of the Sharpe above zero, and
    still positive with costs doubled and with the late entry.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import crypto_trend as ct
from common import Report
from crypto_data import load_futures_daily

TOP, SLOTS = 100, 10
HOLDS = (1, 2, 3)
START = pd.Timestamp("2020-01-01", tz="UTC")
SPLIT = ct.SPLIT
MEMES = {"DOGEUSDT", "1000SHIBUSDT", "1000PEPEUSDT", "1000BONKUSDT", "1000FLOKIUSDT", "WIFUSDT", "BOMEUSDT",
         "POPCATUSDT", "MEWUSDT", "NEIROUSDT", "1000SATSUSDT", "MEMEUSDT", "TRUMPUSDT", "PNUTUSDT", "GOATUSDT",
         "ACTUSDT", "MOODENGUSDT", "FARTCOINUSDT", "CHILLGUYUSDT", "PEOPLEUSDT", "TURBOUSDT", "BRETTUSDT",
         "1000CATUSDT", "DOGSUSDT", "PONKEUSDT", "MYROUSDT", "1000RATSUSDT", "SPXUSDT", "1MBABYDOGEUSDT",
         "1000CHEEMSUSDT", "PENGUUSDT", "MUBARAKUSDT", "BANANAS31USDT", "1000WHYUSDT", "SLERFUSDT", "BANUSDT"}


def build(d: pd.DataFrame) -> dict[str, pd.DataFrame]:
    p = {k: d.pivot(index="date", columns="symbol", values=k).sort_index() for k in
         ("open", "high", "low", "close", "quote_volume", "funding")}
    c, v = p["close"], p["quote_volume"]
    hist = c.notna().cumsum()
    p["age"] = hist
    adv = v.rolling(30, min_periods=20).mean().shift(1).where(hist.shift(1) >= 30)
    p["rank"] = adv.rank(axis=1, ascending=False, method="first")
    p["universe"] = p["rank"] <= TOP
    p["r1"] = c.pct_change(fill_method=None)
    p["r3"] = c / c.shift(3) - 1
    p["r7"] = c / c.shift(7) - 1
    p["volx"] = v / v.rolling(30, min_periods=20).mean().shift(1)
    p["ma50"] = c.rolling(50, min_periods=50).mean()
    btc = c["BTCUSDT"]
    p["btc_down"] = btc < btc.rolling(50, min_periods=50).mean()
    return p


def rows_where(df: pd.DataFrame, s: pd.Series) -> pd.DataFrame:
    m = s.reindex(df.index).fillna(False).astype(bool).to_numpy()[:, None]
    return df.where(np.broadcast_to(m, df.shape))


def top_k(sc: pd.DataFrame, k: int, ascending: bool) -> pd.DataFrame:
    rk = sc.rank(axis=1, ascending=ascending, method="first")
    return sc.where(rk <= k)


def signals(p: dict[str, pd.DataFrame], rule: str) -> pd.DataFrame:
    """Score per coin-day (higher = stronger short signal), NaN = no entry."""
    u = p["universe"]
    if rule in ("SH1", "SH2"):
        m = (p["r1"] >= 0.10) & (p["volx"] >= 3) & u
        sc = p["volx"].where(m)
        return rows_where(sc, p["btc_down"]) if rule == "SH2" else sc
    if rule == "SS1":
        return top_k(p["r3"].where(p["rank"] <= 50), 5, ascending=False)
    if rule == "SN1":
        m = (p["age"] == 2) & (p["quote_volume"] >= 20e6)
        return p["quote_volume"].where(m)
    if rule == "SF1":
        m = (p["funding"] >= 0.0010) & (p["r3"] > 0) & u
        return p["funding"].where(m)
    if rule == "SB1":
        sc = (-p["r7"]).where((p["rank"] <= 50) & (p["close"] < p["ma50"]))
        return rows_where(top_k(sc, 5, ascending=False), p["btc_down"])
    raise ValueError(rule)


def simulate(p, score: pd.DataFrame, hold: int, stop: float = 0.15, cost_mult: float = 1.0,
             use_funding: bool = True) -> tuple[pd.Series, pd.DataFrame]:
    o, h, c, rank, fund = (p[k].to_numpy() for k in ("open", "high", "close", "rank", "funding"))
    sc = score.to_numpy()
    idx, cols = p["close"].index, p["close"].columns
    cash = 1.0
    pos: list[dict] = []
    daily, trades = [], []

    def close_pos(q, px, t, why):
        nonlocal cash
        pnl = q["units"] * (q["entry"] - px) - q["units"] * px * q["cost"] + q["fund"]
        value = max(0.0, q["stake"] * (1 - q["cost"]) + pnl)  # 1x collateral: the loss stops at the stake
        cash += value
        trades.append({**q["rec"], "exit": px, "days": t - q["t0"], "why": why, "funding": q["fund"] / q["stake"],
                       "ret": value / q["stake"] - 1})

    for t in range(len(idx)):
        keep = []
        for q in pos:
            j = q["j"]
            if np.isnan(c[t, j]):  # delisted / no candle: out at the last price
                close_pos(q, q["last"], t, "fine dati")
                continue
            lvl = q["entry"] * (1 + stop)
            if h[t, j] >= lvl:  # stopped during the day: its funding is not counted (conservative)
                close_pos(q, max(o[t, j], lvl), t, "stop")
                continue
            if use_funding and not np.isnan(fund[t, j]):
                q["fund"] += q["units"] * q["last"] * fund[t, j]
            q["last"] = c[t, j]
            if t - q["t0"] >= hold:
                close_pos(q, c[t, j], t, "tempo")
                continue
            keep.append(q)
        pos = keep
        eq = cash + sum(max(0.0, q["stake"] * (1 - q["cost"]) + q["units"] * (q["entry"] - q["last"]) + q["fund"])
                        for q in pos)
        daily.append(eq)
        free = SLOTS - len(pos)
        if free <= 0:
            continue
        row = sc[t]
        held = {q["j"] for q in pos}
        cand = [(row[j], j) for j in np.where(~np.isnan(row))[0] if j not in held]
        for _, j in sorted(cand, reverse=True)[:free]:
            if np.isnan(c[t, j]) or c[t, j] <= 0:
                continue
            r = rank[t, j]
            cost = cost_mult * (0.0005 + (0.0005 if (not np.isnan(r) and r <= 30) else 0.0020))
            stake = eq / SLOTS
            if stake > cash:
                break
            cash -= stake
            pos.append({"j": j, "t0": t, "entry": c[t, j], "units": stake / c[t, j], "last": c[t, j], "cost": cost,
                        "stake": stake, "fund": 0.0,
                        "rec": {"date": idx[t], "coin": cols[j], "entry_px": c[t, j]}})
    ser = pd.Series(daily, index=idx).pct_change().fillna(0.0)
    return ser, pd.DataFrame(trades)


def row(label: str, ser: pd.Series, tr: pd.DataFrame) -> dict:
    ser = ser[ser.index >= START]
    si, so = ct.stats(ser[ser.index < SPLIT]), ct.stats(ser[ser.index >= SPLIT])
    lo, hi = ct.sharpe_ci(ser[ser.index >= SPLIT])
    tro = tr[tr.date >= SPLIT] if not tr.empty else tr
    return {"variante": label, "IS_CAGR_%": si.get("CAGR_%"), "OOS_CAGR_%": so.get("CAGR_%"),
            "OOS_Sharpe": so.get("Sharpe"), "OOS_Sharpe_IC95": f"[{lo:.2f}, {hi:.2f}]", "OOS_maxDD_%": so.get("maxDD_%"),
            "OOS_operazioni": len(tro), "OOS_vincenti_%": 100 * (tro.ret > 0).mean() if len(tro) else np.nan,
            "OOS_media_op_%": 100 * tro.ret.mean() if len(tro) else np.nan,
            "OOS_funding_medio_op_%": 100 * tro.funding.mean() if len(tro) else np.nan,
            "OOS_stop_%": 100 * (tro.why == "stop").mean() if len(tro) else np.nan,
            "_lo": lo}


def yearly(ser: pd.Series) -> pd.Series:
    s = ser[ser.index >= START]
    return ((1 + s).groupby(s.index.year).prod() - 1) * 100


def main() -> None:
    r = Report("crypto_short")
    r("# Studio storico: scommettere sulla discesa (short sui perpetui), tenuta 1-3 giorni (Binance 2020-2026)")
    r("\nPre-registrazione (testo originale):\n\n```\n" + __doc__.split("PRE-REGISTERED")[1].strip() + "\n```")
    d = load_futures_daily()
    p = build(d)
    c = p["close"]
    last = c.index.max()
    gone = int((c.apply(lambda s: s.last_valid_index()) < last - pd.Timedelta(days=7)).sum())
    has_f = d.groupby("symbol").has_funding.first()
    r(f"Perpetui USDT: **{c.shape[1]}** (di cui {gone} chiusi o delistati prima della fine), dati fino al "
      f"{last.date()}; con dati di funding: {int(has_f.sum())}. Memecoin dell'elenco presenti: "
      f"{len([m for m in MEMES if m in c.columns])}.")
    fcov = p["funding"].notna().sum().sum() / max(1, p["close"].notna().sum().sum())
    fu = p["funding"].where(p["universe"]).stack().dropna()
    r(f"Giorni di contrattazione con dato di funding: **{100 * fcov:.1f}%**; nelle 100 più scambiate funding giornaliero "
      f"medio {100 * fu.mean():+.4f}%, mediano {100 * fu.median():+.4f}%, giorni >= 0,10%: {100 * (fu >= 0.001).mean():.1f}%.")
    u = p["universe"]
    fwd3 = (c.shift(-3) / c - 1).where(u)
    ew = p["r1"].where(u).mean(axis=1)
    for lab, a, b in (("2020-2021", START, SPLIT), ("2022-fine", SPLIT, last + pd.Timedelta(days=1))):
        sel = (fwd3.index >= a) & (fwd3.index < b)
        f3 = fwd3[sel].stack().dropna()
        st = ct.stats(ew[(ew.index >= a) & (ew.index < b)])
        r(f"- {lab}: delle 100 monete più scambiate, il {100 * (f3 < 0).mean():.1f}% scende nei 3 giorni successivi "
          f"(variazione media {100 * f3.mean():+.2f}%, mediana {100 * f3.median():+.2f}%); tenerle tutte in parti "
          f"uguali: {st.get('CAGR_%', float('nan')):+.1f}% annuo, perdita massima {st.get('maxDD_%', float('nan')):.0f}%.")
    base_rows, keep = [], []
    for rule in ("SH1", "SH2", "SS1", "SN1", "SF1", "SB1"):
        sc = signals(p, rule)
        for hold in HOLDS:
            ser, tr = simulate(p, sc, hold)
            rw = row(f"{rule}, {hold} giorni", ser, tr)
            base_rows.append(rw)
            print(rw, flush=True)
            if (rw["OOS_CAGR_%"] or -1) > 0:
                keep.append((rule, hold, sc, ser, tr, rw))
    tab = pd.DataFrame(base_rows)
    r("\n## Le regole pre-registrate")
    r.table(tab.drop(columns="_lo"))
    r(f"Positive fuori campione: **{len(keep)} su {len(tab)}**.")
    verdicts = []
    if keep:
        r("\n## Verifiche sulle combinazioni positive fuori campione")
    for rule, hold, sc, ser, tr, rw in keep:
        rows = [rw]
        for lab, kw, s_ in (("costi doppi", {"cost_mult": 2.0}, sc), ("entrata un giorno dopo", {}, sc.shift(1)),
                            ("stop a +25%", {"stop": 0.25}, sc), ("senza funding", {"use_funding": False}, sc)):
            s2, t2 = simulate(p, s_, hold, **kw)
            rows.append(row(f"{rule}, {hold} giorni: {lab}", s2, t2))
        vt = pd.DataFrame(rows)
        r(f"\n### {rule}, {hold} giorni")
        r.table(vt.drop(columns="_lo"))
        y = yearly(ser)
        r("Anno per anno (%): " + ", ".join(f"{k} {v:+.1f}" for k, v in y.items()))
        if not tr.empty:
            m = tr[(tr.date >= SPLIT) & tr.coin.isin(MEMES)]
            nm = tr[(tr.date >= SPLIT) & ~tr.coin.isin(MEMES)]
            r(f"Fuori campione, solo descrittivo: {len(m)} operazioni su memecoin (media {100 * m.ret.mean():+.2f}%), "
              f"{len(nm)} sulle altre (media {100 * nm.ret.mean():+.2f}%).")
        ok = ((rw["IS_CAGR_%"] or -1) > 0 and rw["_lo"] > 0 and (vt.iloc[1]["OOS_CAGR_%"] or -1) > 0
              and (vt.iloc[2]["OOS_CAGR_%"] or -1) > 0)
        verdicts.append((f"{rule}, {hold} giorni", "regge" if ok else "non regge"))
    r("\n## Verdetto")
    if not verdicts:
        r("Nessuna regola positiva fuori campione: **nessuna regge**.")
    for k, v in verdicts:
        r(f"- {k}: **{v}**")
    r.save()


if __name__ == "__main__":
    main()
