"""Study 'dex_model': a portable model for LISTED tokens (any DEX pool), holds of 1 and 4 hours.

Train/test A: jocry postgard_snapshots (Jun-Jul 2026, 5,700 graduated tokens, DEX snapshots about every 5 minutes).
Test B (other period, other source): fly-trader-seed pump_minutes (Sep 14-21 2026, 28,721 tokens, 1-minute candles),
hourly decision points; the model is trained on ALL of A and applied to B unchanged.

PRE-REGISTERED (written before looking at any result):
  * features, all unit-free so they exist for any token on any DEX: age since listing (h), return over 5 minutes,
    1 hour and 6 hours, return since listing, distance from the highest price so far, 1-hour volume / liquidity,
    5-minute volume / 1-hour volume (acceleration), buys / (buys + sells) in the last hour (count), log of the
    trades in the last hour, market cap / liquidity;
  * targets: net return of a 0.1 SOL trade held 1 and 4 hours, exit at the first observation at or after that time;
    costs: 3% latency, 1% pool fee per side, 1% priority fees; a token with no later observation is valued at its
    last observation (optimistic) and, as a second reading, at -100% (pessimistic): both are reported;
  * model: scikit-learn HistGradientBoostingRegressor (fixed settings), target clipped to [-100%, +300%];
    A: walk-forward by day (first 14 days for training, retrained every 3 days); B: trained once on all of A;
  * selections, one trade per token and day (first selected moment): every moment (reference), predicted > 0,
    top 5%, top 1% of the training predictions;
  * verdict "positive" only with q (Benjamini-Hochberg over all tests) < 0.05 and both halves of A positive; a rule
    is "portable" only if it is also positive on B (the other period).
"""

from __future__ import annotations

import os
import subprocess

import duckdb
import numpy as np
import pandas as pd

from common import DATA, JOCRY, Report, download
from loop_curve import bh, boot_mean

LAT, FEE, PRIO = 0.03, 0.01, 0.01
HOLDS_H = (1, 4)
FEATS = ["age_h", "r5m", "r1h", "r6h", "r_since", "dd", "vol_liq", "accel", "buy_share", "log_trades", "mcap_liq"]


def net(gross: np.ndarray) -> np.ndarray:
    return gross / (1 + LAT) * (1 - FEE) ** 2 - PRIO - 1


