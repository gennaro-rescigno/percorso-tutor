"""Study 'meme_trend': the trend filter on EXISTING memecoins (Binance perpetuals, 2021-2026, failed ones included).

The 50-day trend filter is the only rule that survived every check (BTC+ETH+SOL, and on 6 of 7 big coins including
DOGE). Memecoins have the most extreme runs (PEPE, WIF, BONK...) and the most extreme collapses (-90% and more),
which is the case where holding only while the price is above its average should help most. The rule and its 50
were fixed on BTC 2018-2021, so on memecoins the whole period is out of sample.

PRE-REGISTERED (written before looking at any result):
  * coins: the memecoin list below (written now, failures included: whoever is in the list and has a Binance USDT
    perpetual enters from its 50th candle, delisted contracts exit at their last price); a coin is "in the basket"
    while it has >= 50 candles of history and is still trading;
  * portfolio: each basket coin gets 1/N of the equity (N = basket size), held only while its close is above the
    average of its last 50 closes, otherwise that share stays in cash (USDC); shares re-set every 7 days; decisions
    at the candle close, executed at that close; costs 0.30% per side (on-chain swap of liquid memecoins or CEX
    fee + slippage);
  * variants: M1 daily candles, 50-day average; M2 daily, 20-day average; M3 4-hour candles, average of 50 candles
    (about 8 days, shorter holds); the benchmark is the same basket always held (same re-set, same costs);
  * checks for each variant: costs doubled (0.60% per side) and execution one candle late;
  * periods reported: 2021, 2022-2026 and the whole; per year; per coin (filter vs held); every round trip
    (count, length, winners, average, median, profit factor, share of the gains from the best 10%);
  * verdict "regge" only if, on 2022-2026: positive return, better than holding in both return and worst drawdown,
    95% block-bootstrap interval of the Sharpe above zero, and still positive with costs doubled and one candle late.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import crypto_trend as ct
from common import Report
from crypto_data import futures_symbols, load_futures_bars, load_futures_daily

MEMES = [
    "DOGEUSDT", "1000SHIBUSDT", "1000PEPEUSDT", "1000BONKUSDT", "1000FLOKIUSDT", "WIFUSDT", "BOMEUSDT", "MEWUSDT",
    "POPCATUSDT", "NEIROUSDT", "NEIROETHUSDT", "MEMEUSDT", "TRUMPUSDT", "MELANIAUSDT", "PNUTUSDT", "GOATUSDT",
    "ACTUSDT", "MOODENGUSDT", "FARTCOINUSDT", "CHILLGUYUSDT", "PEOPLEUSDT", "TURBOUSDT", "BRETTUSDT", "1000CATUSDT",
    "DOGSUSDT", "PONKEUSDT", "MYROUSDT", "1000RATSUSDT", "SPXUSDT", "1MBABYDOGEUSDT", "1000CHEEMSUSDT", "PENGUUSDT",
    "MUBARAKUSDT", "BANANAS31USDT", "1000WHYUSDT", "SLERFUSDT", "BANUSDT", "1000000MOGUSDT", "1000SATSUSDT",
    "BABYDOGEUSDT", "DEGENUSDT", "HIPPOUSDT", "SUNDOGUSDT", "LUCEUSDT", "KOMAUSDT", "BROCCOLI714USDT",
    "BROCCOLIF3BUSDT", "TUTUSDT", "JELLYJELLYUSDT", "FWOGUSDT", "GIGAUSDT", "MICHIUSDT", "ZEREBROUSDT", "AI16ZUSDT",
    "AIXBTUSDT", "GRIFFAINUSDT", "PIPPINUSDT", "VINEUSDT", "USELESSUSDT", "TROLLUSDT", "1000LUNCUSDT", "WENUSDT",
    "1000XUSDT", "DOGINMEUSDT", "MOTHERUSDT", "1000APUUSDT", "SIGMAUSDT", "RETARDIOUSDT", "NOTUSDT", "HMSTRUSDT",
    "CATIUSDT", "MEMEFIUSDT", "LADYSUSDT", "1000LADYSUSDT", "AIDOGEUSDT", "ELONUSDT", "SAMOUSDT", "BOMEUSDT",
]
COST = 0.003
RESET_DAYS = 7
START = pd.Timestamp("2021-01-01", tz="UTC")
SPLIT = ct.SPLIT


def panel(d: pd.DataFrame) -> pd.DataFrame:
    return d.pivot(index="date", columns="symbol", values="close").sort_index()


def simulate(close: pd.DataFrame, n: int, bars_per_day: int, cost: float = COST, delay: int = 0,
             always: bool = False) -> tuple[pd.Series, pd.DataFrame]:
    c = close.to_numpy()
    hist = close.notna().cumsum().to_numpy()
    ma = close.rolling(n, min_periods=n).mean().to_numpy()
    member = (hist >= n) & ~np.isnan(c)
    on = member if always else member & (c > ma)
    if delay:
        on = np.vstack([np.zeros((delay, on.shape[1]), bool), on[:-delay]]) & member
    idx, cols = close.index, close.columns
    T, N = c.shape
    units = np.zeros(N)
    last = np.full(N, np.nan)
    cash, eq_hist, trades = 1.0, [], []
    open_px = np.full(N, np.nan)
    open_t = np.full(N, -1)
    reset_every = RESET_DAYS * bars_per_day
    for t in range(T):
        px = c[t]
        alive = ~np.isnan(px)
        # delisted / no candle while held: out at the last price
        gone = (units > 0) & ~alive
        for j in np.where(gone)[0]:
            cash += units[j] * last[j] * (1 - cost)
            trades.append((idx[open_t[j]], idx[t], cols[j], open_px[j], last[j], t - open_t[j]))
            units[j] = 0.0
        last = np.where(alive, px, last)
        eq = cash + np.nansum(units * np.where(alive, px, 0.0))
        nb = int(member[t].sum())
        if nb:
            target = np.where(on[t], eq / nb, 0.0)
            cur = units * np.where(alive, px, 0.0)
            change = (on[t] != (units > 0)) & alive
            if t % reset_every == 0:
                change |= alive & on[t]
            for j in np.where(change)[0]:
                delta = target[j] - cur[j]
                if abs(delta) < 1e-12:
                    continue
                if delta < 0:
                    sell = min(-delta, cur[j])
                    cash += sell * (1 - cost)
                    units[j] -= sell / px[j]
                    if target[j] == 0:
                        trades.append((idx[open_t[j]], idx[t], cols[j], open_px[j], px[j], t - open_t[j]))
                        units[j] = 0.0
                else:
                    buy = min(delta, cash)
                    if buy <= 0:
                        continue
                    if units[j] == 0:
                        open_px[j], open_t[j] = px[j], t
                    cash -= buy
                    units[j] += buy * (1 - cost) / px[j]
        eq_hist.append(cash + np.nansum(units * np.where(alive, px, 0.0)))
    ser = pd.Series(eq_hist, index=idx)
    if bars_per_day > 1:  # daily returns for the statistics
        ser = ser.groupby(ser.index.normalize()).last()
    tr = pd.DataFrame(trades, columns=["entrata", "uscita", "moneta", "px_in", "px_out", "candele"])
    if not tr.empty:
        tr["ret"] = tr.px_out / tr.px_in * (1 - cost) ** 2 - 1
        tr["giorni"] = tr.candele / bars_per_day
    return ser.pct_change().fillna(0.0), tr


def period_rows(label: str, ser: pd.Series) -> dict:
    out = {"variante": label}
    for name, a, b in (("2021", START, SPLIT), ("2022-2026", SPLIT, None), ("tutto", START, None)):
        x = ser[(ser.index >= a) & ((ser.index < b) if b is not None else True)]
        s = ct.stats(x)
        out[f"{name}_CAGR_%"] = s.get("CAGR_%")
        out[f"{name}_maxDD_%"] = s.get("maxDD_%")
        if name == "2022-2026":
            lo, hi = ct.sharpe_ci(x)
            out["2022-2026_Sharpe"] = s.get("Sharpe")
            out["2022-2026_Sharpe_IC95"] = f"[{lo:.2f}, {hi:.2f}]"
            out["_lo"] = lo
    return out


def trade_stats(tr: pd.DataFrame) -> dict:
    if tr.empty:
        return {"operazioni": 0}
    t = tr[tr.entrata >= SPLIT]
    if t.empty:
        return {"operazioni": 0}
    win, lose = t[t.ret > 0], t[t.ret <= 0]
    top = t.ret.sort_values(ascending=False)
    k = max(1, int(round(len(t) * 0.1)))
    gains = win.ret.sum()
    return {"operazioni_2022+": len(t), "giorni_mediani": round(float(t.giorni.median()), 1),
            "vincenti_%": round(100 * len(win) / len(t), 1), "media_%": round(100 * t.ret.mean(), 2),
            "mediana_%": round(100 * t.ret.median(), 2),
            "profit_factor": round(gains / -lose.ret.sum(), 2) if len(lose) and lose.ret.sum() < 0 else np.inf,
            "quota_dal_10%_migliore": round(100 * top.head(k).clip(lower=0).sum() / gains, 1) if gains > 0 else np.nan}


def main() -> None:
    r = Report("meme_trend")
    r("# Studio storico: il filtro di trend sulle memecoin già quotate (perpetui Binance, 2021-2026)")
    r("\nPre-registrazione (testo originale):\n\n```\n" + __doc__.split("PRE-REGISTERED")[1].strip() + "\n```")
    avail = set(futures_symbols())
    memes = sorted({m for m in MEMES if m in avail})
    r(f"Memecoin dell'elenco con un perpetuo Binance: **{len(memes)}**: {', '.join(m.replace('USDT', '') for m in memes)}.")
    daily = load_futures_daily()
    cd = panel(daily[daily.symbol.isin(memes)])
    cd = cd[cd.index >= START - pd.Timedelta(days=60)]
    last = cd.index.max()
    dead = [m for m in cd.columns if cd[m].last_valid_index() < last - pd.Timedelta(days=7)]
    r(f"Dati giornalieri fino al {last.date()}; chiusi o delistati prima della fine: {len(dead)} "
      f"({', '.join(m.replace('USDT', '') for m in dead) or 'nessuno'}).")
    c4 = panel(load_futures_bars(memes, "4h"))
    c4 = c4[c4.index >= START - pd.Timedelta(days=30)]
    variants = {"M1 giornaliero, media 50": (cd, 50, 1), "M2 giornaliero, media 20": (cd, 20, 1),
                "M3 4 ore, media di 50 candele": (c4, 50, 6)}
    rows, trows, verdicts = [], [], []
    for name, (cl, n, bpd) in variants.items():
        base, tr = simulate(cl, n, bpd)
        hold, _ = simulate(cl, n, bpd, always=True)
        dbl, _ = simulate(cl, n, bpd, cost=2 * COST)
        late, _ = simulate(cl, n, bpd, delay=1)
        rb, rh, rd, rl = (period_rows(f"{name}{s}", x) for s, x in
                          (("", base), (": sempre tenute", hold), (": costi doppi", dbl), (": una candela dopo", late)))
        rows += [rb, rh, rd, rl]
        trows.append({"variante": name, **trade_stats(tr)})
        ok = ((rb["2022-2026_CAGR_%"] or -1) > 0 and (rb["2022-2026_CAGR_%"] or -1) > (rh["2022-2026_CAGR_%"] or 0)
              and (rb["2022-2026_maxDD_%"] or -100) > (rh["2022-2026_maxDD_%"] or 0) and rb["_lo"] > 0
              and (rd["2022-2026_CAGR_%"] or -1) > 0 and (rl["2022-2026_CAGR_%"] or -1) > 0)
        verdicts.append((name, "regge" if ok else "non regge"))
        if name.startswith("M1"):
            x = base[base.index >= START]
            h = hold[hold.index >= START]
            y = pd.DataFrame({"filtro_%": ((1 + x).groupby(x.index.year).prod() - 1) * 100,
                              "sempre_tenute_%": ((1 + h).groupby(h.index.year).prod() - 1) * 100})
            m1_years, m1_tr = y, tr
    tab = pd.DataFrame(rows).drop(columns="_lo")
    r("\n## Portafogli (rendimento annuo composto e perdita massima)")
    r.table(tab)
    r("## Operazioni (andata e ritorno, entrate dal 2022)")
    r.table(pd.DataFrame(trows))
    r("## M1 anno per anno")
    r.table(m1_years.reset_index().rename(columns={"date": "anno", "index": "anno"}))
    r("## M1 per moneta (operazioni dal 2022: rendimento composto)")
    if not m1_tr.empty:
        g = m1_tr[m1_tr.entrata >= SPLIT].groupby("moneta")
        per = pd.DataFrame({"operazioni": g.size(), "vincenti": g.ret.apply(lambda s: int((s > 0).sum())),
                            "composto_%": g.ret.apply(lambda s: 100 * (np.prod(1 + s) - 1))}).sort_values("composto_%")
        r.table(per.reset_index())
    r("\n## Verdetto")
    for k, v in verdicts:
        r(f"- {k}: **{v}**")
    r.save()


if __name__ == "__main__":
    main()
