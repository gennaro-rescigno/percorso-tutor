"""Study 'tg_backtest': do the signals of the Telegram channel @BINANCE_CRYPTO_SIGNALS_ML make money?

Data: the channel's public posts (downloaded by tg_probe; Sep 13 - Nov 7 2026) and Binance USDT-M perpetual 1-minute
candles (data.binance.vision, public archive). Every signal is replayed minute by minute from the moment it was
posted. Caveat stated in the report: 41% of the channel's message numbers are missing (deleted or not public); if
deleted posts were losing calls, the visible record is biased in the channel's favour.

PRE-REGISTERED (written before looking at any result):
  * a signal = a post with LONG/SHORT, a USDT pair, Entry, TP1 and TP2 (Stop when written); the pair must be a
    Binance USDT-M perpetual; signals whose 7 days after the post are not fully in the archive are left out;
  * entry: (M) at the open of the first minute after the post, plus 0.02% slippage; (L) a limit order at the
    written Entry, valid 60 minutes, filled at the first minute that touches it (at that minute's open if better);
  * exits, all closed after 7 days at the latest:
      V1 as written: half at TP1, half at TP2, stop as written (posts without a stop: -3%, the channel's own earlier
         default);
      V2 V1 plus the stop moved to the entry after TP1 (the channel's later instruction);
      V3 no stop before TP1, half at TP1, then the rest with the stop at the entry, otherwise held to 7 days;
      V4 everything at TP1 with the V1 stop (the "TP1 hit = win" reading);
    when one minute touches both a stop and a target, the stop counts first (conservative; the count is reported);
  * (correction after the first run, rules unchanged: posts without a written stop carried NaN, which the code
    read as a stop that never triggers; the -3% default now applies as written above);
  * costs: 0.05% taker fee per side and 0.02% slippage on market fills (entry M and stops); funding not counted
    (the average holding time is reported);
  * comparison: the same pairs, sides and exits with the entry at a random minute in the 3 days BEFORE the post
    (seed 7; before, so that the 7-day hold fits in the downloaded candles):
    does the timing of the signal add anything over chance?
  * results per trade (no leverage): mean, 95% bootstrap interval, median, winners, profit factor, how trades end;
    by period (with / without a written stop), side, month and score; leverage multiplies both gains and losses
    (and without a stop a -10% move wipes out a 10x position).
"""

from __future__ import annotations

import concurrent.futures as cf
import io
import json
import re
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from common import UA, Report
from crypto_data import FILES, list_prefixes
from loop_curve import boot_mean

CHANNEL = "BINANCE_CRYPTO_SIGNALS_ML"
RAW = f"https://raw.githubusercontent.com/gennaro-rescigno/percorso-tutor/research-results/tg_{CHANNEL.lower()}_raw.json"
FEE, SLIP, HOLD_MIN = 0.0005, 0.0002, 7 * 1440
MIN_TIME = None  # set by tg_backtest2 (out-of-sample check on later signals)
REPORT_NAME = "tg_backtest"
TITLE_EXTRA = ""
SIG_RE = re.compile(r"\b(LONG|SHORT)\s+([A-Z0-9]+USDT)\b")


def num(pattern: str, text: str) -> float | None:
    m = re.search(pattern, text)
    return float(m.group(1)) if m else None


def parse(posts: list[dict]) -> pd.DataFrame:
    rows = []
    for p in posts:
        t = p.get("text") or ""
        m = SIG_RE.search(t)
        if not m:
            continue
        entry, tp1, tp2 = num(r"Entry:\s*([0-9.]+)", t), num(r"TP1:\s*([0-9.]+)", t), num(r"TP2:\s*([0-9.]+)", t)
        if not (entry and tp1 and tp2):
            continue
        rows.append({"id": p["id"], "time": pd.Timestamp(p["date"]).tz_convert("UTC"), "side": m.group(1),
                     "symbol": m.group(2), "entry": entry, "tp1": tp1, "tp2": tp2,
                     "stop": num(r"Stop:\s*([0-9.]+)", t), "score": num(r"Score:\s*(\d+)", t)})
    return pd.DataFrame(rows)


