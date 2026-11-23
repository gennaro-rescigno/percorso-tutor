"""
Lancia il backtest della strategia "London High sweep" e scrive i risultati
in risultati/RISULTATI.md (+ grafico dell'equity).

    python backtest.py

Cosa fa:
  1. testa la regola con i parametri del video (stop 20, target 9R, limite 10 punti sopra il London High)
  2. la confronta con un "gemello casuale": stesso stop e target, ma entrata short a un orario
     a caso nella stessa finestra, SENZA nessuno sweep. Se la strategia non batte il caso,
     lo sweep non aggiunge niente.
  3. prova tante varianti (stop, rapporto R, offset, modalità, lato) per vedere se il risultato
     dipende da un parametro fortunato
  4. divide i dati in due: anni vecchi (per scegliere) e anni recenti (per verificare)
"""

import itertools
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from scarica_dati import carica
from strategia import Parametri, _gestisci_posizione, _m, esegui, prepara, statistiche

QUI = Path(__file__).parent
OUT = QUI / "risultati"
ANNO_DIVISIONE = 2022  # in-sample: < 2022, out-of-sample: >= 2022
DOLLARI_PUNTO_MNQ = 2.0
CONTRATTI = 4  # come nel video


def gemello_casuale(giorni, p: Parametri, seed: int = 0) -> pd.DataFrame:
    """Short a un minuto casuale della finestra di entrata, stesso stop/target in punti."""
    rng = np.random.default_rng(seed)
    righe = []
    for g in giorni:
        finestra = np.where((g.minuto >= _m(p.entrata_inizio)) & (g.minuto < _m(p.entrata_fine)))[0]
        if len(finestra) < 30:
            continue
        i = int(rng.choice(finestra))
        entrata = g.c[i]
        stop, target = entrata + p.stop_punti, entrata - p.rr * p.stop_punti
        _, uscita, motivo = _gestisci_posizione(g, i + 1, "short", stop, target, p)
        punti = entrata - uscita - p.costo_punti
        righe.append({"giorno": g.data, "motivo": motivo, "punti_netti": punti, "r_netto": punti / p.stop_punti})
    return pd.DataFrame(righe)


def per_anno(tr: pd.DataFrame) -> pd.DataFrame:
    g = tr.assign(anno=pd.to_datetime(tr["giorno"]).dt.year).groupby("anno")
    return pd.DataFrame({
        "trade": g.size(),
        "win_rate_%": g["r_netto"].apply(lambda r: round(100 * (r > 0).mean(), 1)),
        "R_totale": g["r_netto"].sum().round(1),
        "dollari_4_MNQ": (g["punti_netti"].sum() * DOLLARI_PUNTO_MNQ * CONTRATTI).round(0),
    })


def griglia(df: pd.DataFrame) -> pd.DataFrame:
    righe = []
    for modalita, lati in [("limite", "short"), ("limite", "long"), ("limite", "entrambi"),
                           ("conferma", "short"), ("conferma", "entrambi")]:
        stop_list = [10, 20, 30, 50] if modalita == "limite" else [None]
        offset_list = [0, 10, 25] if modalita == "limite" else [None]
        for stop, rr, off in itertools.product(stop_list, [1, 2, 3, 5, 9], offset_list):
            p = Parametri(modalita=modalita, lati=lati, rr=rr)
            if stop is not None:
                p = replace(p, stop_punti=stop, offset_punti=off)
            tr = esegui(df, p)
            for parte, sub in [("IS", tr[pd.to_datetime(tr["giorno"]).dt.year < ANNO_DIVISIONE]),
                               ("OOS", tr[pd.to_datetime(tr["giorno"]).dt.year >= ANNO_DIVISIONE])]:
                s = statistiche(sub)
                righe.append({"modalita": modalita, "lati": lati, "stop": stop, "offset": off, "rr": rr,
                              "parte": parte} | {k: s.get(k) for k in ["trade", "win_rate_%", "R_medio", "R_totale", "t_stat"]})
    return pd.DataFrame(righe)


