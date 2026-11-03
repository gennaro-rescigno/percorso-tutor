"""Study 'crypto_daily2': is H2 (hype burst while BTC is in an uptrend, held 2-3 days) robust or luck?

crypto_daily found H2 the only short-trade rule positive in both periods (+11.7%/yr out of sample at 3 days) with
a very wide interval. Written before running, every variant is reported (none is picked):
  * thresholds around the original: day return >= 5% / 10% / 15%, volume >= 2x / 3x / 5x the 30-day average;
  * BTC filter on the 50- or 100-day average; stop at -10% / -15% / -25%;
  * costs doubled; entry one day late (the close after the signal day);
  * memecoins only vs everything else;
  * per-year results of the original H2 (3 days).
"Robust" would need most neighbouring variants positive out of sample and the late entry still positive.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import crypto_daily as cd
import crypto_trend as ct
from common import Report
from crypto_data import load_daily

MEMES = {"DOGEUSDT", "SHIBUSDT", "PEPEUSDT", "WIFUSDT", "BONKUSDT", "FLOKIUSDT", "BOMEUSDT", "1000SATSUSDT",
         "MEMEUSDT", "TRUMPUSDT", "PEOPLEUSDT", "TURBOUSDT", "NEIROUSDT", "POPCATUSDT", "BRETTUSDT", "MOGUSDT",
         "PNUTUSDT", "ACTUSDT", "GOATUSDT", "BABYDOGEUSDT", "1000CATUSDT", "DOGSUSDT", "MEWUSDT", "BANANAS31USDT"}


def h2(p, ret_min=0.10, vol_min=3.0, btc_n=50, only=None, delay=0):
    c = p["close"]
    btc = c["BTCUSDT"]
    up = btc > btc.rolling(btc_n, min_periods=btc_n).mean()
    m = (p["r1"] >= ret_min) & (p["volx"] >= vol_min) & p["universe"]
    if only in ("meme", "nomeme"):
        is_meme = np.array([k in MEMES for k in c.columns])
        keep = is_meme if only == "meme" else ~is_meme
        m &= pd.DataFrame(np.broadcast_to(keep, c.shape), index=c.index, columns=c.columns)
    score = cd.rows_where(p["volx"].where(m), up)
    return score.shift(delay) if delay else score


def run(p, score, hold=3, stop=0.15, cost_mult=1.0):
    old_stop = cd.STOP
    cd.STOP = stop
    try:
        ser, tr = cd.simulate(p, score, hold)
    finally:
        cd.STOP = old_stop
    if cost_mult != 1.0 and not tr.empty:
        extra = (cost_mult - 1) * tr.cost  # per side, on a 10% slot
        # approximate: each trade pays the extra cost twice on its slot (entry + exit)
        by_day = pd.Series(2 * extra.to_numpy() * 0.1, index=pd.to_datetime(tr.date)).groupby(level=0).sum()
        ser = ser.sub(by_day.reindex(ser.index).fillna(0.0), fill_value=0.0)
    return ser, tr


def row(label, ser, tr):
    ser = ser[ser.index >= ct.START]
    si, so = ct.stats(ser[ser.index < ct.SPLIT]), ct.stats(ser[ser.index >= ct.SPLIT])
    lo, hi = ct.sharpe_ci(ser[ser.index >= ct.SPLIT])
    tro = tr[tr.date >= ct.SPLIT] if not tr.empty else tr
    return {"variante": label, "IS_CAGR_%": si.get("CAGR_%"), "OOS_CAGR_%": so.get("CAGR_%"), "OOS_Sharpe": so.get("Sharpe"),
            "OOS_Sharpe_IC95": f"[{lo:.2f}, {hi:.2f}]", "OOS_maxDD_%": so.get("maxDD_%"), "OOS_operazioni": len(tro),
            "OOS_media_op_%": 100 * tro.ret.mean() if len(tro) else np.nan}


def main() -> None:
    r = Report("crypto_daily2")
    r("# Robustezza di H2: hype con BTC in salita, tenuta 2-3 giorni (Binance 2018-2026)")
    r("\n```\n" + __doc__.split("\n\n", 1)[1].strip() + "\n```")
    p = cd.build(load_daily())
    rows = []
    base = h2(p)
    for hold in (2, 3):
        ser, tr = run(p, base, hold)
        rows.append(row(f"H2 originale, {hold} giorni", ser, tr))
        if hold == 3:
            ser3, tr3 = ser, tr
    for rmin in (0.05, 0.10, 0.15):
        for vmin in (2.0, 3.0, 5.0):
            if (rmin, vmin) == (0.10, 3.0):
                continue
            ser, tr = run(p, h2(p, rmin, vmin), 3)
            rows.append(row(f"soglie: prezzo >= {int(rmin * 100)}%, volume >= {vmin:g}x", ser, tr))
    ser, tr = run(p, h2(p, btc_n=100), 3)
    rows.append(row("filtro BTC a 100 giorni", ser, tr))
    for st in (0.10, 0.25):
        ser, tr = run(p, base, 3, stop=st)
        rows.append(row(f"stop a -{int(st * 100)}%", ser, tr))
    ser, tr = run(p, base, 3, cost_mult=2.0)
    rows.append(row("costi doppi", ser, tr))
    ser, tr = run(p, h2(p, delay=1), 3)
    rows.append(row("entrata un giorno dopo", ser, tr))
    for only, lab in (("meme", "solo memecoin"), ("nomeme", "senza memecoin")):
        ser, tr = run(p, h2(p, only=only), 3)
        rows.append(row(lab, ser, tr))
    tab = pd.DataFrame(rows)
    r.table(tab)
    pos = int((tab["OOS_CAGR_%"] > 0).sum())
    r(f"Varianti positive fuori campione: **{pos} su {len(tab)}**.")
    s = ser3[ser3.index >= ct.START]
    yearly = ((1 + s).groupby(s.index.year).prod() - 1) * 100
    r("\n## H2 originale (3 giorni), anno per anno (%)")
    r.table(pd.DataFrame({"anno": yearly.index, "rendimento_%": yearly.values}))
    r.save()


if __name__ == "__main__":
    main()