def day_candles(sym: str, day: str) -> pd.DataFrame | None:
    url = f"{FILES}/data/futures/um/daily/klines/{sym}/1m/{sym}-1m-{day}.zip"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
            z = zipfile.ZipFile(io.BytesIO(r.read()))
        with z.open(z.namelist()[0]) as f:
            df = pd.read_csv(f, header=None, usecols=range(5))
    except Exception:
        return None
    if not str(df.iloc[0, 0]).isdigit():
        df = df.iloc[1:]
    df = df.astype(float)
    df.columns = ["t", "o", "h", "l", "c"]
    df["t"] = (df.t.where(df.t < 1e14, df.t // 1000) // 1000).astype(np.int64)
    return df


def simulate(o, h, l, c, i0, side, entry_px, tp1, tp2, stop, variant, mode):
    """Returns (net return, how it ended, minutes held, ambiguous-minute flag) or None if never filled."""
    s = 1.0 if side == "LONG" else -1.0
    n = len(o)
    if stop is not None and stop != stop:  # NaN = no stop written (the -3% default applies)
        stop = None
    # ---- entry
    if mode == "M":
        if i0 >= n:
            return None
        k, px = i0, o[i0] * (1 + s * SLIP)
        cost_in = FEE
    else:
        k = None
        for j in range(i0, min(n, i0 + 60)):
            if (s > 0 and l[j] <= entry_px) or (s < 0 and h[j] >= entry_px):
                k = j
                px = min(o[j], entry_px) if s > 0 else max(o[j], entry_px)
                break
        if k is None:
            return None
        cost_in = FEE
    st = stop if stop else px * (1 - s * 0.03)
    if variant == "V3":
        st = None
    half_done, realized, amb = False, 0.0, False
    end = min(n, k + HOLD_MIN)

    def ret(exit_px: float) -> float:
        return s * (exit_px / px - 1)

    for j in range(k, end):
        hit_stop = st is not None and ((s > 0 and l[j] <= st) or (s < 0 and h[j] >= st))
        t1 = (s > 0 and h[j] >= tp1) or (s < 0 and l[j] <= tp1)
        t2 = (s > 0 and h[j] >= tp2) or (s < 0 and l[j] <= tp2)
        if hit_stop and (t1 or t2):
            amb = True
        if hit_stop:  # conservative: the stop first
            fill = (min(o[j], st) if s > 0 else max(o[j], st)) * (1 - s * SLIP)
            share = 0.5 if half_done else 1.0
            how = "stop dopo TP1" if half_done else "stop"
            return realized + share * ret(fill) - cost_in - FEE, how, j - k, amb
        if variant == "V4" and t1:
            return ret(tp1) - cost_in - FEE, "TP1", j - k, amb
        if not half_done and t1:
            half_done = True
            realized += 0.5 * ret(tp1)
            if variant in ("V2", "V3"):
                st = px
            if t2:
                return realized + 0.5 * ret(tp2) - cost_in - FEE, "TP2", j - k, amb
            continue
        if half_done and t2:
            return realized + 0.5 * ret(tp2) - cost_in - FEE, "TP2", j - k, amb
    share = 0.5 if half_done else 1.0
    return realized + share * ret(c[end - 1]) - cost_in - FEE, "tempo scaduto", end - 1 - k, amb


def summarize(df: pd.DataFrame, col: str) -> dict:
    x = df[col].dropna().to_numpy()
    if len(x) == 0:
        return {"n": 0}
    lo, hi, _ = boot_mean(x) if len(x) >= 30 else (np.nan, np.nan, np.nan)
    w, ls = x[x > 0], x[x <= 0]
    return {"n": len(x), "media_%": 100 * x.mean(), "IC95_basso_%": 100 * lo, "IC95_alto_%": 100 * hi,
            "mediana_%": 100 * np.median(x), "vincenti_%": 100 * len(w) / len(x),
            "vincita_media_%": 100 * w.mean() if len(w) else np.nan, "perdita_media_%": 100 * ls.mean() if len(ls) else np.nan,
            "profit_factor": w.sum() / -ls.sum() if ls.sum() < 0 else np.inf, "somma_%": 100 * x.sum()}


def main() -> None:
    r = Report(REPORT_NAME)
    r(f"# Backtest dei segnali del canale Telegram @{CHANNEL} (Binance futures, candele da 1 minuto){TITLE_EXTRA}")
    r("\nPre-registrazione (testo originale):\n\n```\n" + __doc__.split("PRE-REGISTERED")[1].strip() + "\n```")
    with urllib.request.urlopen(urllib.request.Request(RAW, headers=UA), timeout=60) as resp:
        posts = json.loads(resp.read())
    ids = sorted(p["id"] for p in posts)
    sig = parse(posts)
    r(f"Messaggi visibili: {len(posts):,} (id da {ids[0]} a {ids[-1]}, mancanti {ids[-1] - ids[0] + 1 - len(ids):,}); "
      f"segnali riconosciuti: **{len(sig):,}** ({(sig.side == 'LONG').sum():,} LONG, {(sig.side == 'SHORT').sum():,} SHORT; "
      f"con stop scritto {sig.stop.notna().sum():,}, senza {sig.stop.isna().sum():,}); coppie diverse: {sig.symbol.nunique()}.")
    # missing message numbers over time (deleted or not public posts)
    s_ids = pd.Series(sorted(ids))
    gaps = pd.DataFrame({"id": s_ids, "gap": s_ids.diff().fillna(1) - 1})
    by_week = pd.DataFrame([{**p} for p in posts]).assign(week=lambda d: pd.to_datetime(d.date).dt.strftime("%G-W%V"))
    wk = by_week.merge(gaps, on="id").groupby("week").agg(visibili=("id", "size"), mancanti_prima=("gap", "sum")).reset_index()
    r("\n## Numeri di messaggio mancanti per settimana (cancellati o non pubblici)")
    r.table(wk)
    # daily listing: pairs listed in the last weeks have no monthly file yet
    perp = {p.rstrip("/").split("/")[-1] for p in list_prefixes("data/futures/um/daily/klines/")}
    sig["su_binance"] = sig.symbol.isin(perp)
    r(f"Segnali su coppie che esistono come perpetui USDT-M su Binance: {sig.su_binance.sum():,} su {len(sig):,} "
      f"(non trovate: {', '.join(sorted(set(sig.symbol[~sig.su_binance]))[:30]) or 'nessuna'}).")
    sig = sig[sig.su_binance].copy()
    if MIN_TIME:
        sig = sig[sig.time >= pd.Timestamp(MIN_TIME, tz="UTC")].copy()
        r(f"Solo i segnali dal {MIN_TIME}: {len(sig):,}; tenuta massima {HOLD_MIN // 60} ore.")
    # candles needed: each signal's day -3 .. +8 (random baseline and the 7-day hold)
    need = set()
    for _, x in sig.iterrows():
        for dd in range(-3, 9):
            need.add((x.symbol, (x.time + timedelta(days=dd)).strftime("%Y-%m-%d")))
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    need = {k for k in need if k[1] < today}
    print(f"file di candele da scaricare: {len(need)}", flush=True)
    candles: dict[str, list[pd.DataFrame]] = {}
    with cf.ThreadPoolExecutor(max_workers=24) as ex:
        for (sym, day), df in zip(sorted(need), ex.map(lambda k: day_candles(*k), sorted(need))):
            if df is not None:
                candles.setdefault(sym, []).append(df)
    data = {s: pd.concat(v).drop_duplicates("t").sort_values("t").reset_index(drop=True) for s, v in candles.items()}
    rng = np.random.default_rng(7)
    rows = []
    for _, x in sig.iterrows():
        d = data.get(x.symbol)
        if d is None:
            continue
        t, o, h, l, c = (d[k].to_numpy() for k in ("t", "o", "h", "l", "c"))
        post_s = int(x.time.timestamp())
        i0 = int(np.searchsorted(t, post_s, side="right"))  # first minute that opens after the post
        if i0 >= len(t) or t[i0] - post_s > 120 or i0 + HOLD_MIN + 60 >= len(t) or t[i0 + HOLD_MIN + 60] - t[i0] > (HOLD_MIN + 60) * 60 + 600:
            continue  # no candles right after the post, or the 7 days are not complete
        rec = {"id": x.id, "time": x.time, "symbol": x.symbol, "side": x.side, "score": x.score,
               "periodo": "con stop scritto" if pd.notna(x.stop) else "senza stop scritto",
               "scarto_entrata_%": 100 * (o[i0] / x.entry - 1)}
        rand_i = int(np.searchsorted(t, post_s + int(rng.integers(-3 * 86400, 0)), side="right"))
        rand_ok = 0 <= rand_i and rand_i + HOLD_MIN < len(t) and t[rand_i + HOLD_MIN] - t[rand_i] <= HOLD_MIN * 60 + 600
        for v in ("V1", "V2", "V3", "V4"):
            for mode in ("M", "L"):
                res = simulate(o, h, l, c, i0, x.side, x.entry, x.tp1, x.tp2, x.stop, v, mode)
                rec[f"{v}{mode}"] = res[0] if res else np.nan
                rec[f"{v}{mode}_esito"] = res[1] if res else "non eseguito"
                rec[f"{v}{mode}_min"] = res[2] if res else np.nan
                rec[f"{v}{mode}_ambiguo"] = bool(res[3]) if res else False
            # random-time baseline: same pair, side and exits, targets/stop at the same distances
            if rand_ok:
                k = o[rand_i] / o[i0]
                res = simulate(o, h, l, c, rand_i, x.side, x.entry * k, x.tp1 * k, x.tp2 * k,
                               x.stop * k if pd.notna(x.stop) else None, v, "M")
                rec[f"{v}_caso"] = res[0] if res else np.nan
        rows.append(rec)
    bt = pd.DataFrame(rows)
    r(f"\nSegnali con 7 giorni completi di candele: **{len(bt):,}** (dal {bt.time.min():%Y-%m-%d} al {bt.time.max():%Y-%m-%d}). "
      f"Scarto mediano tra il prezzo d'entrata scritto e il primo minuto dopo il messaggio: {bt['scarto_entrata_%'].median():+.3f}% "
      f"(in valore assoluto {bt['scarto_entrata_%'].abs().median():.3f}%).")
    names = {"V1": "V1 come scritto (metà TP1, metà TP2, stop scritto o -3%)", "V2": "V2 V1 + stop all'entrata dopo TP1",
             "V3": "V3 senza stop prima di TP1, poi stop all'entrata, max 7 giorni", "V4": "V4 tutto a TP1 con lo stop di V1"}
    r("\n## Risultato per operazione (senza leva, commissioni comprese)")
    out = []
    for v, lab in names.items():
        for mode, ml in (("M", "a mercato subito"), ("L", "limite al prezzo scritto")):
            out.append({"regole": lab, "entrata": ml, **summarize(bt, f"{v}{mode}"),
                        "minuti_medi": bt[f"{v}{mode}_min"].mean(), "minuti_ambigui": int(bt[f"{v}{mode}_ambiguo"].sum())})
        out.append({"regole": lab, "entrata": "a un minuto CASUALE nei 3 giorni prima (confronto)", **summarize(bt, f"{v}_caso")})
    r.table(pd.DataFrame(out))
    r("\n## Come finiscono le operazioni (entrata a mercato)")
    r.table(pd.concat([bt[f"{v}M_esito"].value_counts(normalize=True).mul(100).rename(v) for v in names], axis=1).fillna(0).reset_index())
    r("\n## Per periodo, direzione, mese e punteggio (V1 e V3, entrata a mercato)")
    for col in ("periodo", "side"):
        rows2 = []
        for g, d in bt.groupby(col):
            rows2.append({col: g, **{f"V1_{k}": v for k, v in summarize(d, "V1M").items() if k in ("n", "media_%", "vincenti_%", "IC95_basso_%", "IC95_alto_%")},
                          **{f"V3_{k}": v for k, v in summarize(d, "V3M").items() if k in ("media_%", "vincenti_%")}})
        r.table(pd.DataFrame(rows2))
    bt["mese"] = bt.time.dt.strftime("%Y-%m")
    r.table(pd.DataFrame([{"mese": g, **{k: v for k, v in summarize(d, "V1M").items() if k in ("n", "media_%", "vincenti_%", "somma_%")}}
                          for g, d in bt.groupby("mese")]))
    if bt.score.notna().any():
        bt["punteggio"] = pd.cut(bt.score, [0, 70, 72, 75, 200], labels=["<= 70", "71-72", "73-75", "> 75"])
        r.table(pd.DataFrame([{"punteggio": str(g), **{k: v for k, v in summarize(d, "V1M").items() if k in ("n", "media_%", "vincenti_%")}}
                              for g, d in bt.groupby("punteggio", observed=True)]))
    r("\n## Con la leva")
    for lev in (5, 10, 20):
        m1 = bt["V1M"].mean() * lev
        r(f"- {lev}x: risultato medio per operazione sul margine {100 * m1:+.1f}%; con V3 (senza stop) una mossa contraria del "
          f"{100 / lev:.0f}% azzera la posizione.")
    bt.to_csv(r.path.with_name(f"{REPORT_NAME}_trades.csv"), index=False)
    r.save()


if __name__ == "__main__":
    main()
