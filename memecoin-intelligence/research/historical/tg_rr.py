"""Study 'tg_rr': the user's rule on the @BINANCE_CRYPTO_SIGNALS_ML signals - stop beyond the last opposite candle
before the impulse, target at 1:1 (risk = reward).

The user drew five 1:1 trades on Binance charts after the fact and found them very profitable. Five examples chosen by
looking at the chart cannot show an edge, so the same rule is applied mechanically to EVERY signal of the channel.

PRE-REGISTERED (written before looking at any result):
  * signals: every LONG/SHORT post of the channel on a Binance USDT-M perpetual (Oct 9 - Nov 6 2026), 1-minute candles
    (data.binance.vision); a signal needs candles from 60 minutes before the post to 24 hours after;
  * the impulse and the stop, from the candles BEFORE the post only (what was visible when the signal arrived):
      LONG: the impulse starts at the lowest low of the last K minutes; the stop is the low of the last red candle
      (close < open) at or before that minute (the lowest low itself if there is no red candle);
      SHORT: mirror - highest high of the last K minutes, high of the last green candle at or before it;
    K = 30 minutes (main), 15 and 60 (checks);
  * entry: (M) market at the open of the first minute after the post + 0.02% slippage; (L) limit at the written entry,
    valid 60 minutes; stop distance d measured from the fill; trades with d below 0.3% or above 10% are skipped
    (counted);
  * target: entry + d for a long, entry - d for a short (1:1); checks with 1.5:1 and 2:1; close after 24 hours at most;
    a minute touching both stop and target counts as a stop (conservative; counted);
  * costs: 0.05% fee per side, 0.02% slippage on market entry and on the stop; funding not counted;
  * comparison: the same rule at a random minute in the 3 days before the post (seed 11): does the channel's timing
    add anything to the 1:1 rule?
  * results per trade (no leverage), with the 95% bootstrap interval, separately for Oct 9-30 and Oct 31 - Nov 6;
    break-even needs more than 50% winners plus the costs.
"""

from __future__ import annotations

import concurrent.futures as cf
import json
import urllib.request
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from common import UA, Report
from crypto_data import list_prefixes
from loop_curve import boot_mean
from tg_backtest import RAW, day_candles, parse

FEE, SLIP, HOLD = 0.0005, 0.0002, 1440
SPLIT = pd.Timestamp("2026-10-31", tz="UTC")


def stop_level(o, h, l, c, i0, side, K):
    a = max(0, i0 - K)
    if i0 - a < 3:
        return None
    if side == "LONG":
        j = a + int(np.argmin(l[a:i0]))
        for q in range(j, a - 1, -1):
            if c[q] < o[q]:
                return l[q]
        return l[j]
    j = a + int(np.argmax(h[a:i0]))
    for q in range(j, a - 1, -1):
        if c[q] > o[q]:
            return h[q]
    return h[j]


def trade(o, h, l, c, i0, side, entry_written, K, rr, mode):
    """(net return, ending, minutes, ambiguous) | ('skip', reason) | None when the limit order is never filled."""
    s = 1.0 if side == "LONG" else -1.0
    st = stop_level(o, h, l, c, i0, side, K)
    if st is None:
        return "skip", "storico insufficiente"
    if mode == "M":
        k, px = i0, o[i0] * (1 + s * SLIP)
    else:
        k = None
        for j in range(i0, min(len(o), i0 + 60)):
            if (s > 0 and l[j] <= entry_written) or (s < 0 and h[j] >= entry_written):
                k, px = j, (min(o[j], entry_written) if s > 0 else max(o[j], entry_written))
                break
        if k is None:
            return None
    d = s * (px - st) / px
    if not (0.003 <= d <= 0.10):
        return "skip", "stop troppo vicino o troppo lontano"
    tp = px * (1 + s * rr * d)
    amb = False
    for j in range(k, min(len(o), k + HOLD)):
        hs = (s > 0 and l[j] <= st) or (s < 0 and h[j] >= st)
        ht = (s > 0 and h[j] >= tp) or (s < 0 and l[j] <= tp)
        if hs and ht:
            amb = True
        if hs:
            fill = (min(o[j], st) if s > 0 else max(o[j], st)) * (1 - s * SLIP)
            return s * (fill / px - 1) - 2 * FEE, "stop", j - k, amb
        if ht:
            return s * (tp / px - 1) - 2 * FEE, "obiettivo", j - k, amb
    j = min(len(o), k + HOLD) - 1
    return s * (c[j] / px - 1) - 2 * FEE, "24 ore", j - k, amb