# ----------------------------------------------------------------------------------------------- dataset A
def jocry_points() -> pd.DataFrame:
    p = download(JOCRY, "postgard_snapshots.parquet")
    s = pd.read_parquet(p, columns=["mint", "snapshot_time", "seconds_since_graduation", "price_usd", "price_change_5m",
                                    "price_change_1h", "price_change_6h", "liquidity_usd", "volume_5m", "volume_1h",
                                    "buys_1h", "sells_1h", "market_cap_usd"])
    s = s[(s.price_usd > 0) & (s.liquidity_usd > 0)].copy()
    s["t"] = pd.to_datetime(s.snapshot_time, utc=True).astype("int64") / 1e9
    s = s.sort_values(["mint", "t"])
    g = s.groupby("mint")
    s["age_h"] = s.seconds_since_graduation / 3600
    s["r5m"], s["r1h"], s["r6h"] = s.price_change_5m / 100, s.price_change_1h / 100, s.price_change_6h / 100
    s["r_since"] = s.price_usd / g.price_usd.transform("first") - 1
    s["dd"] = 1 - s.price_usd / g.price_usd.cummax()
    s["vol_liq"] = s.volume_1h / s.liquidity_usd
    s["accel"] = np.where(s.volume_1h > 0, s.volume_5m / s.volume_1h, np.nan)
    tot = s.buys_1h + s.sells_1h
    s["buy_share"] = np.where(tot > 0, s.buys_1h / tot, np.nan)
    s["log_trades"] = np.log1p(tot)
    s["mcap_liq"] = s.market_cap_usd / s.liquidity_usd
    s["px"] = s.price_usd
    s["day"] = (s.t // 86400).astype(int)
    return s[["mint", "t", "day", "px"] + FEATS]


def add_targets(d: pd.DataFrame, obs: pd.DataFrame) -> pd.DataFrame:
    """Exit price = first observation at or after t + hold; else the last one (and a pessimistic flag)."""
    obs = obs[["mint", "t", "px"]].rename(columns={"t": "x_t", "px": "x_px"}).sort_values("x_t")
    last = obs.groupby("mint").x_px.last()
    for h in HOLDS_H:
        left = d[["mint", "t"]].copy()
        left["target"] = left.t + h * 3600
        left["i"] = np.arange(len(left))
        m = pd.merge_asof(left.sort_values("target"), obs, left_on="target", right_on="x_t", by="mint",
                          direction="forward").sort_values("i")
        found = m.x_px.notna().to_numpy()
        px_out = np.where(found, m.x_px.to_numpy(), d.mint.map(last).to_numpy())
        d[f"y{h}"] = net(px_out / d.px.to_numpy())
        d[f"y{h}_pess"] = np.where(found, d[f"y{h}"], -1.0)
        d[f"found{h}"] = found
    return d


# ----------------------------------------------------------------------------------------------- dataset B
def fly_points(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    import fly_rules

    pm = fly_rules.extract(con, Report("fly_extract_tmp"))
    con.execute(f"CREATE OR REPLACE VIEW pm AS SELECT * FROM read_parquet('{pm}') WHERE close > 0")
    raw = con.execute(f"SELECT * FROM read_parquet('{pm}') LIMIT 0").df()
    has_counts = "n_buys" in raw.columns
    counts = "sum(n_buys) AS nb, sum(n_sells) AS ns" if has_counts else "sum(n_traders) AS nb, 0 AS ns"
    df = con.execute(f"""
        WITH g AS (SELECT mint, min(ts) AS g0, arg_min(close, ts) AS p0 FROM pm GROUP BY mint),
        hb AS (SELECT p.mint, floor((p.ts - g.g0) / 3600)::INT AS b, arg_max(p.close, p.ts) AS close,
                      max(p.high) AS high, sum(p.buy_sol + p.sell_sol) AS vol, arg_max(p.resq_sol, p.ts) AS resq,
                      {counts}, any_value(g.g0) AS g0, any_value(g.p0) AS p0
               FROM pm p JOIN g USING (mint) GROUP BY p.mint, b)
        SELECT mint, b, g0 + (b + 1) * 3600 AS t, close, vol, resq, nb, ns, p0,
               max(high) OVER (PARTITION BY mint ORDER BY b ROWS UNBOUNDED PRECEDING) AS peak
        FROM hb""").df()
    df = df.sort_values(["mint", "t"])
    minute = con.execute("SELECT mint, ts, close, buy_sol + sell_sol AS v FROM pm").df().sort_values("ts")

    def asof_close(lag_s: float) -> np.ndarray:
        left = df[["mint", "t"]].copy()
        left["q"] = left.t - lag_s
        left["i"] = np.arange(len(left))
        m = pd.merge_asof(left.sort_values("q"), minute[["mint", "ts", "close"]], left_on="q", right_on="ts",
                          by="mint", direction="backward").sort_values("i")
        return m.close.to_numpy()

    out = pd.DataFrame({"mint": df.mint.to_numpy(), "t": df.t.to_numpy()})
    out["px"] = df.close.to_numpy()
    out["age_h"] = (df.b + 1).to_numpy()
    for name, lag in (("r5m", 300), ("r1h", 3600), ("r6h", 21600)):
        prev = asof_close(lag)
        out[name] = out.px / prev - 1
    out["r_since"] = out.px / df.p0.to_numpy() - 1
    out["dd"] = 1 - out.px / df.peak.to_numpy()
    liq = 2 * df.resq.to_numpy()
    out["vol_liq"] = df.vol.to_numpy() / np.where(liq > 0, liq, np.nan)
    v5 = minute.assign(cv=minute.groupby("mint").v.cumsum())
    def cum_at(q):
        l2 = df[["mint"]].copy()
        l2["q"] = q
        l2["i"] = np.arange(len(l2))
        m = pd.merge_asof(l2.sort_values("q"), v5[["mint", "ts", "cv"]], left_on="q", right_on="ts", by="mint",
                          direction="backward").sort_values("i")
        return m.cv.fillna(0).to_numpy()
    vol5 = cum_at(df.t.to_numpy()) - cum_at(df.t.to_numpy() - 300)
    out["accel"] = np.where(df.vol.to_numpy() > 0, vol5 / df.vol.to_numpy(), np.nan)
    tot = (df.nb + df.ns).to_numpy()
    out["buy_share"] = np.where(tot > 0, df.nb.to_numpy() / np.where(tot > 0, tot, 1), np.nan) if has_counts else np.nan
    out["log_trades"] = np.log1p(tot)
    out["mcap_liq"] = out.px * 1e9 / np.where(liq > 0, liq, np.nan)
    out["day"] = (out.t // 86400).astype(int)
    obs = minute.rename(columns={"ts": "t", "close": "px"})
    return add_targets(out, obs)


# ----------------------------------------------------------------------------------------------- evaluation
def select(te: pd.DataFrame, p_tr: np.ndarray) -> dict[str, pd.Series]:
    return {"P0 ogni momento": te.pred > -np.inf, "P1 previsto > 0": te.pred > 0,
            "P2 5% più alto": te.pred >= np.quantile(p_tr, 0.95), "P3 1% più alto": te.pred >= np.quantile(p_tr, 0.99)}


def stats_row(pick: pd.DataFrame, ycol: str, extra: dict, mid_day: int | None) -> dict:
    x = pick[ycol].to_numpy()
    lo, hi, p = boot_mean(x)
    row = {**extra, "n": len(x), "media_%": 100 * x.mean(), "IC95_basso_%": 100 * lo, "IC95_alto_%": 100 * hi,
           "p": p, "mediana_%": 100 * np.median(x), "vincenti_%": 100 * (x > 0).mean()}
    if mid_day is not None:
        e = (pick.day < mid_day).to_numpy()
        row["1a_metà_%"] = 100 * x[e].mean() if e.any() else np.nan
        row["2a_metà_%"] = 100 * x[~e].mean() if (~e).any() else np.nan
    return row


def model():
    from sklearn.ensemble import HistGradientBoostingRegressor

    return HistGradientBoostingRegressor(max_iter=200, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=200,
                                         l2_regularization=1.0, random_state=0)


def main() -> None:
    r = Report("dex_model")
    r("# Studio storico: un modello portabile per i token quotati, tenuta 1 e 4 ore")
    r("\nPre-registrazione (testo originale):\n\n```\n" + __doc__.split("PRE-REGISTERED")[1].strip() + "\n```")
    a = jocry_points()
    a = add_targets(a, a)
    r(f"A (giugno-luglio): {len(a):,} momenti di decisione di {a.mint.nunique():,} token, {a.day.nunique()} giorni.")
    rows = []
    days = sorted(a.day.unique())
    for h in HOLDS_H:
        preds = []
        for k in range(14, len(days), 3):
            tdays = days[k:k + 3]
            tr, te = a[a.day < tdays[0]], a[a.day.isin(tdays)].copy()
            if len(tr) < 1000 or te.empty:
                continue
            m = model().fit(tr[FEATS], tr[f"y{h}"].clip(-1, 3))
            te["pred"] = m.predict(te[FEATS])
            p_tr = m.predict(tr[FEATS])
            te["q95"], te["q99"] = np.quantile(p_tr, 0.95), np.quantile(p_tr, 0.99)
            preds.append(te)
        if not preds:
            continue
        te = pd.concat(preds)
        mid = sorted(te.day.unique())[len(te.day.unique()) // 2]
        sels = {"P0 ogni momento": te.pred > -np.inf, "P1 previsto > 0": te.pred > 0,
                "P2 5% più alto": te.pred >= te.q95, "P3 1% più alto": te.pred >= te.q99}
        for name, msk in sels.items():
            pick = te[msk].sort_values("t").drop_duplicates(["mint", "day"])
            if len(pick) < 30:
                continue
            for ycol, lab in ((f"y{h}", "ottimistica"), (f"y{h}_pess", "pessimistica")):
                rows.append(stats_row(pick, ycol, {"dati": "A giu-lug", "tenuta_h": h, "selezione": name,
                                                   "lettura": lab}, mid))
    # B: other period, other source; trained on all of A
    try:
        con = duckdb.connect(str(DATA / "dex.duckdb"))
        con.execute("SET memory_limit='5GB'; SET temp_directory='/tmp/duck'")
        b = fly_points(con)
        r(f"B (settembre, altra fonte): {len(b):,} momenti orari di {b.mint.nunique():,} token.")
        for h in HOLDS_H:
            m = model().fit(a[FEATS], a[f"y{h}"].clip(-1, 3))
            p_tr = m.predict(a[FEATS])
            b["pred"] = m.predict(b[FEATS])
            for name, msk in select(b, p_tr).items():
                pick = b[msk].sort_values("t").drop_duplicates(["mint", "day"])
                if len(pick) < 30:
                    continue
                for ycol, lab in ((f"y{h}", "ottimistica"), (f"y{h}_pess", "pessimistica")):
                    rows.append(stats_row(pick, ycol, {"dati": "B settembre", "tenuta_h": h, "selezione": name,
                                                       "lettura": lab}, None))
    except Exception as e:  # B is a bonus check: report and keep A
        r(f"B non disponibile: {type(e).__name__}: {str(e)[:300]}")
    tab = pd.DataFrame(rows)
    if not tab.empty:
        tab["q_BH"] = bh(tab.p.tolist())
        ok_a = (tab.dati.str.startswith("A") & (tab.q_BH < 0.05) & (tab["IC95_basso_%"] > 0)
                & (tab.get("1a_metà_%", 0) > 0) & (tab.get("2a_metà_%", 0) > 0))
        ok_b = tab.dati.str.startswith("B") & (tab.q_BH < 0.05) & (tab["IC95_basso_%"] > 0)
        tab["verdetto"] = np.where(ok_a | ok_b, "positiva", "non dimostrata")
    r.table(tab)
    r.save()


if __name__ == "__main__":
    main()
