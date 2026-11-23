"""
Strategia "London High sweep" vista nel video TikTok (MNQ, 22/10/2026):

  1. Si segna il massimo (e il minimo) della sessione di Londra.
  2. All'apertura di New York il prezzo sale sopra il London High
     e fa scattare gli stop di chi era short ("presa di liquidità").
  3. Si va short su quella spinta, stop stretto sopra, target molto lontano
     (nel video: stop 20 punti, target ~187 punti, cioè circa 9R).
  4. Tutto si chiude a fine giornata se né stop né target vengono toccati.

Qui la regola è scritta in modo meccanico così si può testare su anni di dati.
Ogni scelta "a occhio" del video è diventata un parametro (vedi Parametri).

Convenzioni:
- prezzi in punti dell'indice/future Nasdaq-100 (1 punto MNQ = 2 $)
- orari in ora di New York (America/New_York), quindi l'ora legale è gestita
- dati a 1 minuto; se nello stesso minuto vengono toccati sia stop che target
  assumiamo SEMPRE lo stop (ipotesi pessimista, la più onesta senza tick)
"""

from dataclasses import dataclass, field, asdict
from datetime import time

import numpy as np
import pandas as pd

TICK = 0.25  # tick minimo del future NQ/MNQ


@dataclass
class Parametri:
    # Sessione di Londra in ora di New York (ICT "London killzone": 02:00-05:00)
    londra_inizio: time = time(2, 0)
    londra_fine: time = time(5, 0)
    # Finestra in cui si può ENTRARE (nel video l'entrata è alle 10:00 NY circa)
    entrata_inizio: time = time(9, 30)
    entrata_fine: time = time(11, 0)
    # Uscita forzata ("TIF: End of day" nel video)
    uscita_forzata: time = time(15, 55)

    # "limite": ordine limite piazzato in anticipo a London High + offset (come nel video)
    # "conferma": aspetta che il prezzo rompa il London High e poi richiuda sotto
    modalita: str = "limite"
    offset_punti: float = 10.0       # quanto sopra il London High sta l'ordine limite
    stop_punti: float = 20.0         # distanza dello stop dall'entrata (modalità limite)
    rr: float = 9.0                  # target = rr * rischio
    minuti_conferma: int = 30        # modalità conferma: tempo max per rientrare sotto il livello
    buffer_stop_conferma: float = 2.0  # modalità conferma: stop = massimo dello sweep + buffer

    lati: str = "short"              # "short" (come nel video), "long" (sweep del London Low), "entrambi"
    salta_se_gia_preso: bool = True  # se il livello è già stato rotto tra le 05:00 e l'entrata, niente trade
    costo_punti: float = 0.75        # commissioni + slippage per trade, in punti (~1,5 $ a contratto MNQ)


@dataclass
class Trade:
    giorno: object
    lato: str
    ora_entrata: object
    entrata: float
    stop: float
    target: float
    ora_uscita: object
    uscita: float
    motivo: str
    livello_londra: float
    punti: float = field(init=False)
    r: float = field(init=False)

    def __post_init__(self):
        segno = -1 if self.lato == "short" else 1
        rischio = abs(self.stop - self.entrata)
        self.punti = segno * (self.uscita - self.entrata)
        self.r = self.punti / rischio if rischio else 0.0


def prepara(df: pd.DataFrame) -> pd.DataFrame:
    """Da CSV con colonna 'time' in UTC a indice in ora di New York."""
    df = df.copy()
    df["time"] = pd.to_datetime(df["time"], utc=True).dt.tz_convert("America/New_York")
    df = df.set_index("time").sort_index()
    df = df[~df.index.duplicated()]
    return df[["open", "high", "low", "close"]]


def _gestisci_posizione(barre, i_start, lato, entrata, stop, target, p: Parametri):
    """Scorre le barre da i_start finché non tocca stop, target o l'orario di uscita."""
    ore = barre.index
    h, l, c = (barre[k].to_numpy() for k in ["high", "low", "close"])
    for j in range(i_start, len(barre)):
        if ore[j].time() >= p.uscita_forzata:
            return ore[j], barre["open"].iat[j], "fine giornata"
        if lato == "short":
            if h[j] >= stop:
                return ore[j], stop, "stop"
            if l[j] <= target:
                return ore[j], target, "target"
        else:
            if l[j] <= stop:
                return ore[j], stop, "stop"
            if h[j] >= target:
                return ore[j], target, "target"
    return ore[-1], c[-1], "fine dati"


def _trade_del_giorno(giorno, barre: pd.DataFrame, p: Parametri):
    t = barre.index.time
    londra = barre[(t >= p.londra_inizio) & (t < p.londra_fine)]
    if len(londra) < 60:  # sessione di Londra incompleta: salta il giorno
        return []
    lh, ll = londra["high"].max(), londra["low"].min()

    pre = barre[(t >= p.londra_fine) & (t < p.entrata_inizio)]
    sessione = barre[t >= p.entrata_inizio]
    if len(sessione) < 30:
        return []

    lati = ["short", "long"] if p.lati == "entrambi" else [p.lati]
    trades = []
    for lato in lati:
        livello = lh if lato == "short" else ll
        segno = 1 if lato == "short" else -1  # +1: il livello è sopra, -1: sotto
        if p.salta_se_gia_preso and len(pre):
            gia_preso = pre["high"].max() > livello if lato == "short" else pre["low"].min() < livello
            if gia_preso:
                continue
        tr = _entra(giorno, sessione, lato, livello, segno, p)
        if tr:
            trades.append(tr)
    # se nello stesso giorno scattano entrambi i lati teniamo solo il primo (un trade al giorno)
    trades.sort(key=lambda x: x.ora_entrata)
    return trades[:1]


