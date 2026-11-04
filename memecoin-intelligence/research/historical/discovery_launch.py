"""Study 'discovery_launch': Strategy Discovery Engine for NEW pump.fun launches (jocry, trade by trade, with wallets).

Question: is there ANY combination of signal x moment after the launch x entry mode x exit rule that makes money
on new launches after realistic costs and the real data delay, on days never used to choose it? The engine
generates the hypotheses itself, keeps only what survives three separate sets of days, and says so when nothing
does. It also answers the descriptive questions (when a signal becomes informative, how much upside is left,
organic vs artificial pumps, which exit loses least, how many entries are not executable).

PRE-REGISTERED (written before looking at any result):
  * data: jocry/Pumpfun_Memecoin_Corpus trades (2026-06-05 .. 07-14) with the trading wallet; cleaning as the
    dataset documents: prices must be > 0; the System Program address is removed from every wallet feature (its
    trades stay in the price path); SOL amounts inconsistent with tokens x price (ratio outside 0.01-100) are not
    used for volumes; split by the token's launch day: discovery Jun 5-24, validation Jun 25 - Jul 4, test
    Jul 5-14 (the test days are read once, at the end, only for the strategies that passed validation);
  * decision moments after the launch: 10 s, 30 s, 1, 3, 5, 15 and 60 minutes; a token is a candidate at a moment if
    it had >= 5 trades so far, traded in the second half of that window and had not graduated yet;
  * signals known at the moment (trades up to it only): trades, buys, sells, distinct buyers and sellers, SOL bought,
    sold/bought ratio, net SOL, average buy, trades per wallet, buyers/sellers, return since the first trade,
    distance from the high, seconds since the last trade, buy acceleration (second half vs first half of the
    window), real SOL in the curve, snipers (buyers in the first 2 s), largest number of distinct wallets buying in
    the same second (bundle), share of the largest buyer and of the top 5, buyers with a good PAST record (>= 8
    positions closed on EARLIER days, >= 50% winners, >= +1 SOL: point-in-time, never the future) and their share
    of the buying, share of brand-new wallets, creator's buy, creator's past tokens and rugs (as recorded at the
    launch), mayhem mode;
  * hypotheses generated automatically per moment: every signal in its top 20% and in its bottom 20% (thresholds
    from the discovery days), the AND of every pair of the 8 best single signals (by discovery t-statistic), a
    gradient-boosted model trained on the discovery days (its top 10% of discovery predictions), and "every
    candidate" (the reference);
  * entries, with a data delay d = 0 s (theoretical), 3 s, 30 s (the median delay measured on the live stream):
    E1 at once; E2 confirmation: price 15% above the decision price within 2 minutes; E3 pullback: price 25% below
    its high since the decision within 5 minutes; E4 consolidation: a 60-second stretch with >= 3 trades and a
    high/low range <= 15% within 5 minutes; every trigger is seen d seconds late and filled at the curve price
    d seconds after it;
  * exits (also acted on d seconds late): X1 after 5 min; X2 after 30 min; X3 stop -30% / target +100%; X4 trailing
    stop 35% below the high since the entry; X5 half at +100%, the rest with the X4 trailing stop; X6 momentum lost:
    from 60 s after the entry, 60 s without a buy or a 60-second window with more SOL sold than bought; X7 held to
    the graduation; everything closes after 60 minutes at most; a graduation during the hold moves the position to
    PumpSwap, sold at the price 1 minute after the graduation (jocry postgard outcomes; 30% below the last curve
    price when missing);
  * costs on 0.1 SOL: 1.25% curve fee per side, own price impact (0.1 SOL / virtual SOL reserve at the entry,
    position value / reserve at the exit), 0.0002 SOL network fee per transaction (above the p90 measured on the
    server); stress: fee 2.5% per side and 3% more slippage;
  * selection (discovery days only): a strategy = moment x hypothesis x entry x delay x exit; kept if it has >= 100
    trades, a positive mean and a t-statistic >= 3; the 60 best by t, plus the 20 best with the 30 s delay, go to
    validation; they pass with a positive mean on >= 50 validation trades and q (Benjamini-Hochberg over those
    candidates) < 0.10; survivors are read on the test days; verdict "edge" only with a test 95% bootstrap interval
    above zero, a positive result under the cost stress and a positive result with the 30 s delay;
  * descriptive outputs on all days (no selection): AUC per moment of every signal for the graduation and for "2x
    before -50%", upside left at each moment, organic vs artificial signals, exits and entries compared on all
    candidates, survival of the tokens after each moment, entries not executable.
"""

from __future__ import annotations

import os

import duckdb
import numpy as np
import pandas as pd
from numba import njit

from common import DATA, JOCRY, Report, download, hf_tree
from loop_curve import bh, boot_mean

SYSTEM = "BwWK17cbHxwWBKZkUYvzxLcNQ1YVyaFezduWbtm2de6s"
WINDOWS = (10, 30, 60, 180, 300, 900, 3600)
DELAYS = (0, 3, 30)
ENTRIES = ("E1 subito", "E2 conferma +15%", "E3 ritracciamento -25%", "E4 consolidamento")
EXITS = ("X1 5 min", "X2 30 min", "X3 stop -30% / +100%", "X4 trailing 35%", "X5 metà a +100% + trailing",
         "X6 slancio perso", "X7 fino al diploma")
SIZE, FEE, NETFEE = 0.1, 0.0125, 0.0002
TRAIN_END = pd.Timestamp("2026-06-25", tz="UTC").timestamp()
VAL_END = pd.Timestamp("2026-07-05", tz="UTC").timestamp()
MAX_CAND = 100_000  # per moment, deterministic sample above this
DB = str(DATA / "discovery_launch.duckdb")
FEATS = ["n", "nb", "ns", "buyers", "sellers", "bsol", "sell_ratio", "net_sol", "avg_buy", "tpw", "buyer_seller",
         "ret", "dd", "idle", "accel", "reserve", "snipers", "bundle", "max_share", "top5_share", "skilled_n",
         "skilled_share", "fresh_share", "dev_pct", "creator_past", "creator_rugs", "mayhem"]
