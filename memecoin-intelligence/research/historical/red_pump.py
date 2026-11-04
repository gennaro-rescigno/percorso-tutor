"""Study 'red_pump': do the PROJECT's declared links and description predict a graduation? (pump.fun, May-June 2026)

Data: AratiKamat/red-pump-2026 (CC BY 4.0): 860,213 launches with the metadata known at creation (X / website /
Telegram link present, description length, initial market cap) and a collector-recorded label (bonding curve
filled within 24 hours or not). It answers "evaluate the projects" with data that exist at the moment of the
decision. Limit: there are no prices, so it measures the probability of a graduation, not a profit (section 9.2
showed that the curve price already reflects that probability).

PRE-REGISTERED (written before looking at any result): days split by creation time: May 8-31 (model fitted) and
June 1-10 (measured); graduation rate by link presence, description length (0, 1-50, 51-200, > 200 characters) and
initial market cap tercile; AUC of each signal and of a logistic regression on all of them (fitted on May, measured
on June), with a 95% interval; lift of the model's top 10% over the base rate.
"""

from __future__ import annotations

import gzip
import io
import json

import numpy as np
import pandas as pd

from common import Report, download
from discovery_launch import auc

DS = "AratiKamat/red-pump-2026"
SPLIT = pd.Timestamp("2026-06-01", tz="UTC").timestamp() * 1000


def main() -> None:
    from sklearn.linear_model import LogisticRegression

    r = Report("red_pump")
    r("# I progetti (link social, descrizione) predicono il diploma? (pump.fun, 8 maggio - 10 giugno 2026)")
    r("\n" + __doc__.split("\n\n", 1)[1].strip())
    lp = download(DS, "red_pump_2026_v1_launches.jsonl.gz")
    rows = []
    with gzip.open(lp, "rt") as f:
        for line in f:
            try:
                o = json.loads(line)
            except Exception:
                continue
            rows.append((o.get("mint"), o.get("created_timestamp"), o.get("initial_market_cap_sol"), o.get("has_twitter"),
                         o.get("has_website"), o.get("has_telegram"), o.get("description_length")))
    la = pd.DataFrame(rows, columns=["mint", "created", "mcap0", "tw", "web", "tg", "desc"]).drop_duplicates("mint")
    op = download(DS, "red_pump_2026_v1_outcomes.csv.gz")
    # the file mixes two schemas: read every line and take the outcome word and the mint wherever they are
    import csv
    import re
    b58 = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")
    recs, bad = [], 0
    with gzip.open(op, "rt", errors="replace") as f:
        for row in csv.reader(f):
            outc = next((x for x in row if x in ("GRADUATED", "TIMEOUT")), None)
            mint = next((x for x in row if b58.match(x)), None)
            if outc is None or mint is None:
                bad += 1
                continue
            recs.append((mint, outc))
    oc = pd.DataFrame(recs, columns=["mint", "outcome"]).drop_duplicates("mint")
    r(f"Lanci: {len(la):,}; esiti leggibili: {len(oc):,} (righe senza esito o mint riconoscibili: {bad:,}).")
    d = la.merge(oc, on="mint", how="inner")
    d["grad"] = (d.outcome.astype(str).str.upper() == "GRADUATED").astype(int)
    for c in ("tw", "web", "tg"):
        d[c] = d[c].fillna(False).astype(bool).astype(int)
    d["desc"] = pd.to_numeric(d.desc, errors="coerce").fillna(0)
    d["mcap0"] = pd.to_numeric(d.mcap0, errors="coerce")
    d["created"] = pd.to_numeric(d.created, errors="coerce")
    d = d.dropna(subset=["created"])
    d["links"] = d.tw + d.web + d.tg
    d["desc_bin"] = pd.cut(d.desc, [-1, 0, 50, 200, 1e9], labels=["0", "1-50", "51-200", "> 200"])
    tr, te = d[d.created < SPLIT], d[d.created >= SPLIT]
    r(f"Con esito: {len(d):,} (maggio {len(tr):,}, giugno {len(te):,}); diplomati: {100 * d.grad.mean():.2f}% "
      f"(maggio {100 * tr.grad.mean():.2f}%, giugno {100 * te.grad.mean():.2f}%).")
    r("\n## Tasso di diploma per caratteristica del progetto (giugno, mai usato per adattare nulla)")
    rows = []
    for col, lab in (("tw", "link X"), ("web", "sito"), ("tg", "Telegram"), ("links", "numero di link"),
                     ("desc_bin", "lunghezza della descrizione")):
        for v, g in te.groupby(col, observed=True):
            rows.append({"caratteristica": lab, "valore": str(v), "lanci": len(g), "diplomati_%": 100 * g.grad.mean()})
    q = tr.mcap0.quantile([1 / 3, 2 / 3]).to_numpy()
    te = te.assign(mcap_t=np.digitize(te.mcap0.fillna(q[0]), q))
    for v, g in te.groupby("mcap_t"):
        rows.append({"caratteristica": "capitalizzazione iniziale (terzile di maggio)", "valore": str(int(v) + 1),
                     "lanci": len(g), "diplomati_%": 100 * g.grad.mean()})
    r.table(pd.DataFrame(rows))
    r("\n## Capacità di previsione (AUC su giugno; 0,5 = nessuna informazione)")
    feats = ["tw", "web", "tg", "links", "desc", "mcap0"]
    rows = []
    for fe in feats:
        a, se = auc(te[fe].to_numpy(np.float64), te.grad.to_numpy())
        rows.append({"segnale": fe, "AUC": a, "IC95": f"[{a - 1.96 * se:.3f}, {a + 1.96 * se:.3f}]" if a == a else "–"})
    X_tr = tr[feats].fillna(tr[feats].median()).to_numpy(np.float64)
    X_te = te[feats].fillna(tr[feats].median()).to_numpy(np.float64)
    mu, sd = X_tr.mean(0), X_tr.std(0) + 1e-9
    m = LogisticRegression(max_iter=500).fit((X_tr - mu) / sd, tr.grad)
    p = m.predict_proba((X_te - mu) / sd)[:, 1]
    a, se = auc(p, te.grad.to_numpy())
    rows.append({"segnale": "regressione logistica su tutti", "AUC": a, "IC95": f"[{a - 1.96 * se:.3f}, {a + 1.96 * se:.3f}]"})
    r.table(pd.DataFrame(rows))
    top = p >= np.quantile(p, 0.9)
    r(f"Il 10% dei lanci con la previsione più alta si diploma nel **{100 * te.grad.to_numpy()[top].mean():.2f}%** dei casi, "
      f"contro il {100 * te.grad.mean():.2f}% di tutti (x{te.grad.to_numpy()[top].mean() / max(te.grad.mean(), 1e-9):.1f}).")
    r.save()


if __name__ == "__main__":
    main()
