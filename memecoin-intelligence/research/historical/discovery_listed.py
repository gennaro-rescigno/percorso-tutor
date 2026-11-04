"""Study 'discovery_listed': Strategy Discovery Engine for memecoins ALREADY LISTED (PumpSwap pools of graduates).

Independent of the launch engine. Question: on tokens that already have a pool and a trading history (from 30
minutes to 2 days after the graduation), does any combination of pattern x entry mode x exit rule make money
after costs, on days never used to choose it?

PRE-REGISTERED (written before looking at any result):
  * data: jocry postgard_snapshots (PumpSwap pools, June 5 - July 14 2026, a snapshot about every 5 minutes; USD
    converted to SOL with Binance SOLUSDT hourly closes); days split by the snapshot's day: discovery Jun 5-24,
    validation Jun 25 - Jul 4, test Jul 5-14 (read once, only for what passed validation); the other dataset (fly,
    September) is used only if something passes the test;
  * decision moments: the first snapshot of every hour of age, from 30 minutes to 48 hours after the graduation, with
    >= 20 SOL on the pool's SOL side;
  * signals (past and present snapshots only): age, returns over 5 minutes / 1 hour / 6 hours, distance from the
    high since the graduation, return since the graduation, last hour's volume / liquidity, last 5 minutes' volume vs
    the hour (acceleration), buyers' share of the last hour's trades, trades in the last hour, liquidity change over
    the last hour, market cap / liquidity, last hour's volume vs the 6-hour average (revival);
  * named pattern families (thresholds fixed here): momentum = within 5% of the high and turnover above the discovery
    median; breakout = within 2% of the high and acceleration >= 1.5; pullback = 30-60% below the high with a positive
    5-minute return and >= 55% buyers; accumulation = 6-hour return within +-15%, >= 60% buyers and turnover above the
    discovery median; revival = age >= 6 h and last hour's volume >= 3x the 6-hour average; plus, generated
    automatically, every signal in its top / bottom 20%, pairs of the 8 best, a gradient-boosted model (top 10%) and
    every moment (reference); (correction after the synthetic check, before any real run: on the discovery days the
    model is cross-fitted by day - trained on half of the days, scored on the other half - otherwise its
    in-sample fit fills the validation slots; validation and test days use the model trained on all discovery days);
  * entries: E1 at once; E2 confirmation (+10% within 1 hour); E3 pullback (-20% from the high since the decision
    within 2 hours); E4 consolidation (a 1-hour stretch of >= 6 snapshots within a 15% range, within 3 hours);
    delay: the same snapshot (with 1% latency slippage) or the next snapshot;
  * exits (24 hours at most): X1 1 h; X2 4 h; X3 24 h; X4 stop -25% / target +50%; X5 trailing stop 30%; X6 half at
    +50%, the rest with the trailing stop; X7 momentum lost (buyers < 45% of the last hour's trades, after 1 hour);
    X8 liquidity lost (pool liquidity 30% below the entry); a token no longer observed exits at its last snapshot
    (optimistic) and, as a second reading, at -100% (pessimistic);
  * costs on 0.1 SOL: PumpSwap fee tier by market cap (1.25% at <= $100k down to 0.30% at $20M) per side, the sale
    through the constant product of the pool at that moment, own buy impact, 1% latency slippage per side, 0.0002 SOL
    network fee per transaction; stress: fee doubled and 3% more slippage;
  * selection as in discovery_launch: discovery t >= 3 with >= 100 trades; the 60 best go to validation (positive
    mean on >= 50 trades, Benjamini-Hochberg q < 0.10); verdict "edge" only with a test 95% interval above zero,
    positive under the cost stress, positive with the next-snapshot delay and positive in the pessimistic reading.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from numba import njit

from common import JOCRY, OUT, Report, download
from dex_lp import sol_usd_hourly, tier_fee
from discovery_launch import cross_fit, metrics, tstats
from loop_curve import bh, boot_mean

TRAIN_END = pd.Timestamp("2026-06-25", tz="UTC").timestamp()
VAL_END = pd.Timestamp("2026-07-05", tz="UTC").timestamp()
SIZE, NETFEE, LAT = 0.1, 0.0002, 0.01
DELAYS = ("stessa istantanea", "istantanea dopo")
ENTRIES = ("E1 subito", "E2 conferma +10%", "E3 ritracciamento -20%", "E4 consolidamento")
EXITS = ("X1 1 h", "X2 4 h", "X3 24 h", "X4 stop -25% / +50%", "X5 trailing 30%", "X6 metà a +50% + trailing",
         "X7 slancio perso", "X8 liquidità persa")
FEATS = ["age_h", "r5m", "r1h", "r6h", "dd", "r_since", "turn1h", "accel", "buy_share", "log_trades", "liq_chg",
         "mcap_liq", "revival"]
FEAT_IT = {"age_h": "età (ore)", "r5m": "rendimento 5 min", "r1h": "rendimento 1 h", "r6h": "rendimento 6 h",
           "dd": "distanza dal massimo", "r_since": "rendimento dal diploma", "turn1h": "volume 1 h / liquidità",
           "accel": "accelerazione del volume", "buy_share": "quota di acquisti 1 h", "log_trades": "scambi 1 h (log)",
           "liq_chg": "variazione della liquidità 1 h", "mcap_liq": "capitalizzazione / liquidità",
           "revival": "volume 1 h / media 6 h"}


def load() -> pd.DataFrame:
    p = download(JOCRY, "postgard_snapshots.parquet")
    s = pd.read_parquet(p, columns=["mint", "snapshot_time", "seconds_since_graduation", "price_usd", "price_change_5m",
                                    "price_change_1h", "price_change_6h", "liquidity_usd", "volume_5m", "volume_1h",
                                    "volume_6h", "buys_1h", "sells_1h", "market_cap_usd"])
    s = s[(s.price_usd > 0) & (s.liquidity_usd > 0)].copy()
    s["t"] = (pd.to_datetime(s.snapshot_time, utc=True) - pd.Timestamp("1970-01-01", tz="UTC")).dt.total_seconds()
    s = s.sort_values(["mint", "t"]).drop_duplicates(["mint", "t"]).reset_index(drop=True)
    sol = sol_usd_hourly()
    pos = np.clip(np.searchsorted(sol.index.to_numpy(), s.t.to_numpy(), side="right") - 1, 0, len(sol) - 1)
    solp = sol.to_numpy()[pos]
    s["p"] = s.price_usd / solp
    s["liq"] = s.liquidity_usd / 2 / solp  # SOL side of the pool
    s["age"] = s.seconds_since_graduation
    g = s.groupby("mint", sort=False)
    s["age_h"] = s.age / 3600
    s["r5m"], s["r1h"], s["r6h"] = s.price_change_5m / 100, s.price_change_1h / 100, s.price_change_6h / 100
    s["dd"] = s.p / g.p.cummax() - 1
    s["r_since"] = s.p / g.p.transform("first") - 1
    s["turn1h"] = s.volume_1h.fillna(0) / s.liquidity_usd
    s["accel"] = np.where(s.volume_1h > 0, 12 * s.volume_5m / s.volume_1h, np.nan)
    tot = s.buys_1h + s.sells_1h
    s["buy_share"] = np.where(tot > 0, s.buys_1h / tot.where(tot > 0), np.nan)
    s["log_trades"] = np.log1p(tot)
    left = s[["mint", "t"]].assign(q=s.t - 3600, i=np.arange(len(s)))
    m = pd.merge_asof(left.sort_values("q"), s[["mint", "t", "liq"]].rename(columns={"t": "x_t"}).sort_values("x_t"),
                      left_on="q", right_on="x_t", by="mint", direction="backward").sort_values("i")
    s["liq_chg"] = s.liq.to_numpy() / m.liq.to_numpy() - 1
    s["mcap_liq"] = s.market_cap_usd / s.liquidity_usd
    s["revival"] = np.where(s.volume_6h > 0, 6 * s.volume_1h / s.volume_6h, np.nan)
    s["fee"] = tier_fee(s.market_cap_usd.to_numpy())
    s["day"] = (s.t // 86400).astype(int)
    s["split"] = np.where(s.t < TRAIN_END, 0, np.where(s.t < VAL_END, 1, 2))
    return s


@njit(cache=True)
def entry_idx(t, p, s, e, i0, delay, mode):
    """Index of the snapshot where the order is filled, -1 if the entry never triggers."""
    if mode == 0:
        j = i0 + delay
        return j if j < e else -1
    p0 = p[i0]
    j = i0 + 1
    if mode == 1:
        while j < e and t[j] <= t[i0] + 3600:
            if p[j] >= 1.10 * p0:
                return j + delay if j + delay < e else -1
            j += 1
        return -1
    if mode == 2:
        hi = p0
        while j < e and t[j] <= t[i0] + 7200:
            if p[j] > hi:
                hi = p[j]
            elif p[j] <= 0.80 * hi:
                return j + delay if j + delay < e else -1
            j += 1
        return -1
    k = i0 + 1
    while j < e and t[j] <= t[i0] + 10800:
        while t[k] < t[j] - 3600:
            k += 1
        if t[j] >= t[i0] + 3600 and j - k + 1 >= 6:
            mx = p[k]
            mn = p[k]
            for q in range(k, j + 1):
                if p[q] > mx:
                    mx = p[q]
                if p[q] < mn:
                    mn = p[q]
            if mx <= 1.15 * mn:
                return j + delay if j + delay < e else -1
        j += 1
    return -1


@njit(cache=True)
def exit_idx(t, p, liq, bs, s, e, ii, delay, mode):
    """(exit index, value multiple, ended) for a position filled at snapshot ii."""
    p_in = p[ii]
    t_end = t[ii] + 86400.0
    if mode == 0:
        t_end = t[ii] + 3600.0
    elif mode == 1:
        t_end = t[ii] + 14400.0
    hi = p_in
    half = False
    half_val = 0.0
    j = ii + 1
    while j < e and t[j] <= t_end:
        if p[j] > hi:
            hi = p[j]
        trig = False
        if mode == 3 and (p[j] >= 1.5 * p_in or p[j] <= 0.75 * p_in):
            trig = True
        elif mode == 4 and p[j] <= 0.70 * hi:
            trig = True
        elif mode == 5:
            if not half and p[j] >= 1.5 * p_in:
                k = j + delay if j + delay < e else e - 1
                half_val = 0.5 * p[k] / p_in
                half = True
            elif p[j] <= 0.70 * hi:
                trig = True
        elif mode == 6 and t[j] >= t[ii] + 3600 and bs[j] == bs[j] and bs[j] < 0.45:
            trig = True
        elif mode == 7 and liq[j] <= 0.70 * liq[ii]:
            trig = True
        if trig:
            k = j + delay
            ended = 0
            if k >= e:
                k = e - 1
                ended = 1
            share = 0.5 if (mode == 5 and half) else 1.0
            return k, half_val + share * p[k] / p_in, ended
        j += 1
    k = j - 1 + delay if j < e else e - 1
    ended = 1 if j >= e else 0
    if k >= e:
        k = e - 1
    share = 0.5 if (mode == 5 and half) else 1.0
    return k, half_val + share * p[k] / p_in, ended


@njit(cache=True)
def simulate(t, p, liq, bs, fee, starts, ends, c_tok, c_i, size, netfee, lat):
    n = c_tok.shape[0]
    net = np.full((n, 2, 4, 8), np.nan, dtype=np.float32)
    pess = np.full((n, 2, 4, 8), np.nan, dtype=np.float32)
    stress = np.full((n, 2, 4, 8), np.nan, dtype=np.float32)
    hold = np.full((n, 2, 4, 8), np.nan, dtype=np.float32)
    for c in range(n):
        s = starts[c_tok[c]]
        e = ends[c_tok[c]]
        i0 = c_i[c]
        for d in range(2):
            for em in range(4):
                ii = entry_idx(t, p, s, e, i0, d, em)
                if ii < 0:
                    continue
                imp_in = size / liq[ii] if liq[ii] > 0 else 0.9
                if imp_in > 0.9:
                    imp_in = 0.9
                for xm in range(8):
                    k, m, ended = exit_idx(t, p, liq, bs, s, e, ii, d, xm)
                    value = size * m
                    r_out = liq[k] if liq[k] > 0 else 0.0
                    proceeds = r_out * value / (r_out + value) if r_out > 0 else 0.0
                    g = proceeds / size
                    f_in, f_out = fee[ii], fee[k]
                    base = g * (1 - imp_in) * (1 - lat) ** 2
                    net[c, d, em, xm] = base * (1 - f_in) * (1 - f_out) - 2 * netfee / size - 1
                    pess[c, d, em, xm] = -1.0 if ended == 1 else net[c, d, em, xm]
                    stress[c, d, em, xm] = base * (1 - 2 * f_in) * (1 - 2 * f_out) * 0.97 - 2 * netfee / size - 1
                    hold[c, d, em, xm] = (t[k] - t[ii]) / 60.0
    return net, pess, stress, hold


def main() -> None:
    from sklearn.ensemble import HistGradientBoostingRegressor

    r = Report("discovery_listed")
    r("# Strategy Discovery Engine sulle memecoin già quotate (pool PumpSwap, jocry giugno-luglio 2026)")
    r("\nPre-registrazione (testo originale):\n\n```\n" + __doc__.split("PRE-REGISTERED")[1].strip() + "\n```")
    s = load()
    codes, uniq = pd.factorize(s.mint, sort=False)
    s["tok"] = codes
    order = np.argsort(codes, kind="stable")
    s = s.iloc[order].reset_index(drop=True)
    tok = s.tok.to_numpy()
    starts = np.searchsorted(tok, np.arange(len(uniq)), side="left")
    ends = np.searchsorted(tok, np.arange(len(uniq)), side="right")
    hour = (s.age // 3600).astype(int)
    cand_m = (s.age >= 1800) & (s.age <= 48 * 3600) & (s.liq >= 20)
    first = ~pd.DataFrame({"tok": s.tok, "h": hour}).duplicated()
    c = s[cand_m & first.to_numpy()].copy()
    c["i"] = c.index.to_numpy()
    r(f"Istantanee: {len(s):,} di {len(uniq):,} token; momenti di decisione (uno per token e ora, 30 min - 48 h dopo il "
      f"diploma, >= 20 SOL di liquidità): **{len(c):,}** (scoperta {int((c.split == 0).sum()):,}, validazione "
      f"{int((c.split == 1).sum()):,}, test {int((c.split == 2).sum()):,}).")
    net, pess, stress, hold = simulate(s.t.to_numpy(np.float64), s.p.to_numpy(np.float64), s.liq.to_numpy(np.float64),
                                       s.buy_share.to_numpy(np.float64), s.fee.to_numpy(np.float64), starts, ends,
                                       c.tok.to_numpy(np.int64), c.i.to_numpy(np.int64), SIZE, NETFEE, LAT)
    c = c.reset_index(drop=True)
    tr_m = (c.split == 0).to_numpy()
    med_turn = float(np.nanmedian(c.turn1h[tr_m]))
    rules = {"tutti i momenti": np.ones(len(c), bool),
             "slancio: vicino al massimo, volume alto": ((c.dd >= -0.05) & (c.turn1h >= med_turn)).to_numpy(),
             "rottura: nuovo massimo con accelerazione": ((c.dd >= -0.02) & (c.accel >= 1.5)).to_numpy(),
             "ritracciamento con ripresa": ((c.dd <= -0.3) & (c.dd >= -0.6) & (c.r5m > 0) & (c.buy_share >= 0.55)).to_numpy(),
             "accumulazione": ((c.r6h.abs() <= 0.15) & (c.buy_share >= 0.6) & (c.turn1h >= med_turn)).to_numpy(),
             "revival: volume 3x la media di 6 ore": ((c.age_h >= 6) & (c.revival >= 3)).to_numpy()}
    best = []
    for fe in FEATS:
        v = c[fe].to_numpy(np.float64)
        vt = v[tr_m & ~np.isnan(v)]
        if len(vt) < 200:
            continue
        q20, q80 = np.quantile(vt, [0.2, 0.8])
        if q80 > q20:
            rules[f"{FEAT_IT[fe]} alto (>= {q80:.3g})"] = v >= q80
            rules[f"{FEAT_IT[fe]} basso (<= {q20:.3g})"] = v <= q20
    for name, m in list(rules.items()):
        sub = net[m & tr_m]
        if len(sub) < 100:
            continue
        cnt, mu, t = tstats(sub.reshape(len(sub), -1))
        t = np.where(cnt >= 100, t, np.nan)
        best.append((np.nanmax(t) if np.isfinite(t).any() else -np.inf, name))
    top8 = [n for _, n in sorted(best, reverse=True)[:8] if n != "tutti i momenti"]
    for i in range(len(top8)):
        for j in range(i + 1, len(top8)):
            rules[f"{top8[i]} E {top8[j]}"] = rules[top8[i]] & rules[top8[j]]
    y = np.clip(net[:, 0, 0, 4], -1, 3)
    pred = cross_fit(c[FEATS].to_numpy(np.float64), y, tr_m, c.day.to_numpy(), HistGradientBoostingRegressor)
    if pred is not None:
        rules["modello (10% migliore)"] = pred >= np.nanquantile(pred[tr_m], 0.9)

    r("\n## 1. Le famiglie di pattern su tutti i giorni (entrata subito, stessa istantanea)")
    rows = []
    for name in list(rules)[:6]:
        m = rules[name]
        for xm, xn in enumerate(EXITS):
            yv = net[m, 0, 0, xm]
            okv = ~np.isnan(yv)
            if okv.sum() < 30:
                continue
            rows.append({"pattern": name, "uscita": xn, "n": int(okv.sum()), "media_%": 100 * np.nanmean(yv),
                         "mediana_%": 100 * np.nanmedian(yv), "vincenti_%": 100 * np.mean(yv[okv] > 0),
                         "pessimistica_%": 100 * np.nanmean(pess[m, 0, 0, xm]), "durata_media_min": float(np.nanmean(hold[m, 0, 0, xm]))})
    fam = pd.DataFrame(rows)
    r.table(fam)
    r(f"Combinazioni positive (lettura ottimistica): {int((fam['media_%'] > 0).sum())} su {len(fam)}.")

    found = []
    for name, m in rules.items():
        sub = net[m & tr_m]
        if len(sub) < 100:
            continue
        cnt, mu, t = tstats(sub)
        for d in range(2):
            for em in range(4):
                for xm in range(8):
                    if cnt[d, em, xm] >= 100 and mu[d, em, xm] > 0 and t[d, em, xm] >= 3:
                        found.append({"ipotesi": name, "ritardo": DELAYS[d], "entrata": ENTRIES[em], "uscita": EXITS[xm],
                                      "n_scoperta": int(cnt[d, em, xm]), "media_scoperta_%": 100 * mu[d, em, xm],
                                      "t_scoperta": float(t[d, em, xm]), "_m": m, "_c": (d, em, xm)})
    n_strat = len(rules) * 2 * 4 * 8
    r("\n## 2. Il motore di scoperta")
    r(f"Strategie generate e valutate sui giorni di scoperta: **{n_strat:,}** ({len(rules)} ipotesi x 2 ritardi x 4 entrate "
      f"x 8 uscite). Con t >= 3, media positiva e >= 100 operazioni: **{len(found):,}**.")
    if not found:
        r("Nessuna strategia supera nemmeno la soglia sui giorni di scoperta: **nessun vantaggio** sulle memecoin quotate.")
        r.save()
        return
    sel = pd.DataFrame(found).sort_values("t_scoperta", ascending=False).head(60).reset_index(drop=True)
    val = []
    for _, x in sel.iterrows():
        d, em, xm = x._c
        yv = net[x._m & (c.split == 1).to_numpy(), d, em, xm]
        yv = yv[~np.isnan(yv)]
        lo, hi, pv = boot_mean(yv) if len(yv) >= 30 else (np.nan, np.nan, 1.0)
        val.append({"n_validazione": len(yv), "media_validazione_%": 100 * yv.mean() if len(yv) else np.nan, "p_val": pv})
    sel = pd.concat([sel, pd.DataFrame(val)], axis=1)
    sel["q_val"] = bh(sel.p_val.fillna(1.0).tolist())
    sel["passa_validazione"] = (sel.n_validazione >= 50) & (sel["media_validazione_%"] > 0) & (sel.q_val < 0.10)
    r(f"Selezionate per la validazione: {len(sel)}; passano: **{int(sel.passa_validazione.sum())}**.")
    cols = ["ipotesi", "ritardo", "entrata", "uscita", "n_scoperta", "media_scoperta_%", "t_scoperta", "n_validazione",
            "media_validazione_%", "q_val", "passa_validazione"]
    r.table(sel[cols].head(25))
    surv = sel[sel.passa_validazione]
    to_test = surv if len(surv) else sel.head(10)
    r("\n## 3. Giorni di test (letti una sola volta)" + ("" if len(surv) else
      ": nessuna ha passato la validazione; per trasparenza, le 10 migliori della scoperta"))
    rows = []
    te = (c.split == 2).to_numpy()
    for _, x in to_test.iterrows():
        d, em, xm = x._c
        mm = x._m & te
        day, order_ = c.day.to_numpy()[mm], c.t.to_numpy()[mm]
        mt = metrics(net[mm, d, em, xm], order_, hold[mm, d, em, xm], day)
        mp = metrics(pess[mm, d, em, xm], order_, hold[mm, d, em, xm], day)
        ms = metrics(stress[mm, d, em, xm], order_, hold[mm, d, em, xm], day)
        ml = metrics(net[mm, 1, em, xm], order_, hold[mm, 1, em, xm], day)
        edge = (mt.get("n", 0) >= 30 and (mt.get("IC95_basso_%") or -1) > 0 and (ms.get("media_%") or -1) > 0
                and (ml.get("media_%") or -1) > 0 and (mp.get("media_%") or -1) > 0)
        rows.append({"momento_s": "1-48 h", "ipotesi": x.ipotesi, "ritardo_s": 0 if d == 0 else 300, "entrata": x.entrata,
                     "uscita": x.uscita, **{f"test_{k}": v for k, v in mt.items()}, "test_pessimistica_%": mp.get("media_%"),
                     "test_stress_media_%": ms.get("media_%"), "test_ritardo30_media_%": ml.get("media_%"),
                     "media_scoperta_%": x["media_scoperta_%"], "verdetto": "VANTAGGIO" if edge else "no"})
    tt = pd.DataFrame(rows)
    r.table(tt)
    r(f"\n**Strategie con un vantaggio dimostrato fuori campione: {int((tt.verdetto == 'VANTAGGIO').sum())}.**")
    OUT.mkdir(parents=True, exist_ok=True)
    sel.drop(columns=["_m", "_c"]).to_csv(OUT / "discovery_listed_candidates.csv", index=False)
    tt.to_csv(OUT / "discovery_listed_test.csv", index=False)
    r.save()


if __name__ == "__main__":
    main()