FEAT_IT = {"n": "operazioni", "nb": "acquisti", "ns": "vendite", "buyers": "acquirenti unici", "sellers": "venditori unici",
           "bsol": "SOL comprati", "sell_ratio": "venduto/comprato", "net_sol": "SOL netti", "avg_buy": "acquisto medio",
           "tpw": "operazioni per wallet", "buyer_seller": "acquirenti/venditori", "ret": "rendimento dal primo scambio",
           "dd": "distanza dal massimo", "idle": "secondi dall'ultimo scambio", "accel": "accelerazione degli acquisti",
           "reserve": "SOL reali nella curva", "snipers": "sniper (primi 2 s)", "bundle": "wallet nello stesso secondo",
           "max_share": "quota del primo acquirente", "top5_share": "quota dei primi 5", "skilled_n": "wallet bravi (passato)",
           "skilled_share": "quota dei wallet bravi", "fresh_share": "quota di wallet nuovi", "dev_pct": "acquisto del creatore",
           "creator_past": "token passati del creatore", "creator_rugs": "rug passati del creatore", "mayhem": "mayhem"}


# ----------------------------------------------------------------------------------------------- data
def build(con: duckdb.DuckDBPyConnection, r: Report) -> None:
    if con.execute("SELECT count(*) FROM information_schema.tables WHERE table_name = 'bp'").fetchone()[0]:
        return
    con.execute("CREATE TABLE IF NOT EXISTS tr (mint VARCHAR, ts DOUBLE, age DOUBLE, w VARCHAR, is_buy BOOLEAN, "
                "sol DOUBLE, sol_ok BOOLEAN, px DOUBLE, vsol DOUBLE)")
    shards = sorted(f["path"] for f in hf_tree(JOCRY) if f["path"].startswith("trades/") and f["path"].endswith(".parquet"))
    total = 0
    for sh in shards:
        p = download(JOCRY, sh)
        total += con.execute(f"SELECT count(*) FROM read_parquet('{p}')").fetchone()[0]
        con.execute(f"""
            INSERT INTO tr
            SELECT mint, epoch(event_time), seconds_since_launch,
                   CASE WHEN user_wallet = '{SYSTEM}' THEN NULL ELSE user_wallet END, is_buy, sol_amount,
                   coalesce(sol_amount > 0 AND token_amount > 0
                            AND sol_amount / (token_amount * price_sol) BETWEEN 0.01 AND 100, false),
                   price_sol,
                   CASE WHEN v_sol_bonding_curve / 1e9 BETWEEN 20 AND 200 THEN v_sol_bonding_curve / 1e9 END
            FROM read_parquet('{p}')
            WHERE price_sol > 0 AND seconds_since_launch >= 0 AND mint IS NOT NULL""")
        os.remove(p)
        print(f"{sh}: fatto", flush=True)
    kept = con.execute("SELECT count(*), sum(CASE WHEN sol_ok THEN 1 ELSE 0 END), count(w) FROM tr").fetchone()
    r(f"Operazioni nel corpus: {total:,}; con prezzo valido: {kept[0]:,}; con importo SOL coerente: {kept[1]:,}; "
      f"con un wallet reale: {kept[2]:,}.")
    tok = download(JOCRY, "tokens.parquet")
    con.execute(f"""
        CREATE TABLE tok AS
        WITH l AS (SELECT mint, min(ts - age) AS launch_ts FROM tr GROUP BY mint)
        SELECT l.mint, l.launch_ts, k.creator, coalesce(k.is_mayhem_mode, false)::INT AS mayhem,
               k.dev_buy_pct_corrected AS dev_pct, k.creator_past_tokens AS creator_past, k.creator_past_rugs AS creator_rugs,
               k.seconds_to_graduation AS grad_age
        FROM l JOIN read_parquet('{tok}') k USING (mint)""")
    try:
        po = download(JOCRY, "postgard_outcomes.parquet")
        con.execute(f"""CREATE TABLE post AS SELECT mint, greatest(least(price_at_1m_usd / price_at_grad_usd, 5), 0.05) AS post_ratio
                        FROM read_parquet('{po}') WHERE price_at_grad_usd > 0 AND price_at_1m_usd > 0""")
    except Exception as e:  # the haircut is used for every graduation instead
        print(f"postgard_outcomes non disponibile: {e}", flush=True)
        con.execute("CREATE TABLE post (mint VARCHAR, post_ratio DOUBLE)")
    con.execute("CREATE TABLE tokx AS SELECT t.*, coalesce(p.post_ratio, 0.7) AS post_ratio, p.post_ratio IS NOT NULL AS has_post "
                "FROM tok t LEFT JOIN post p USING (mint)")
    # wallet record, point-in-time: positions closed on EARLIER days only
    con.execute("""
        CREATE TABLE pos AS
        WITH p AS (
            SELECT w, mint, sum(CASE WHEN is_buy THEN sol ELSE 0 END) AS bs, sum(CASE WHEN is_buy THEN 0 ELSE sol END) AS ss,
                   max(ts) AS end_ts
            FROM tr WHERE w IS NOT NULL AND sol_ok GROUP BY w, mint)
        SELECT p.w, floor(p.end_ts / 86400)::INT AS d, p.ss * (1 - 0.0125) - p.bs * (1 + 0.0125) AS pnl,
               p.ss * (1 - 0.0125) > p.bs * (1 + 0.0125) AS win
        FROM p JOIN tok k USING (mint) WHERE p.bs >= 0.01 AND (k.creator IS NULL OR p.w <> k.creator)""")
    con.execute("""
        CREATE TABLE cum AS
        WITH g AS (SELECT w, d, count(*) AS n, sum(win::INT) AS wins, sum(pnl) AS pnl FROM pos GROUP BY w, d)
        SELECT w, d, sum(n) OVER (PARTITION BY w ORDER BY d) AS cn, sum(wins) OVER (PARTITION BY w ORDER BY d) AS cw,
               sum(pnl) OVER (PARTITION BY w ORDER BY d) AS cp FROM g""")
    con.execute("CREATE TABLE first_seen AS SELECT w, min(ts) AS t0 FROM tr WHERE w IS NOT NULL GROUP BY w")
    con.execute("""
        CREATE TABLE bp AS
        WITH b AS (SELECT mint, w, min(age) AS first_age FROM tr WHERE is_buy AND w IS NOT NULL AND age <= 3600
                   GROUP BY mint, w),
        b2 AS (SELECT b.*, floor(k.launch_ts / 86400)::INT - 1 AS dprev, k.launch_ts FROM b JOIN tok k USING (mint))
        SELECT b2.mint, b2.w, b2.first_age,
               coalesce(c.cn >= 8 AND c.cw >= 0.5 * c.cn AND c.cp >= 1.0, false) AS skilled,
               f.t0 >= b2.launch_ts AS fresh
        FROM b2 ASOF LEFT JOIN cum c ON b2.w = c.w AND b2.dprev >= c.d
        LEFT JOIN first_seen f ON b2.w = f.w""")
    con.execute("DROP TABLE pos; DROP TABLE first_seen")