def summary(x: np.ndarray) -> dict:
    x = x[~np.isnan(x)]
    if len(x) == 0:
        return {"n": 0}
    lo, hi, _ = boot_mean(x) if len(x) >= 30 else (np.nan, np.nan, np.nan)
    w, ls = x[x > 0], x[x <= 0]
    return {"n": len(x), "media_%": 100 * x.mean(), "IC95_basso_%": 100 * lo, "IC95_alto_%": 100 * hi,
            "vincenti_%": 100 * len(w) / len(x), "vincita_media_%": 100 * w.mean() if len(w) else np.nan,
            "perdita_media_%": 100 * ls.mean() if len(ls) else np.nan,
            "profit_factor": w.sum() / -ls.sum() if ls.sum() < 0 else np.inf, "somma_%": 100 * x.sum()}


def main() -> None:
    r = Report("tg_rr")
    r("# La tua regola sui segnali di @BINANCE_CRYPTO_SIGNALS_ML: stop oltre l'ultima candela opposta, obiettivo 1:1")
    r("\nPre-registrazione (testo originale):\n\n```\n" + __doc__.split("PRE-REGISTERED")[1].strip() + "\n```")
    with urllib.request.urlopen(urllib.request.Request(RAW, headers=UA), timeout=60) as resp:
        sig = parse(json.loads(resp.read()))
    perp = {p.rstrip("/").split("/")[-1] for p in list_prefixes("data/futures/um/daily/klines/")}
    sig = sig[sig.symbol.isin(perp)].copy()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    need = {(x.symbol, (x.time + timedelta(days=dd)).strftime("%Y-%m-%d")) for _, x in sig.iterrows() for dd in range(-4, 3)}
    need = sorted(k for k in need if k[1] < today)
    print(f"file di candele: {len(need)}", flush=True)
    candles: dict[str, list] = {}
    with cf.ThreadPoolExecutor(max_workers=24) as ex:
        for (sym, _), df in zip(need, ex.map(lambda k: day_candles(*k), need)):
            if df is not None:
                candles.setdefault(sym, []).append(df)
    data = {s: pd.concat(v).drop_duplicates("t").sort_values("t").reset_index(drop=True) for s, v in candles.items()}
    rng = np.random.default_rng(11)
    configs = [(30, 1.0, "M"), (30, 1.0, "L"), (15, 1.0, "M"), (60, 1.0, "M"), (30, 1.5, "M"), (30, 2.0, "M")]
    rows, skips = [], {}
    for _, x in sig.iterrows():
        d = data.get(x.symbol)
        if d is None:
            continue
        t, o, h, l, c = (d[k].to_numpy() for k in ("t", "o", "h", "l", "c"))
        post = int(x.time.timestamp())
        i0 = int(np.searchsorted(t, post, side="right"))
        if i0 < 60 or i0 + HOLD + 60 >= len(t) or t[i0] - post > 120 or t[i0] - t[i0 - 60] > 3700 \
                or t[i0 + HOLD + 60] - t[i0] > (HOLD + 60) * 60 + 600:
            continue
        rec = {"time": x.time, "symbol": x.symbol, "side": x.side,
               "periodo": "9-30 ottobre" if x.time < SPLIT else "31 ottobre - 6 novembre"}
        for K, rr, mode in configs:
            key = f"K{K}_rr{rr:g}_{mode}"
            res = trade(o, h, l, c, i0, x.side, x.entry, K, rr, mode)
            if res is None:
                rec[key] = np.nan
            elif res[0] == "skip":
                rec[key] = np.nan
                skips[(key, res[1])] = skips.get((key, res[1]), 0) + 1
            else:
                rec[key], rec[key + "_fine"], rec[key + "_min"], rec[key + "_amb"] = res
        ri = int(np.searchsorted(t, post + int(rng.integers(-3 * 86400, -3600)), side="right"))
        if 60 <= ri and ri + HOLD < len(t) and t[ri + HOLD] - t[ri - 60] <= (HOLD + 60) * 60 + 600:
            res = trade(o, h, l, c, ri, x.side, o[ri], 30, 1.0, "M")
            rec["caso"] = res[0] if isinstance(res, tuple) and res[0] != "skip" else np.nan
        rows.append(rec)
    bt = pd.DataFrame(rows)
    r(f"Segnali con candele complete (60 minuti prima, 24 ore dopo): **{len(bt):,}** "
      f"(9-30 ottobre {int((bt.periodo == '9-30 ottobre').sum()):,}, 31 ottobre - 6 novembre "
      f"{int((bt.periodo != '9-30 ottobre').sum()):,}).")
    labels = {"K30_rr1_M": "regola principale: 30 min, 1:1, entrata subito",
              "K30_rr1_L": "30 min, 1:1, limite al prezzo scritto", "K15_rr1_M": "15 min, 1:1, entrata subito",
              "K60_rr1_M": "60 min, 1:1, entrata subito", "K30_rr1.5_M": "30 min, 1,5:1, entrata subito",
              "K30_rr2_M": "30 min, 2:1, entrata subito"}
    r("\n## Risultato per operazione (senza leva, commissioni comprese)")
    out = []
    for key, lab in labels.items():
        for per in ("9-30 ottobre", "31 ottobre - 6 novembre", "tutto"):
            sub = bt if per == "tutto" else bt[bt.periodo == per]
            row = {"regola": lab, "periodo": per, **summary(sub[key].to_numpy(np.float64))}
            if key + "_min" in sub:
                row["minuti_medi"] = sub[key + "_min"].mean()
                row["minuti_ambigui"] = int(sub.get(key + "_amb", pd.Series(dtype=bool)).fillna(False).astype(bool).sum())
            out.append(row)
    for per in ("9-30 ottobre", "31 ottobre - 6 novembre", "tutto"):
        sub = bt if per == "tutto" else bt[bt.periodo == per]
        out.append({"regola": "stessa regola a un minuto CASUALE (confronto)", "periodo": per,
                    **summary(sub["caso"].to_numpy(np.float64))})
    r.table(pd.DataFrame(out))
    r("Operazioni saltate (stop non valido): " + "; ".join(f"{k[0]} {k[1]}: {v}" for k, v in sorted(skips.items())))
    r("\n## Come finiscono (regola principale)")
    r.table(bt["K30_rr1_M_fine"].value_counts(normalize=True).mul(100).rename("quota_%").reset_index())
    r("\n## Per direzione (regola principale)")
    r.table(pd.DataFrame([{"direzione": g, **summary(d_["K30_rr1_M"].to_numpy(np.float64))} for g, d_ in bt.groupby("side")]))
    r("\n## Con la leva (regola principale, media per operazione sul margine)")
    m = np.nanmean(bt["K30_rr1_M"].to_numpy(np.float64))
    r(", ".join(f"{lev}x: {100 * m * lev:+.2f}%" for lev in (5, 10, 20)))
    bt.to_csv(r.path.with_name("tg_rr_trades.csv"), index=False)
    r.save()


if __name__ == "__main__":
    main()
