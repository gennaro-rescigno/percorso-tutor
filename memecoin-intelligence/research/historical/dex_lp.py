"""Study 'dex_lp': earning like "the house" - providing liquidity to memecoin pools on PumpSwap for 1 hour to 3 days.

Buyers of memecoins lose on average (sections 9.x). Liquidity providers earn a fee on every trade instead
(PumpSwap: 0.20% of each trade goes to the pool's liquidity providers and stays in the pool; anyone can add
liquidity to a graduated token's pool), but they hold half of the position in the token, so when the token falls
they lose too ("impermanent loss"). Question: do the fees beat the loss, net of all costs?

Mechanics used (constant-product pool, full range): measured in SOL, a liquidity position is worth
sqrt(price_out / price_in) x (1 + fees earned), where the fees earned per unit of liquidity are the sum over the
holding window of 0.20% x traded volume / pool value (pool value = 2 x SOL reserve).

PRE-REGISTERED (written before looking at any result):
  * data A: jocry postgard_snapshots (June-July 2026, PumpSwap pools of graduated pump.fun tokens, snapshots about
    every 5 minutes; USD prices converted to SOL with Binance SOLUSDT hourly closes; the volume of a snapshot is
    counted for at most the 5 minutes since the previous one, so gaps lower the fees, never raise them);
    data B: fly-trader-seed pump_minutes (one week of September 2026, every PumpSwap trade in 1-minute candles with
    the pool's SOL reserve; no trade = unchanged price, which is exact for a pool); B is the other period, used only
    to check what A shows; in B tokens first seen in the first 12 hours of the week are dropped (unknown age);
  * position 1 SOL: half is swapped into the token (pool fee + price impact (0.5 SOL / reserve)), both halves are
    deposited; at the exit the liquidity is withdrawn and the token half is sold (pool fee + impact (value / 2 /
    reserve)); network fees 0.001 SOL; pool fee: B the pool's own fee rate, A the PumpSwap market-cap tiers (1.25%
    at <= $100k down to 0.30% at $20M, as in the bot's cost model); LP fee 0.20% of volume;
  * decision points: every snapshot (A) / the end of every hour after the first trade (B); one position per token,
    rule and day (the first moment that meets the rule); holds 1, 4, 24 and 72 hours; exit at the first observation
    at or after the hold (A) or the last price at or before it (B); a hold ending after the end of the data is
    dropped; A tokens that stop being observed before the exit: last observation (optimistic) and a second reading
    with the price -90% after the last observation (pessimistic);
  * rules (R = SOL reserve of the pool, T = last hour's volume / pool value):
      Q0 any moment, R >= 20 (reference);
      Q1 busy pool: R >= 20, T >= 1;
      Q2 survivor: age >= 24 h, R >= 50, T >= 0.25;
      Q3 calm survivor: Q2 and price change over the last 6 hours within +-20%;
      Q4 two-way flow: age >= 2 h, R >= 50, T >= 0.5, buys between 40% and 60% of the trades of the last hour;
  * also shown for the same moments: simply buying the token (to see what the liquidity position changes);
  * statistics: mean net return per position with bootstrap 95% interval, Benjamini-Hochberg over all tests;
    verdict "positiva" only with q < 0.05 and a positive mean in both halves of A; "portabile" if B is positive too.
"""

from __future__ import annotations

import io
import urllib.parse
import zipfile

import duckdb
import numpy as np
import pandas as pd

from common import DATA, JOCRY, Report, download
from crypto_data import FILES, _get, list_prefixes
from loop_curve import bh, boot_mean

LP_FEE, SIZE, NET_FEE = 0.002, 1.0, 0.001
HOLDS_H = (1, 4, 24, 72)
RULES = ("Q0", "Q1", "Q2", "Q3", "Q4")


def tier_fee(mcap_usd: np.ndarray) -> np.ndarray:
    lo, hi = 1e5, 2e7
    mc = np.clip(np.nan_to_num(mcap_usd, nan=lo), lo, hi)
    frac = (np.log(mc) - np.log(lo)) / (np.log(hi) - np.log(lo))
    return 0.0125 - frac * (0.0125 - 0.0030)


def rule_mask(d: pd.DataFrame, rule: str) -> np.ndarray:
    R, T, age = d.R.to_numpy(), d["turn"].to_numpy(), d.age_h.to_numpy()
    if rule == "Q0":
        m = R >= 20
    elif rule == "Q1":
        m = (R >= 20) & (T >= 1)
    elif rule in ("Q2", "Q3"):
        m = (age >= 24) & (R >= 50) & (T >= 0.25)
        if rule == "Q3":
            m &= np.abs(d.r6h.to_numpy()) <= 0.20
    elif rule == "Q4":
        bs = d.buy_share.to_numpy()
        m = (age >= 2) & (R >= 50) & (T >= 0.5) & (bs >= 0.4) & (bs <= 0.6)
    else:
        raise ValueError(rule)
    return np.nan_to_num(m, nan=0).astype(bool)