def features(con: duckdb.DuckDBPyConnection, a: int) -> pd.DataFrame:
    df = con.execute(f"""
        WITH x AS (SELECT * FROM tr WHERE age <= {a}),
        g AS (
            SELECT mint, count(*) AS n, sum(is_buy::INT) AS nb, sum((NOT is_buy)::INT) AS ns,
                   count(DISTINCT CASE WHEN is_buy THEN w END) AS buyers,
                   count(DISTINCT CASE WHEN NOT is_buy THEN w END) AS sellers,
                   sum(CASE WHEN is_buy AND sol_ok THEN sol ELSE 0 END) AS bsol,
                   sum(CASE WHEN NOT is_buy AND sol_ok THEN sol ELSE 0 END) AS ssol,
                   arg_max(px, age) AS px_last, arg_min(px, age) AS px_first, max(px) AS px_max, max(age) AS last_age,
                   arg_max(vsol, age) AS vsol_last,
                   sum(CASE WHEN is_buy AND age > {a} / 2.0 THEN 1 ELSE 0 END) AS nb_late,
                   sum(CASE WHEN is_buy AND age <= {a} / 2.0 THEN 1 ELSE 0 END) AS nb_early,
                   count(DISTINCT CASE WHEN is_buy AND age <= 2 THEN w END) AS snipers
            FROM x GROUP BY mint HAVING count(*) >= 5 AND max(age) >= {a} / 2.0),
        sec AS (SELECT mint, max(k) AS bundle FROM (
                    SELECT mint, floor(age) AS s, count(DISTINCT w) AS k FROM x WHERE is_buy AND w IS NOT NULL
                    GROUP BY mint, s) GROUP BY mint),
        wb AS (SELECT x.mint, x.w, sum(x.sol) AS s FROM x WHERE x.is_buy AND x.w IS NOT NULL AND x.sol_ok GROUP BY x.mint, x.w),
        wf AS (SELECT wb.*, coalesce(bp.skilled, false) AS skilled, coalesce(bp.fresh, false) AS fresh,
                      row_number() OVER (PARTITION BY wb.mint ORDER BY wb.s DESC) AS rk,
                      sum(wb.s) OVER (PARTITION BY wb.mint) AS tot
               FROM wb LEFT JOIN bp ON wb.mint = bp.mint AND wb.w = bp.w),
        conc AS (SELECT mint, max(s) / nullif(max(tot), 0) AS max_share,
                        sum(CASE WHEN rk <= 5 THEN s ELSE 0 END) / nullif(max(tot), 0) AS top5_share,
                        sum(skilled::INT) AS skilled_n,
                        sum(CASE WHEN skilled THEN s ELSE 0 END) / nullif(max(tot), 0) AS skilled_share,
                        avg(fresh::INT) AS fresh_share
                 FROM wf GROUP BY mint)
        SELECT g.*, coalesce(sec.bundle, 0) AS bundle, conc.max_share, conc.top5_share, coalesce(conc.skilled_n, 0) AS skilled_n,
               conc.skilled_share, conc.fresh_share, k.launch_ts, k.grad_age, k.mayhem, k.dev_pct, k.creator_past,
               k.creator_rugs, k.post_ratio, k.has_post
        FROM g LEFT JOIN sec USING (mint) LEFT JOIN conc USING (mint) JOIN tokx k USING (mint)
        WHERE k.grad_age IS NULL OR k.grad_age > {a}""").df()
    df["sell_ratio"] = df.ssol / df.bsol.where(df.bsol > 0)
    df["net_sol"] = df.bsol - df.ssol
    df["avg_buy"] = df.bsol / df.nb.where(df.nb > 0)
    df["tpw"] = df.n / (df.buyers + df.sellers).where(df.buyers + df.sellers > 0)
    df["buyer_seller"] = df.buyers / (df.sellers + 1)
    df["ret"] = df.px_last / df.px_first - 1
    df["dd"] = df.px_last / df.px_max - 1
    df["idle"] = a - df.last_age
    df["accel"] = df.nb_late / (df.nb_early + 1)
    df["reserve"] = df.vsol_last - 30
    df["day"] = (df.launch_ts // 86400).astype(int)
    df["split"] = np.where(df.launch_ts < TRAIN_END, 0, np.where(df.launch_ts < VAL_END, 1, 2))
    if len(df) > MAX_CAND:  # deterministic sample (by mint), reported
        h = pd.util.hash_pandas_object(df.mint, index=False).to_numpy() % 1_000_000
        df = df[h < np.quantile(h, MAX_CAND / len(df))]
    df["window"] = a
    return df.reset_index(drop=True)


# ----------------------------------------------------------------------------------------------- path engine
@njit(cache=True)
def idx_at(ages, s, e, t):
    lo, hi = s, e
    while lo < hi:
        mid = (lo + hi) // 2
        if ages[mid] <= t:
            lo = mid + 1
        else:
            hi = mid
    return lo - 1


@njit(cache=True)
def entry_time(ages, px, s, e, a, d, mode):
    i0 = idx_at(ages, s, e, a)
    if i0 < s:
        return -1.0
    p0 = px[i0]
    if mode == 0:
        return a + d
    j = i0 + 1
    if mode == 1:
        while j < e and ages[j] <= a + 120:
            if px[j] >= 1.15 * p0:
                return ages[j] + d
            j += 1
        return -1.0
    if mode == 2:
        hi_ = p0
        while j < e and ages[j] <= a + 300:
            if px[j] > hi_:
                hi_ = px[j]
            elif px[j] <= 0.75 * hi_:
                return ages[j] + d
            j += 1
        return -1.0
    k = i0 + 1
    while j < e and ages[j] <= a + 300:
        while ages[k] < ages[j] - 60:
            k += 1
        if ages[j] >= a + 60 and j - k + 1 >= 3:
            mx = px[k]
            mn = px[k]
            for q in range(k, j + 1):
                if px[q] > mx:
                    mx = px[q]
                if px[q] < mn:
                    mn = px[q]
            if mx <= 1.15 * mn:
                return ages[j] + d
        j += 1
    return -1.0


@njit(cache=True)
def price_or_grad(ages, px, s, e, t, grad_age, post_ratio):
    """Curve price at t (last trade at or before), or the PumpSwap price after the graduation."""
    if grad_age > 0 and t >= grad_age:
        ig = idx_at(ages, s, e, grad_age)
        if ig < s:
            ig = s
        return px[ig] * post_ratio, 1
    i = idx_at(ages, s, e, t)
    if i < s:
        i = s
    return px[i], 0


@njit(cache=True)
def run_exit(ages, px, buy, sol, s, e, t_in, p_in, d, mode, grad_age, post_ratio):
    """Gross multiple of one position, its exit time and how it ended (0 time, 1 trigger, 2 graduation)."""
    t_end = t_in + 3600.0
    if mode == 0:
        t_end = t_in + 300.0
    elif mode == 1:
        t_end = t_in + 1800.0
    i = idx_at(ages, s, e, t_in)
    hi_ = p_in
    half = False
    half_val = 0.0
    last_buy = t_in
    k = i + 1
    bwin = 0.0
    swin = 0.0
    j = i + 1
    while j < e and ages[j] <= t_end:
        t = ages[j]
        if grad_age > 0 and t >= grad_age:
            break
        if mode == 5 and t - last_buy > 60.0:
            tg = last_buy + 60.0
            if tg < t_in + 60.0:
                tg = t_in + 60.0
            if tg < t:
                p, g = price_or_grad(ages, px, s, e, tg + d, grad_age, post_ratio)
                return p / p_in, tg + d, 1 + g
        p = px[j]
        if buy[j]:
            bwin += sol[j]
            last_buy = t
        else:
            swin += sol[j]
        while k < j and ages[k] < t - 60.0:
            if buy[k]:
                bwin -= sol[k]
            else:
                swin -= sol[k]
            k += 1
        if p > hi_:
            hi_ = p
        trig = False
        if mode == 2 and (p >= 2.0 * p_in or p <= 0.7 * p_in):
            trig = True
        elif mode == 3 and p <= 0.65 * hi_:
            trig = True
        elif mode == 4:
            if not half and p >= 2.0 * p_in:
                q, g = price_or_grad(ages, px, s, e, t + d, grad_age, post_ratio)
                half_val = 0.5 * q / p_in
                half = True
            elif p <= 0.65 * hi_:
                trig = True
        elif mode == 5 and t >= t_in + 60.0 and swin > bwin:
            trig = True
        if trig:
            q, g = price_or_grad(ages, px, s, e, t + d, grad_age, post_ratio)
            share = 0.5 if (mode == 4 and half) else 1.0
            return half_val + share * q / p_in, t + d, 1 + g
        j += 1
    if grad_age > t_in and grad_age <= t_end:
        q, g = price_or_grad(ages, px, s, e, grad_age, grad_age, post_ratio)
        share = 0.5 if (mode == 4 and half) else 1.0
        return half_val + share * q / p_in, grad_age + 60.0, 2
    if mode == 5:
        tg = last_buy + 60.0
        if tg < t_in + 60.0:
            tg = t_in + 60.0
        if tg < t_end:
            q, g = price_or_grad(ages, px, s, e, tg + d, grad_age, post_ratio)
            return q / p_in, tg + d, 1 + g
    q, g = price_or_grad(ages, px, s, e, t_end + d, grad_age, post_ratio)
    share = 0.5 if (mode == 4 and half) else 1.0
    return half_val + share * q / p_in, t_end + d, 2 * g


@njit(cache=True)
def simulate_all(ages, px, buy, sol, vs, starts, ends, c_tok, c_a, c_grad, c_post, delays, fee, size, netfee):
    n = c_tok.shape[0]
    nd = delays.shape[0]
    net = np.full((n, nd, 4, 7), np.nan, dtype=np.float32)
    stress = np.full((n, nd, 4, 7), np.nan, dtype=np.float32)
    hold = np.full((n, nd, 4, 7), np.nan, dtype=np.float32)
    noexec = np.zeros((nd, 4), dtype=np.int64)
    trig = np.zeros((nd, 4), dtype=np.int64)
    for c in range(n):
        tk = c_tok[c]
        s = starts[tk]
        e = ends[tk]
        for di in range(nd):
            d = delays[di]
            for em in range(4):
                t_in = entry_time(ages, px, s, e, c_a[c], d, em)
                if t_in < 0:
                    continue
                trig[di, em] += 1
                if c_grad[c] > 0 and t_in >= c_grad[c]:
                    noexec[di, em] += 1  # the curve closed before the order could land
                    continue
                i_in = idx_at(ages, s, e, t_in)
                if i_in < s:
                    noexec[di, em] += 1
                    continue
                p_in = px[i_in]
                v_in = vs[i_in] if vs[i_in] > 0 else 30.0
                imp_in = size / v_in
                for xm in range(7):
                    m, t_out, how = run_exit(ages, px, buy, sol, s, e, t_in, p_in, d, xm, c_grad[c], c_post[c])
                    if how == 2:
                        v_out = 85.0
                    else:
                        i_out = idx_at(ages, s, e, t_out)
                        v_out = vs[i_out] if (i_out >= s and vs[i_out] > 0) else v_in
                    imp_out = min(size * m / v_out, 0.9)
                    base = m * (1 - imp_in) * (1 - imp_out)
                    net[c, di, em, xm] = base * (1 - fee) ** 2 - 2 * netfee / size - 1
                    stress[c, di, em, xm] = base * (1 - 2 * fee) ** 2 * 0.97 - 2 * netfee / size - 1
                    hold[c, di, em, xm] = (t_out - t_in) / 60.0
    return net, stress, hold, noexec, trig


@njit(cache=True)
def describe_paths(ages, px, starts, ends, c_tok, c_a):
    """From the decision price: peak multiple in the next hour, 2x before -50% (1/0), still trading after 5/15/60 min."""
    n = c_tok.shape[0]
    peak = np.full(n, np.nan)
    hit = np.zeros(n, dtype=np.int8)
    alive = np.zeros((n, 3), dtype=np.int8)
    for c in range(n):
        s = starts[c_tok[c]]
        e = ends[c_tok[c]]
        i0 = idx_at(ages, s, e, c_a[c])
        if i0 < s:
            continue
        p0 = px[i0]
        mx = p0
        done = False
        j = i0 + 1
        while j < e and ages[j] <= c_a[c] + 3600:
            if px[j] > mx:
                mx = px[j]
            if not done:
                if px[j] >= 2 * p0:
                    hit[c] = 1
                    done = True
                elif px[j] <= 0.5 * p0:
                    done = True
            j += 1
        peak[c] = mx / p0
        last = ages[e - 1]
        alive[c, 0] = 1 if last > c_a[c] + 300 else 0
        alive[c, 1] = 1 if last > c_a[c] + 900 else 0
        alive[c, 2] = 1 if last > c_a[c] + 3600 else 0
    return peak, hit, alive


# ----------------------------------------------------------------------------------------------- statistics
def tstats(x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """x: (n, ...) with NaN for 'no trade' -> count, mean, t over axis 0."""
    cnt = np.sum(~np.isnan(x), axis=0)
    mean = np.nanmean(x, axis=0) if len(x) else np.full(x.shape[1:], np.nan)
    sd = np.nanstd(x, axis=0, ddof=1) if len(x) > 1 else np.full(x.shape[1:], np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        t = mean / (sd / np.sqrt(cnt))
    return cnt, mean, t


def metrics(y: np.ndarray, order: np.ndarray, hold: np.ndarray, day: np.ndarray) -> dict:
    ok = ~np.isnan(y)
    y, order, hold, day = y[ok], order[ok], hold[ok], day[ok]
    if len(y) == 0:
        return {"n": 0}
    lo, hi, p = boot_mean(y) if len(y) >= 30 else (np.nan, np.nan, np.nan)
    wins, losses = y[y > 0], y[y <= 0]
    seq = y[np.argsort(order)] <= 0
    streak = best = 0
    for v in seq:
        streak = streak + 1 if v else 0
        best = max(best, streak)
    pnl = pd.Series(y * SIZE).groupby(day).sum()
    pnl = pnl.reindex(range(int(day.min()), int(day.max()) + 1), fill_value=0.0)
    eq = 2.0 + pnl.cumsum()
    dd = (eq / eq.cummax() - 1).min()
    sd = pnl.std()
    down = pnl[pnl < 0].std()
    return {"n": len(y), "media_%": 100 * y.mean(), "IC95_basso_%": 100 * lo, "IC95_alto_%": 100 * hi, "p": p,
            "mediana_%": 100 * np.median(y), "vincenti_%": 100 * len(wins) / len(y),
            "vincita_media_%": 100 * wins.mean() if len(wins) else np.nan,
            "perdita_media_%": 100 * losses.mean() if len(losses) else np.nan,
            "profit_factor": wins.sum() / -losses.sum() if losses.sum() < 0 else np.inf,
            "serie_perdite_max": best, "durata_media_min": float(np.mean(hold)),
            "profitto_SOL_su_0,1": float(y.sum() * SIZE), "ROI_su_2_SOL_%": float(100 * y.sum() * SIZE / 2.0),
            "maxDD_%": 100 * dd, "Sharpe_giorni": float(pnl.mean() / sd * np.sqrt(365)) if sd > 0 else np.nan,
            "Sortino_giorni": float(pnl.mean() / down * np.sqrt(365)) if down and down > 0 else np.nan,
            "commissioni_SOL": float(len(y) * (2 * FEE * SIZE + 2 * NETFEE))}


def auc(score: np.ndarray, label: np.ndarray) -> tuple[float, float]:
    ok = ~np.isnan(score)
    s, l = score[ok], label[ok].astype(bool)
    n1, n0 = l.sum(), (~l).sum()
    if n1 < 20 or n0 < 20:
        return np.nan, np.nan
    rk = pd.Series(s).rank().to_numpy()
    a = (rk[l].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)
    q1, q2 = a / (2 - a), 2 * a * a / (1 + a)
    se = np.sqrt((a * (1 - a) + (n1 - 1) * (q1 - a * a) + (n0 - 1) * (q2 - a * a)) / (n1 * n0))
    return float(a), float(se)


# ----------------------------------------------------------------------------------------------- main
def main() -> None:
    from sklearn.ensemble import HistGradientBoostingRegressor

    r = Report("discovery_launch")
    r("# Strategy Discovery Engine sui nuovi lanci pump.fun (jocry, operazione per operazione, con i wallet)")
    r("\nPre-registrazione (testo originale):\n\n```\n" + __doc__.split("PRE-REGISTERED")[1].strip() + "\n```")
    con = duckdb.connect(DB)
    con.execute("SET memory_limit='3GB'; SET temp_directory='/tmp/duck'; SET preserve_insertion_order=false")
    build(con, r)
    cands = []
    for a in WINDOWS:
        f = features(con, a)
        print(f"finestra {a}s: {len(f):,} candidati", flush=True)
        cands.append(f)
    allc = pd.concat(cands, ignore_index=True)
    mints = sorted(allc.mint.unique())
    con.execute("CREATE OR REPLACE TEMP TABLE m AS SELECT unnest(?) AS mint", [mints])
    con.execute("CREATE OR REPLACE TEMP TABLE mid AS SELECT mint, row_number() OVER (ORDER BY mint) - 1 AS k FROM m")
    path = con.execute("""
        SELECT mid.k::INTEGER AS k, tr.age::FLOAT AS age, tr.px::FLOAT AS px, tr.is_buy,
               (CASE WHEN tr.sol_ok THEN tr.sol ELSE 0 END)::FLOAT AS sol, coalesce(tr.vsol, 0)::FLOAT AS vsol
        FROM tr JOIN mid USING (mint) WHERE tr.age <= 3600 + 3600 + 400 ORDER BY mid.k, tr.age""").fetchnumpy()
    k = path["k"].astype(np.int64)
    ages, px = np.asarray(path["age"], np.float32), np.asarray(path["px"], np.float32)
    buy, sol, vs = np.asarray(path["is_buy"], np.bool_), np.asarray(path["sol"], np.float32), np.asarray(path["vsol"], np.float32)
    del path
    nk = len(mints)
    starts = np.searchsorted(k, np.arange(nk), side="left")
    ends = np.searchsorted(k, np.arange(nk), side="right")
    kmap = {m: i for i, m in enumerate(mints)}
    allc["tok"] = allc.mint.map(kmap).astype(np.int64)
    c_grad = allc.grad_age.fillna(-1.0).to_numpy(np.float64)
    c_post = allc.post_ratio.fillna(0.7).to_numpy(np.float64)
    r(f"Candidati: {len(allc):,} momenti di {nk:,} token; operazioni nei percorsi: {len(ages):,}; giorni "
      f"{allc.day.nunique()} (scoperta {int((allc.split == 0).sum()):,}, validazione {int((allc.split == 1).sum()):,}, "
      f"test {int((allc.split == 2).sum()):,} momenti).")
    net, stress, hold, noexec, trig = simulate_all(ages, px, buy, sol, vs, starts, ends, allc.tok.to_numpy(),
                                                   allc.window.to_numpy(np.float64), c_grad, c_post,
                                                   np.array(DELAYS, np.float64), FEE, SIZE, NETFEE)
    peak, hit, alive = describe_paths(ages, px, starts, ends, allc.tok.to_numpy(), allc.window.to_numpy(np.float64))
    allc["peak"], allc["hit2x"] = peak, hit
    allc["alive5"], allc["alive15"], allc["alive60"] = alive[:, 0], alive[:, 1], alive[:, 2]
    allc["graduated"] = allc.grad_age.notna().astype(int)

    # ---------------- descriptive: timing, upside left, survival
    r("\n## 1. Quando entrare: cosa resta dopo ogni momento (tutti i giorni)")
    rows = []
    for a in WINDOWS:
        x = allc[allc.window == a]
        rows.append({"momento_s": a, "candidati": len(x), "diplomati_%": 100 * x.graduated.mean(),
                     "2x_prima_di_-50%_%": 100 * x.hit2x.mean(), "massimo_mediano_nell'ora_x": float(np.nanmedian(x.peak)),
                     "massimo_p90_x": float(np.nanpercentile(x.peak, 90)), "vivi_dopo_5_min_%": 100 * x.alive5.mean(),
                     "vivi_dopo_15_min_%": 100 * x.alive15.mean(), "vivi_dopo_60_min_%": 100 * x.alive60.mean()})
    r.table(pd.DataFrame(rows))

    r("\n## 2. Quali segnali sono informativi e da quando (AUC, tutti i giorni; 0,5 = nessuna informazione)")
    for target, lab in (("graduated", "diploma"), ("hit2x", "2x prima di -50% dal momento")):
        rows = []
        for a in WINDOWS:
            x = allc[allc.window == a]
            for fe in FEATS:
                v, se = auc(x[fe].to_numpy(np.float64), x[target].to_numpy())
                if np.isnan(v):
                    continue
                rows.append({"momento_s": a, "segnale": FEAT_IT[fe], "AUC": v, "IC95": f"[{v - 1.96 * se:.3f}, {v + 1.96 * se:.3f}]",
                             "forza": abs(v - 0.5)})
        t = pd.DataFrame(rows)
        if t.empty:
            continue
        top = t.sort_values(["momento_s", "forza"], ascending=[True, False]).groupby("momento_s").head(6)
        r(f"\n### Obiettivo: {lab}")
        r.table(top.drop(columns="forza"))

    r("\n## 3. Pump organico o artificiale (momento 60 s e 5 min, tutti i giorni)")
    rows = []
    for a in (60, 300):
        x = allc[allc.window == a]
        ix = np.where(allc.window.to_numpy() == a)[0]
        base = net[ix, 1, 0, 3]  # 3 s, E1, trailing
        for fe, lab_hi in (("bundle", "molti wallet nello stesso secondo"), ("fresh_share", "molti wallet nuovi"),
                           ("max_share", "un acquirente domina"), ("snipers", "molti sniper"),
                           ("skilled_n", "wallet bravi presenti"), ("buyers", "molti acquirenti unici")):
            if x[fe].notna().sum() < 100:
                continue
            q = x[fe].quantile(0.8)
            hi_m = (x[fe] > q).to_numpy() if q > x[fe].min() else (x[fe] > 0).to_numpy()
            for lab, m in ((lab_hi, hi_m), ("il resto", ~hi_m)):
                rows.append({"momento_s": a, "gruppo": f"{FEAT_IT[fe]}: {lab}", "token": int(m.sum()),
                             "diplomati_%": 100 * x.graduated.to_numpy()[m].mean(),
                             "2x_prima_di_-50%_%": 100 * x.hit2x.to_numpy()[m].mean(),
                             "netto_medio_E1_X4_3s_%": 100 * np.nanmean(base[m])})
    r.table(pd.DataFrame(rows))

    r("\n## 4. Entrate e uscite a confronto su TUTTI i candidati (nessuna selezione), ritardo 3 s e 30 s")
    rows = []
    for a in (30, 60, 300, 900):
        ix = np.where(allc.window.to_numpy() == a)[0]
        for di, d in enumerate(DELAYS):
            if d == 0:
                continue
            for em, en in enumerate(ENTRIES):
                for xm, xn in enumerate(EXITS):
                    y = net[ix, di, em, xm]
                    ok = ~np.isnan(y)
                    if ok.sum() < 30:
                        continue
                    rows.append({"momento_s": a, "ritardo_s": d, "entrata": en, "uscita": xn, "n": int(ok.sum()),
                                 "media_%": 100 * np.nanmean(y), "mediana_%": 100 * np.nanmedian(y),
                                 "vincenti_%": 100 * np.mean(y[ok] > 0), "durata_media_min": float(np.nanmean(hold[ix, di, em, xm]))})
    cmp_tab = pd.DataFrame(rows)
    r.table(cmp_tab.sort_values("media_%", ascending=False).head(25))
    r(f"Combinazioni su tutti i candidati con media positiva: {int((cmp_tab['media_%'] > 0).sum())} su {len(cmp_tab)}.")
    r("\nEntrate attivate e non eseguibili (la curva si è chiusa prima che l'ordine arrivasse):")
    rows = []
    for di, d in enumerate(DELAYS):
        for em, en in enumerate(ENTRIES):
            rows.append({"ritardo_s": d, "entrata": en, "attivate": int(trig[di, em]), "non_eseguibili": int(noexec[di, em]),
                         "non_eseguibili_%": 100 * noexec[di, em] / max(1, trig[di, em])})
    r.table(pd.DataFrame(rows))

    # ---------------- discovery: hypotheses on the discovery days only
    cells = []  # (window, rule name, mask over allc rows)
    for a in WINDOWS:
        ix = np.where(allc.window.to_numpy() == a)[0]
        x = allc.iloc[ix]
        tr_m = (x.split == 0).to_numpy()
        rules = {"tutti i candidati": np.ones(len(x), bool)}
        for fe in FEATS:
            v = x[fe].to_numpy(np.float64)
            vt = v[tr_m & ~np.isnan(v)]
            if len(vt) < 200:
                continue
            q20, q80 = np.quantile(vt, [0.2, 0.8])
            if q80 > q20:
                rules[f"{FEAT_IT[fe]} alto (>= {q80:.4g})"] = v >= q80
                rules[f"{FEAT_IT[fe]} basso (<= {q20:.4g})"] = v <= q20
            elif np.nanmax(vt) > q80:
                rules[f"{FEAT_IT[fe]} > {q80:.4g}"] = v > q80
        # single-rule discovery t to pick the 8 best for pairs
        best = []
        for name, m in rules.items():
            sub = net[ix[m & tr_m]]
            if len(sub) < 100:
                continue
            c_, mu, t = tstats(sub.reshape(len(sub), -1))
            t = np.where(c_ >= 100, t, np.nan)
            best.append((np.nanmax(t) if np.isfinite(t).any() else -np.inf, name))
        top8 = [n for _, n in sorted(best, reverse=True)[:8] if n != "tutti i candidati"]
        for i in range(len(top8)):
            for j in range(i + 1, len(top8)):
                rules[f"{top8[i]} E {top8[j]}"] = rules[top8[i]] & rules[top8[j]]
        try:
            Xtr = x.loc[tr_m, FEATS].to_numpy(np.float64)
            ytr = np.clip(net[ix[tr_m], 1, 0, 3], -1, 3)
            ok = ~np.isnan(ytr)
            if ok.sum() >= 2000:
                mdl = HistGradientBoostingRegressor(max_iter=200, learning_rate=0.05, max_leaf_nodes=31,
                                                    min_samples_leaf=200, l2_regularization=1.0, random_state=0)
                mdl.fit(Xtr[ok], ytr[ok])
                pred = mdl.predict(x[FEATS].to_numpy(np.float64))
                rules["modello (10% migliore)"] = pred >= np.quantile(pred[tr_m], 0.9)
        except Exception as e:
            print(f"modello {a}s: {e}", flush=True)
        for name, m in rules.items():
            cells.append((a, name, ix[m]))
    n_strat = len(cells) * len(DELAYS) * 4 * 7
    found = []
    for a, name, rows_ix in cells:
        sp = allc.split.to_numpy()[rows_ix]
        sub = net[rows_ix[sp == 0]]
        if len(sub) < 100:
            continue
        c_, mu, t = tstats(sub)
        for di in range(len(DELAYS)):
            for em in range(4):
                for xm in range(7):
                    if c_[di, em, xm] >= 100 and mu[di, em, xm] > 0 and t[di, em, xm] >= 3:
                        found.append({"momento_s": a, "ipotesi": name, "ritardo_s": DELAYS[di], "entrata": ENTRIES[em],
                                      "uscita": EXITS[xm], "n_scoperta": int(c_[di, em, xm]),
                                      "media_scoperta_%": 100 * mu[di, em, xm], "t_scoperta": float(t[di, em, xm]),
                                      "_ix": rows_ix, "_c": (di, em, xm)})
    r("\n## 5. Il motore di scoperta")
    r(f"Strategie generate e valutate sui giorni di scoperta: **{n_strat:,}** ({len(cells):,} ipotesi x "
      f"{len(DELAYS)} ritardi x 4 entrate x 7 uscite). Con t >= 3, media positiva e >= 100 operazioni: **{len(found):,}**.")
    if not found:
        r("Nessuna strategia supera nemmeno la soglia sui giorni di scoperta.")
        r.save()
        return
    fd = pd.DataFrame(found).sort_values("t_scoperta", ascending=False)
    sel = pd.concat([fd.head(60), fd[fd.ritardo_s == 30].head(20)]).drop_duplicates(
        subset=["momento_s", "ipotesi", "ritardo_s", "entrata", "uscita"])
    val = []
    for _, s_ in sel.iterrows():
        sp = allc.split.to_numpy()[s_._ix]
        y = net[s_._ix[sp == 1]][:, s_._c[0], s_._c[1], s_._c[2]]
        y = y[~np.isnan(y)]
        lo, hi, p = boot_mean(y) if len(y) >= 30 else (np.nan, np.nan, 1.0)
        val.append({"n_validazione": len(y), "media_validazione_%": 100 * y.mean() if len(y) else np.nan, "p_val": p})
    sel = pd.concat([sel.reset_index(drop=True), pd.DataFrame(val)], axis=1)
    sel["q_val"] = bh(sel.p_val.fillna(1.0).tolist())
    sel["passa_validazione"] = (sel.n_validazione >= 50) & (sel["media_validazione_%"] > 0) & (sel.q_val < 0.10)
    r(f"Selezionate per la validazione: {len(sel)}; passano la validazione: **{int(sel.passa_validazione.sum())}**.")
    show_cols = ["momento_s", "ipotesi", "ritardo_s", "entrata", "uscita", "n_scoperta", "media_scoperta_%",
                 "t_scoperta", "n_validazione", "media_validazione_%", "q_val", "passa_validazione"]
    r("\nLe 25 migliori sui giorni di scoperta e come vanno in validazione:")
    r.table(sel[show_cols].head(25))
    # test: survivors (or, for transparency, the 10 best by discovery t when nobody survives)
    surv = sel[sel.passa_validazione]
    to_test = surv if len(surv) else sel.head(10)
    r("\n## 6. Giorni di test (letti una sola volta)" + ("" if len(surv) else
      ": nessuna strategia ha passato la validazione; per trasparenza, le 10 migliori della scoperta"))
    rows = []
    for _, s_ in to_test.iterrows():
        di, em, xm = s_._c
        sp = allc.split.to_numpy()[s_._ix]
        tix = s_._ix[sp == 2]
        day = allc.day.to_numpy()[tix]
        order = allc.launch_ts.to_numpy()[tix] + allc.window.to_numpy()[tix]
        m = metrics(net[tix, di, em, xm], order, hold[tix, di, em, xm], day)
        ms = metrics(stress[tix, di, em, xm], order, hold[tix, di, em, xm], day)
        m30 = metrics(net[tix, DELAYS.index(30), em, xm], order, hold[tix, DELAYS.index(30), em, xm], day)
        edge = (m.get("n", 0) >= 30 and (m.get("IC95_basso_%") or -1) > 0 and (ms.get("media_%") or -1) > 0
                and (m30.get("media_%") or -1) > 0)
        rows.append({"momento_s": s_.momento_s, "ipotesi": s_.ipotesi, "ritardo_s": s_.ritardo_s, "entrata": s_.entrata,
                     "uscita": s_.uscita, **{f"test_{k_}": v for k_, v in m.items()},
                     "test_stress_media_%": ms.get("media_%"), "test_ritardo30_media_%": m30.get("media_%"),
                     "verdetto": "VANTAGGIO" if edge else "no"})
    tt = pd.DataFrame(rows)
    r.table(tt)
    r(f"\n**Strategie con un vantaggio dimostrato fuori campione: {int((tt.verdetto == 'VANTAGGIO').sum())}.**")
    try:  # machine-readable results for the ranking engine
        from common import OUT
        OUT.mkdir(parents=True, exist_ok=True)
        sel.drop(columns=["_ix", "_c"]).to_csv(OUT / "discovery_launch_candidates.csv", index=False)
        tt.to_csv(OUT / "discovery_launch_test.csv", index=False)
        cmp_tab.to_csv(OUT / "discovery_launch_all_candidates.csv", index=False)
    except Exception as e:
        print(f"csv: {e}", flush=True)
    r.save()


if __name__ == "__main__":
    main()