def tabella_md(df: pd.DataFrame) -> str:
    df = df.reset_index() if df.index.name else df
    righe = ["| " + " | ".join(map(str, df.columns)) + " |", "|" + "---|" * len(df.columns)]
    righe += ["| " + " | ".join("" if pd.isna(v) else str(v) for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join(righe)


def grafico(tr: pd.DataFrame, casuale: pd.DataFrame, file: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10, 4.5), dpi=120)
    ax.plot(pd.to_datetime(tr["giorno"]), tr["r_netto"].cumsum(), label="London High sweep (parametri del video)", color="#c0392b")
    ax.plot(pd.to_datetime(casuale["giorno"]), casuale["r_netto"].cumsum(), label="short a orario casuale (stesso stop/target)", color="#7f8c8d")
    ax.axhline(0, color="black", lw=0.6)
    ax.set_ylabel("R cumulati (al netto dei costi)")
    ax.set_title("Equity in R: 1R = 20 punti = 160 $ con 4 MNQ")
    ax.legend(loc="best", frameon=False)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(file)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    df = prepara(carica())  # lista di giorni
    giorni = len(df)
    inizio, fine = df[0].ore[0], df[-1].ore[-1]
    print(f"Dati: {inizio} -> {fine}, {giorni} giorni")

    video = Parametri()
    tr = esegui(df, video)
    tr.to_csv(OUT / "trade_parametri_video.csv", index=False)
    s_video = statistiche(tr, giorni)
    casuale = gemello_casuale(df, video)
    s_casuale = statistiche(casuale.assign(stop=0, entrata=0), giorni)

    conferma = esegui(df, Parametri(modalita="conferma", rr=3))
    s_conf = statistiche(conferma, giorni)

    print("Video:", s_video)
    print("Casuale:", s_casuale)
    g = griglia(df)
    g.to_csv(OUT / "griglia_varianti.csv", index=False)

    try:
        grafico(tr, casuale, OUT / "equity.png")
    except ImportError:
        print("matplotlib non installato: niente grafico")

    oos = g[g["parte"] == "OOS"].drop(columns="parte")
    is_ = g[g["parte"] == "IS"].drop(columns="parte")
    chiavi = ["modalita", "lati", "stop", "offset", "rr"]
    unite = is_.merge(oos, on=chiavi, suffixes=("_IS", "_OOS"))
    migliori_is = unite.sort_values("R_medio_IS", ascending=False).head(10)

    md = [
        "# Backtest: London High sweep (strategia del video)",
        "",
        f"Dati: Nasdaq-100 a 1 minuto (Dukascopy), {inizio:%d/%m/%Y} → {fine:%d/%m/%Y}, {giorni} giorni di borsa.",
        "Costi: 0,75 punti a trade. Se stop e target cadono nello stesso minuto si conta lo stop.",
        "",
        "## 1. Parametri del video",
        "Short con ordine limite 10 punti sopra il London High (02:00-05:00 NY), entrata tra 9:30 e 11:00 NY,",
        "stop 20 punti, target 9R (180 punti), chiusura alle 15:55. Si salta il giorno se il London High",
        "era già stato rotto prima delle 9:30.",
        "",
        tabella_md(pd.DataFrame([s_video | {"nome": "sweep (video)"}, s_casuale | {"nome": "short casuale"},
                                 s_conf | {"nome": "sweep + conferma, 3R"}]).set_index("nome")),
        "",
        "![equity](equity.png)",
        "",
        "### Anno per anno (parametri del video, 4 MNQ)",
        tabella_md(per_anno(tr)),
        "",
        f"## 2. Le 10 varianti migliori negli anni < {ANNO_DIVISIONE}, e come sono andate dopo",
        "Se una variante è buona davvero, deve restare positiva anche negli anni che non ha \"visto\".",
        "",
        tabella_md(migliori_is[chiavi + ["trade_IS", "R_medio_IS", "t_stat_IS", "trade_OOS", "R_medio_OOS", "t_stat_OOS"]]),
        "",
        f"Varianti testate: {len(unite)}. Positive sia prima che dopo il {ANNO_DIVISIONE}: "
        f"{int(((unite['R_medio_IS'] > 0) & (unite['R_medio_OOS'] > 0)).sum())}. "
        f"Con t-stat > 2 in entrambi i periodi: {int(((unite['t_stat_IS'] > 2) & (unite['t_stat_OOS'] > 2)).sum())}.",
        "",
        "Tutte le varianti sono in `griglia_varianti.csv`, i singoli trade in `trade_parametri_video.csv`.",
    ]
    (OUT / "RISULTATI.md").write_text("\n".join(md))
    print(f"Scritto {OUT / 'RISULTATI.md'}")


if __name__ == "__main__":
    main()