def lp_net(p_in, p_out, F, R_in, R_out, fee) -> np.ndarray:
    gross = np.sqrt(p_out / p_in) * (1 + F)
    imp_in = np.clip(0.5 * SIZE / R_in, 0, 0.9)
    value = SIZE * gross
    imp_out = np.clip(0.5 * value / np.where(R_out > 0, R_out, np.nan), 0, 0.9)
    imp_out = np.nan_to_num(imp_out, nan=0.9)
    return (1 - (fee + imp_in) / 2) * gross * (1 - (fee + imp_out) / 2) - NET_FEE / SIZE - 1


def buy_net(p_in, p_out, R_in, R_out, fee) -> np.ndarray:
    imp_in = np.clip(SIZE / R_in, 0, 0.9)
    value = SIZE * p_out / p_in
    imp_out = np.nan_to_num(np.clip(value / np.where(R_out > 0, R_out, np.nan), 0, 0.9), nan=0.9)
    return (p_out / p_in) * (1 - fee - imp_in) * (1 - fee - imp_out) - NET_FEE / SIZE - 1


# ----------------------------------------------------------------------------------------------- data A
def sol_usd_hourly() -> pd.Series:
    keys = [k for k in list_prefixes("data/spot/monthly/klines/SOLUSDT/1h/") if k.endswith(".zip")
            and any(f"-2026-{m:02d}" in k for m in range(5, 11))]
    frames = []
    for k in keys:
        z = zipfile.ZipFile(io.BytesIO(_get(f"{FILES}/{urllib.parse.quote(k)}")))
        with z.open(z.namelist()[0]) as f:
            df = pd.read_csv(f, header=None, usecols=[0, 4])
        if not str(df.iloc[0, 0]).isdigit():
            df = df.iloc[1:]
        frames.append(df.astype(float))
    df = pd.concat(frames)
    ot = df[0].where(df[0] < 1e14, df[0] // 1000) / 1000  # seconds; the close is at open + 1 h
    return pd.Series(df[4].to_numpy(), index=(ot + 3600).to_numpy()).sort_index()


def points_a() -> tuple[pd.DataFrame, pd.DataFrame]:
    p = download(JOCRY, "postgard_snapshots.parquet")
    s = pd.read_parquet(p, columns=["mint", "snapshot_time", "seconds_since_graduation", "price_usd", "price_change_6h",
                                    "liquidity_usd", "volume_5m", "volume_1h", "buys_1h", "sells_1h", "market_cap_usd"])
    s = s[(s.price_usd > 0) & (s.liquidity_usd > 0)].copy()
    s["t"] = (pd.to_datetime(s.snapshot_time, utc=True) - pd.Timestamp("1970-01-01", tz="UTC")).dt.total_seconds()
    s = s.sort_values(["mint", "t"]).reset_index(drop=True)
    sol = sol_usd_hourly()
    pos = np.clip(np.searchsorted(sol.index.to_numpy(), s.t.to_numpy(), side="right") - 1, 0, len(sol) - 1)
    solp = sol.to_numpy()[pos]
    s["p"] = s.price_usd / solp
    s["R"] = s.liquidity_usd / 2 / solp
    s["turn"] = s.volume_1h.fillna(0) / s.liquidity_usd
    s["age_h"] = s.seconds_since_graduation / 3600
    s["r6h"] = s.price_change_6h / 100
    tot = s.buys_1h + s.sells_1h
    s["buy_share"] = np.where(tot > 0, s.buys_1h / tot, np.nan)
    s["fee"] = tier_fee(s.market_cap_usd.to_numpy())
    dt = s.groupby("mint").t.diff().fillna(300).clip(0, 300) / 300
    s["F"] = (LP_FEE * s.volume_5m.fillna(0) * dt / s.liquidity_usd).groupby(s.mint).cumsum()
    s["day"] = (s.t // 86400).astype(int)
    return s, s[["mint", "t", "p", "R", "F"]]


def outcomes_a(e: pd.DataFrame, obs: pd.DataFrame, h: int, t_end: float) -> pd.DataFrame:
    e = e[e.t + h * 3600 <= t_end].copy()
    if e.empty:
        return e
    e["target"] = e.t + h * 3600
    e["i"] = np.arange(len(e))
    o = obs.rename(columns={"t": "x_t", "p": "x_p", "R": "x_R", "F": "x_F"}).sort_values("x_t")
    m = pd.merge_asof(e.sort_values("target"), o, left_on="target", right_on="x_t", by="mint",
                      direction="forward").sort_values("i")
    last = obs.groupby("mint")[["p", "R", "F"]].last()
    found = m.x_p.notna().to_numpy()
    e["found"] = found
    for k in ("p", "R", "F"):
        e[f"{k}_out"] = np.where(found, m[f"x_{k}"].to_numpy(), e.mint.map(last[k]).to_numpy())
    return e


# ----------------------------------------------------------------------------------------------- data B
def points_b(con: duckdb.DuckDBPyConnection) -> tuple[pd.DataFrame, pd.DataFrame, float]:
    import fly_rules

    pm = fly_rules.extract(con, Report("fly_extract_tmp"))
    con.execute(f"CREATE OR REPLACE VIEW pm AS SELECT * FROM read_parquet('{pm}') WHERE close > 0 AND resq_sol > 0")
    t0, t1 = con.execute("SELECT min(ts), max(ts) FROM pm").fetchone()
    df = con.execute(f"""
        WITH g AS (SELECT mint, min(ts) AS g0 FROM pm GROUP BY mint HAVING min(ts) >= {t0} + 12 * 3600),
        hb AS (SELECT p.mint, floor((p.ts - g.g0) / 3600)::INT AS b, arg_max(p.close, p.ts) AS close,
                      sum(p.buy_sol + p.sell_sol) AS vol, arg_max(p.resq_sol, p.ts) AS resq,
                      arg_max(p.fee_rate, p.ts) AS fee, sum(p.n_buys) AS nb, sum(p.n_sells) AS ns,
                      any_value(g.g0) AS g0
               FROM pm p JOIN g USING (mint) GROUP BY p.mint, b)
        SELECT mint, b, g0 + (b + 1) * 3600 AS t, close, vol, resq, fee, nb, ns FROM hb""").df()
    df = df.sort_values(["mint", "t"]).reset_index(drop=True)
    minute = con.execute(f"""SELECT mint, ts, close, resq_sol, buy_sol + sell_sol AS v FROM pm
                            WHERE mint IN (SELECT mint FROM pm GROUP BY mint HAVING min(ts) >= {t0} + 12 * 3600)
                            ORDER BY mint, ts""").df()
    minute["F"] = (LP_FEE * minute.v / (2 * minute.resq_sol)).groupby(minute.mint).cumsum()
    obs = minute.rename(columns={"ts": "t", "close": "p", "resq_sol": "R"})[["mint", "t", "p", "R", "F"]]
    # price 6 hours before (last trade at or before), for the calm rule
    left = df[["mint", "t"]].copy()
    left["q"] = left.t - 6 * 3600
    left["i"] = np.arange(len(left))
    m = pd.merge_asof(left.sort_values("q"), obs[["mint", "t", "p"]].rename(columns={"t": "x_t"}).sort_values("x_t"),
                      left_on="q", right_on="x_t", by="mint", direction="backward").sort_values("i")
    d = pd.DataFrame({"mint": df.mint, "t": df.t.astype(float), "p": df.close, "R": df.resq,
                      "turn": df.vol / (2 * df.resq), "age_h": (df.b + 1).astype(float),
                      "r6h": df.close.to_numpy() / m.p.to_numpy() - 1,
                      "buy_share": df.nb / (df.nb + df.ns).where(df.nb + df.ns > 0),
                      "fee": df.fee.fillna(0.0125).clip(0, 0.05)})
    # the fees earned so far at each decision point
    li = d[["mint", "t"]].copy()
    li["i"] = np.arange(len(li))
    mm = pd.merge_asof(li.sort_values("t"), obs[["mint", "t", "F"]].sort_values("t"), on="t", by="mint",
                       direction="backward").sort_values("i")
    d["F"] = mm.F.fillna(0).to_numpy()
    d["day"] = (d.t // 86400).astype(int)
    return d, obs, float(t1)


def outcomes_b(e: pd.DataFrame, obs: pd.DataFrame, h: int, t_end: float) -> pd.DataFrame:
    e = e[e.t + h * 3600 <= t_end].copy()
    if e.empty:
        return e
    e["target"] = e.t + h * 3600
    e["i"] = np.arange(len(e))
    o = obs.rename(columns={"t": "x_t", "p": "x_p", "R": "x_R", "F": "x_F"}).sort_values("x_t")
    m = pd.merge_asof(e.sort_values("target"), o, left_on="target", right_on="x_t", by="mint",
                      direction="backward").sort_values("i")
    e["found"] = True
    for k in ("p", "R", "F"):
        e[f"{k}_out"] = m[f"x_{k}"].to_numpy()
    return e


# ----------------------------------------------------------------------------------------------- evaluation
def evaluate(label: str, d: pd.DataFrame, obs: pd.DataFrame, t_end: float, outcomes, halves: bool) -> list[dict]:
    rows = []
    mid = None
    if halves:
        days = sorted(d.day.unique())
        mid = days[len(days) // 2]
    for rule in RULES:
        e0 = d[rule_mask(d, rule)].sort_values("t").drop_duplicates(["mint", "day"])
        for h in HOLDS_H:
            e = outcomes(e0, obs, h, t_end)
            if len(e) < 30:
                rows.append({"dati": label, "regola": rule, "tenuta_h": h, "n": len(e)})
                continue
            F = (e.F_out - e.F).clip(lower=0).to_numpy()
            readings = [("ottimistica", e.p_out.to_numpy(), e.R_out.to_numpy())]
            if not e.found.all():
                pess_p = np.where(e.found, e.p_out, 0.1 * e.p_out)
                pess_R = np.where(e.found, e.R_out, np.sqrt(0.1) * e.R_out)
                readings.append(("pessimistica", pess_p, pess_R))
            for rd, p_out, R_out in readings:
                y = lp_net(e.p.to_numpy(), p_out, F, e.R.to_numpy(), R_out, e.fee.to_numpy())
                yb = buy_net(e.p.to_numpy(), p_out, e.R.to_numpy(), R_out, e.fee.to_numpy())
                y = np.nan_to_num(y, nan=-1.0)
                lo, hi, p = boot_mean(y)
                rw = {"dati": label, "regola": rule, "tenuta_h": h, "lettura": rd, "n": len(e),
                      "osservati_%": 100 * e.found.mean(), "media_%": 100 * y.mean(), "IC95_basso_%": 100 * lo,
                      "IC95_alto_%": 100 * hi, "p": p, "mediana_%": 100 * np.median(y), "vincenti_%": 100 * (y > 0).mean(),
                      "commissioni_guadagnate_medie_%": 100 * F.mean(),
                      "effetto_prezzo_medio_%": 100 * (np.sqrt(p_out / e.p.to_numpy()) - 1).mean(),
                      "comprare_media_%": 100 * np.nan_to_num(yb, nan=-1.0).mean()}
                if halves:
                    first = (e.day < mid).to_numpy()
                    rw["1a_metà_%"] = 100 * y[first].mean() if first.any() else np.nan
                    rw["2a_metà_%"] = 100 * y[~first].mean() if (~first).any() else np.nan
                rows.append(rw)
    return rows


def main() -> None:
    r = Report("dex_lp")
    r("# Studio storico: fornire liquidità ai pool delle memecoin (PumpSwap), da 1 ora a 3 giorni")
    r("\n" + __doc__.split("PRE-REGISTERED")[0].split("\n\n", 1)[1].strip())
    r("\nPre-registrazione (testo originale):\n\n```\n" + __doc__.split("PRE-REGISTERED")[1].strip() + "\n```")
    a, obs_a = points_a()
    r(f"A (giugno-luglio): {len(a):,} momenti di {a.mint.nunique():,} token, {a.day.nunique()} giorni; intervallo "
      f"mediano tra le osservazioni {a.groupby('mint').t.diff().median():.0f} s.")
    rows = evaluate("A giu-lug", a, obs_a, float(a.t.max()), outcomes_a, halves=True)
    del a, obs_a
    con = duckdb.connect()
    con.execute("SET memory_limit='5GB'; SET temp_directory='/tmp/duck'; SET preserve_insertion_order=false")
    b, obs_b, t_end = points_b(con)
    r(f"B (settembre, altra fonte): {len(b):,} momenti orari di {b.mint.nunique():,} token.")
    rows += evaluate("B settembre", b, obs_b, t_end, outcomes_b, halves=False)
    tab = pd.DataFrame(rows)
    ok = tab.p.notna() if "p" in tab else pd.Series(False, index=tab.index)
    tab["q_BH"] = np.nan
    if ok.any():
        tab.loc[ok, "q_BH"] = bh(tab.loc[ok, "p"].tolist())
    verdict = []
    for _, x in tab.iterrows():
        if x.get("dati") != "A giu-lug" or pd.isna(x.get("q_BH")):
            verdict.append("")
            continue
        pos = x.q_BH < 0.05 and x.get("1a_metà_%", -1) > 0 and x.get("2a_metà_%", -1) > 0
        bmatch = tab[(tab.dati == "B settembre") & (tab.regola == x.regola) & (tab.tenuta_h == x.tenuta_h)]
        port = pos and len(bmatch) and (bmatch["media_%"] > 0).all()
        verdict.append("positiva e portabile" if port else ("positiva" if pos else "non dimostrata"))
    tab["verdetto"] = verdict
    r.table(tab)
    r.save()


if __name__ == "__main__":
    main()