def _entra(giorno, s: pd.DataFrame, lato, livello, segno, p: Parametri):
    ore = s.index
    o, h, l, c = (s[k].to_numpy() for k in ["open", "high", "low", "close"])
    n_finestra = int(np.searchsorted(np.array([x.time() for x in ore]), p.entrata_fine))
    # (l'array di orari è ordinato dentro la giornata, quindi searchsorted va bene)

    if p.modalita == "limite":
        prezzo = livello + segno * p.offset_punti
        for i in range(n_finestra):
            # l'ordine limite si considera eseguito solo se il prezzo lo SUPERA di un tick
            toccato = h[i] >= prezzo + TICK if lato == "short" else l[i] <= prezzo - TICK
            if not toccato:
                continue
            # se la barra apre già oltre il prezzo (gap), il limite viene eseguito all'apertura
            entrata = max(prezzo, o[i]) if lato == "short" else min(prezzo, o[i])
            stop = entrata + segno * p.stop_punti
            target = entrata - segno * p.rr * p.stop_punti
            # stessa barra dell'entrata: se ha toccato anche lo stop, pessimisticamente è stop
            colpito_stop = h[i] >= stop if lato == "short" else l[i] <= stop
            if colpito_stop:
                ora_u, uscita, motivo = ore[i], stop, "stop"
            else:
                ora_u, uscita, motivo = _gestisci_posizione(s, i + 1, lato, entrata, stop, target, p)
            return Trade(giorno, lato, ore[i], entrata, stop, target, ora_u, uscita, motivo, livello)
        return None

    if p.modalita == "conferma":
        estremo, i_sweep = None, None
        for i in range(n_finestra):
            oltre = h[i] > livello if lato == "short" else l[i] < livello
            if i_sweep is None:
                if oltre:
                    i_sweep, estremo = i, (h[i] if lato == "short" else l[i])
                else:
                    continue
            estremo = max(estremo, h[i]) if lato == "short" else min(estremo, l[i])
            if i - i_sweep > p.minuti_conferma:
                return None
            rientrato = c[i] < livello if lato == "short" else c[i] > livello
            if rientrato:
                entrata = c[i]
                stop = estremo + segno * p.buffer_stop_conferma
                rischio = abs(stop - entrata)
                target = entrata - segno * p.rr * rischio
                ora_u, uscita, motivo = _gestisci_posizione(s, i + 1, lato, entrata, stop, target, p)
                return Trade(giorno, lato, ore[i], entrata, stop, target, ora_u, uscita, motivo, livello)
        return None

    raise ValueError(f"modalità sconosciuta: {p.modalita}")


def esegui(df: pd.DataFrame, p: Parametri) -> pd.DataFrame:
    """Esegue il backtest su tutto il DataFrame (già passato da prepara())."""
    trades = []
    for giorno, barre in df.groupby(df.index.date):
        if pd.Timestamp(giorno).weekday() >= 5:
            continue
        trades += _trade_del_giorno(giorno, barre, p)
    out = pd.DataFrame([asdict(t) | {"punti": t.punti, "r": t.r} for t in trades])
    if len(out):
        rischio = (out["stop"] - out["entrata"]).abs()
        out["punti_netti"] = out["punti"] - p.costo_punti
        out["r_netto"] = out["punti_netti"] / rischio
    return out


def statistiche(tr: pd.DataFrame, giorni_totali: int | None = None) -> dict:
    if tr.empty:
        return {"trade": 0}
    r = tr["r_netto"]
    equity = r.cumsum()
    dd = (equity - equity.cummax()).min()
    perdite = (r <= 0).astype(int)
    serie = perdite.groupby((perdite != perdite.shift()).cumsum()).cumsum().max()
    vinti, persi = r[r > 0].sum(), -r[r <= 0].sum()
    st = {
        "trade": len(tr),
        "win_rate_%": round(100 * (r > 0).mean(), 1),
        "target_%": round(100 * (tr["motivo"] == "target").mean(), 1),
        "R_medio": round(r.mean(), 3),
        "R_totale": round(r.sum(), 1),
        "profit_factor": round(vinti / persi, 2) if persi else np.inf,
        "max_drawdown_R": round(dd, 1),
        "max_perdite_di_fila": int(serie),
        "punti_totali": round(tr["punti_netti"].sum(), 1),
    }
    if giorni_totali:
        st["trade_%_giorni"] = round(100 * len(tr) / giorni_totali, 1)
    # t-statistic dell'R medio: sotto ~2 il risultato non si distingue dal caso
    st["t_stat"] = round(r.mean() / (r.std(ddof=1) / np.sqrt(len(r))), 2) if len(r) > 2 else np.nan
    return st
