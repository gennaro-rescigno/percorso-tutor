"""Study 'crypto_carry': harvesting the hype without betting on the price (long spot + short perpetual, 1-3 days).

When a coin is in a frenzy, leveraged buyers on perpetual futures pay a funding fee to the sellers every 8 hours.
Holding the coin (spot) and selling the same amount of its perpetual cancels the price move and collects that fee.
It is a known trade ("cash and carry"; Schmeling, Schrimpf and Todorov, "Crypto carry", BIS 2023, document large
and time-varying carry in crypto); the question is whether it survives our costs with holds of 1-3 days on many
coins and memecoins. Free data: Binance spot and USDT perpetual daily candles and funding (data.binance.vision).

PRE-REGISTERED (written before looking at any result):
  * coins: every USDT perpetual with a Binance spot pair of the same coin (exact name, or the perpetual's "1000" /
    "1000000" / "1M" multiplier removed), accepted only if the daily returns of the two correlate >= 0.9; universe
    each day: the 100 with the highest 30-day perpetual volume known the day before, >= 30 days of history;
  * signal at the daily close (00:00 UTC): the funding of the day just ended (its 3 payments, all known by then);
    position = half of the slot in spot, half as 1x collateral of an equal short on the perpetual; it earns the
    funding of each following day (or pays it when negative) plus the change in the spot-perpetual gap; exit at the
    close 1, 2 or 3 days later (7 days shown only for information: it is outside the 3-day limit);
  * costs per side and leg: spot 0.10% fee, perpetual 0.05% fee, plus slippage 0.05% (rank 1-30) or 0.20% (31-100)
    on each leg; the short leg cannot lose more than its collateral;
  * rules (strongest funding first, at most 10 positions of 10% of equity):
      C1 the day's funding >= 0.03% (above the base rate of 0.01% every 8 hours);
      C2 the day's funding >= 0.10% (frenzy);
      C3 funding >= 0.05% on each of the last 3 days (persistent);
      C0 BTC and ETH only, whenever their funding >= 0.03% (the classic, liquid version);
  * periods: 2020-2021 (in sample) and 2022-01-01 .. end (out of sample); every rule and hold positive out of sample
    is re-run with costs doubled and with entry one day late; verdict "regge" only with positive results in both
    periods, an out-of-sample 95% interval of the Sharpe above zero, and still positive with costs doubled and late.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import crypto_trend as ct
from common import Report
from crypto_data import load_daily, load_futures_daily, usdt_symbols

TOP, SLOTS = 100, 10
HOLDS = (1, 2, 3, 7)
START, SPLIT = pd.Timestamp("2020-01-01", tz="UTC"), ct.SPLIT
MULT = ("1000000", "1000", "1M")


def spot_name(perp: str, spot: set[str]) -> str | None:
    if perp in spot:
        return perp
    for m in MULT:
        if perp.startswith(m) and perp[len(m):] in spot:
            return perp[len(m):]
    return None


def build(fut: pd.DataFrame, spot: pd.DataFrame, pairs: dict[str, str]) -> dict[str, pd.DataFrame]:
    P = {k: fut.pivot(index="date", columns="symbol", values=k).sort_index() for k in
         ("high", "close", "quote_volume", "funding")}
    cols = sorted(pairs)
    S = spot.pivot(index="date", columns="symbol", values="close").sort_index()
    S = S.reindex(index=P["close"].index)[[pairs[c] for c in cols]]
    S.columns = cols
    p = {k: v[cols] for k, v in P.items()}
    p["spot"] = S
    c, v = p["close"], p["quote_volume"]
    hist = (c.notna() & S.notna()).cumsum()
    adv = v.rolling(30, min_periods=20).mean().shift(1).where(hist.shift(1) >= 30)
    p["rank"] = adv.rank(axis=1, ascending=False, method="first")
    p["universe"] = p["rank"] <= TOP
    return p


def signals(p, rule: str) -> pd.DataFrame:
    f, u = p["funding"], p["universe"]
    if rule == "C1":
        return f.where(u & (f >= 0.0003))
    if rule == "C2":
        return f.where(u & (f >= 0.0010))
    if rule == "C3":
        m = (f >= 0.0005) & (f.shift(1) >= 0.0005) & (f.shift(2) >= 0.0005)
        return f.where(u & m)
    if rule == "C0":
        keep = [k for k in f.columns if k in ("BTCUSDT", "ETHUSDT")]
        out = pd.DataFrame(np.nan, index=f.index, columns=f.columns)
        out[keep] = f[keep].where(f[keep] >= 0.0003)
        return out
    raise ValueError(rule)


def simulate(p, score: pd.DataFrame, hold: int, cost_mult: float = 1.0) -> tuple[pd.Series, pd.DataFrame]:
    hi, pc, sc_, rank, fund = (p[k].to_numpy() for k in ("high", "close", "spot", "rank", "funding"))
    sig = score.to_numpy()
    idx, cols = p["close"].index, p["close"].columns
    cash = 1.0
    pos: list[dict] = []
    daily, trades = [], []

    def value(q, s_px, p_px):
        spot_leg = q["half"] * s_px / q["s0"]
        short_leg = max(0.0, q["half"] * (1 + (q["p0"] - p_px) / q["p0"]) + q["fund"] - q["entry_cost"])
        return spot_leg, short_leg

    def close(q, s_px, p_px, t, why):
        nonlocal cash
        a, b = value(q, s_px, p_px)
        out = a * (1 - q["cs"]) + b - q["half"] * (p_px / q["p0"]) * q["cp"]
        cash += max(0.0, out)
        trades.append({**q["rec"], "days": t - q["t0"], "why": why, "funding": q["fund"] / (2 * q["half"]),
                       "ret": max(0.0, out) / (2 * q["half"]) - 1})

    for t in range(len(idx)):
        keep = []
        for q in pos:
            j = q["j"]
            if np.isnan(pc[t, j]) or np.isnan(sc_[t, j]):
                close(q, q["ls"], q["lp"], t, "fine dati")
                continue
            if not np.isnan(fund[t, j]):
                q["fund"] += q["half"] * (q["lp"] / q["p0"]) * fund[t, j]  # short receives positive funding
            if hi[t, j] >= 2 * q["p0"]:  # short leg wiped out (1x collateral)
                close(q, sc_[t, j], 2 * q["p0"], t, "liquidazione")
                continue
            q["ls"], q["lp"] = sc_[t, j], pc[t, j]
            if t - q["t0"] >= hold:
                close(q, sc_[t, j], pc[t, j], t, "tempo")
                continue
            keep.append(q)
        pos = keep
        eq = cash + sum(sum(value(q, q["ls"], q["lp"])) for q in pos)
        daily.append(eq)
        free = SLOTS - len(pos)
        if free <= 0:
            continue
        row = sig[t]
        held = {q["j"] for q in pos}
        cand = [(row[j], j) for j in np.where(~np.isnan(row))[0] if j not in held]
        for _, j in sorted(cand, reverse=True)[:free]:
            if np.isnan(pc[t, j]) or np.isnan(sc_[t, j]) or pc[t, j] <= 0 or sc_[t, j] <= 0:
                continue
            r = rank[t, j]
            slip = 0.0005 if (not np.isnan(r) and r <= 30) else 0.0020
            cs, cp = cost_mult * (0.0010 + slip), cost_mult * (0.0005 + slip)
            stake = eq / SLOTS
            if stake > cash:
                break
            cash -= stake
            half = stake / 2
            # entry costs paid out of the slot
            half_s = half * (1 - cs)
            pos.append({"j": j, "t0": t, "s0": sc_[t, j], "p0": pc[t, j], "ls": sc_[t, j], "lp": pc[t, j],
                        "half": half, "fund": 0.0, "entry_cost": half * cp + (half - half_s), "cs": cs, "cp": cp,
                        "rec": {"date": idx[t], "coin": cols[j], "funding_signal": row[j]}})
    ser = pd.Series(daily, index=idx).pct_change().fillna(0.0)
    return ser, pd.DataFrame(trades)


def row(label, ser, tr) -> dict:
    ser = ser[ser.index >= START]
    si, so = ct.stats(ser[ser.index < SPLIT]), ct.stats(ser[ser.index >= SPLIT])
    lo, hi = ct.sharpe_ci(ser[ser.index >= SPLIT])
    tro = tr[tr.date >= SPLIT] if not tr.empty else tr
    return {"variante": label, "IS_CAGR_%": si.get("CAGR_%"), "OOS_CAGR_%": so.get("CAGR_%"),
            "OOS_Sharpe": so.get("Sharpe"), "OOS_Sharpe_IC95": f"[{lo:.2f}, {hi:.2f}]", "OOS_maxDD_%": so.get("maxDD_%"),
            "OOS_operazioni": len(tro), "OOS_vincenti_%": 100 * (tro.ret > 0).mean() if len(tro) else np.nan,
            "OOS_media_op_%": 100 * tro.ret.mean() if len(tro) else np.nan,
            "OOS_funding_medio_op_%": 100 * tro.funding.mean() if len(tro) else np.nan,
            "OOS_liquidazioni": int((tro.why == "liquidazione").sum()) if len(tro) else 0, "_lo": lo}


def main() -> None:
    r = Report("crypto_carry")
    r("# Studio storico: incassare il funding dell'hype senza scommettere sul prezzo (spot + short perpetuo, 1-3 giorni)")
    r("\n" + __doc__.split("PRE-REGISTERED")[0].split("\n\n", 1)[1].strip())
    r("\nPre-registrazione (testo originale):\n\n```\n" + __doc__.split("PRE-REGISTERED")[1].strip() + "\n```")
    fut = load_futures_daily()
    spot_set = set(usdt_symbols())
    cand = {s: spot_name(s, spot_set) for s in fut.symbol.unique()}
    cand = {k: v for k, v in cand.items() if v}
    spot = load_daily(only=sorted(set(cand.values())))
    # accept a pair only if the two price series move together
    fr = fut.pivot(index="date", columns="symbol", values="close").pct_change(fill_method=None)
    sr = spot.pivot(index="date", columns="symbol", values="close").pct_change(fill_method=None)
    pairs = {}
    for k, v in cand.items():
        if k in fr and v in sr:
            j = pd.concat([fr[k], sr[v]], axis=1).dropna()
            if len(j) >= 30 and j.corr().iloc[0, 1] >= 0.9:
                pairs[k] = v
    r(f"Perpetui: {fut.symbol.nunique()}; con una coppia spot Binance della stessa moneta: {len(cand)}; accettati "
      f"(correlazione >= 0,9): **{len(pairs)}**.")
    p = build(fut, spot, pairs)
    fu = p["funding"].where(p["universe"])
    for lab, a, b in (("2020-2021", START, SPLIT), ("2022-fine", SPLIT, p["close"].index.max() + pd.Timedelta(days=1))):
        x = fu[(fu.index >= a) & (fu.index < b)].stack().dropna()
        r(f"- {lab}: funding giornaliero nelle 100 più scambiate: medio {100 * x.mean():+.4f}%, mediano "
          f"{100 * x.median():+.4f}%; giorni >= 0,03%: {100 * (x >= 0.0003).mean():.1f}%, >= 0,10%: "
          f"{100 * (x >= 0.001).mean():.1f}%; negativi: {100 * (x < 0).mean():.1f}%.")
    rows, keep = [], []
    for rule in ("C0", "C1", "C2", "C3"):
        s = signals(p, rule)
        for hold in HOLDS:
            ser, tr = simulate(p, s, hold)
            rw = row(f"{rule}, {hold} giorni", ser, tr)
            print(rw, flush=True)
            rows.append(rw)
            if hold <= 3 and (rw["OOS_CAGR_%"] or -1) > 0:
                keep.append((rule, hold, s, ser, rw))
    tab = pd.DataFrame(rows)
    r("\n## Le regole pre-registrate")
    r.table(tab.drop(columns="_lo"))
    r(f"Positive fuori campione (tenute 1-3 giorni): **{len(keep)} su {3 * 4}**.")
    verdicts = []
    for rule, hold, s, ser, rw in keep:
        rows2 = [rw]
        for lab, s2, kw in (("costi doppi", s, {"cost_mult": 2.0}), ("entrata un giorno dopo", s.shift(1), {})):
            a, b = simulate(p, s2, hold, **kw)
            rows2.append(row(f"{rule}, {hold} giorni: {lab}", a, b))
        vt = pd.DataFrame(rows2)
        r(f"\n### {rule}, {hold} giorni")
        r.table(vt.drop(columns="_lo"))
        x = ser[ser.index >= START]
        y = ((1 + x).groupby(x.index.year).prod() - 1) * 100
        r("Anno per anno (%): " + ", ".join(f"{k} {v:+.1f}" for k, v in y.items()))
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
