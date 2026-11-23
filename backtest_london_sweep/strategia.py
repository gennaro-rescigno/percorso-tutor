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

    # se True, stop_punti e offset_punti sono "punti al livello del video" (Nasdaq a 29.586) e vengono
    # scalati col prezzo del giorno: con il Nasdaq a 15.000, 20 punti diventano ~10
    scala_col_prezzo: bool = False
    prezzo_video: float = 29586.0

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


@dataclass
class Giorno:
    """Le candele di un giorno già pronte come array numpy (molto più veloci di pandas nei cicli)."""
    data: object
    ore: pd.DatetimeIndex
    minuto: np.ndarray  # minuti dalla mezzanotte di New York (es. 9:30 -> 570)
    o: np.ndarray
    h: np.ndarray
    l: np.ndarray
    c: np.ndarray


def _m(t: time) -> int:
    return t.hour * 60 + t.minute


def prepara(df: pd.DataFrame) -> list[Giorno]:
    """Da DataFrame con colonna 'time' in UTC a lista di giorni in ora di New York."""
    df = df.copy()
    df["time"] = pd.to_datetime(df["time"], utc=True).dt.tz_convert("America/New_York")
    df = df.set_index("time").sort_index()
    df = df[~df.index.duplicated()]
    giorni = []
    for data, b in df.groupby(df.index.date):
        if pd.Timestamp(data).weekday() >= 5:
            continue
        giorni.append(Giorno(data, b.index, (b.index.hour * 60 + b.index.minute).to_numpy(),
                             *(b[k].to_numpy(dtype="float64") for k in ["open", "high", "low", "close"])))
    return giorni


def _gestisci_posizione(g: Giorno, i_start, lato, stop, target, p: Parametri):
    """Dalla barra i_start cerca il primo tocco di stop o target, altrimenti esce all'orario forzato."""
    fine = int(np.searchsorted(g.minuto, _m(p.uscita_forzata)))
    if i_start >= fine:
        j = min(fine, len(g.c) - 1)
        return g.ore[j], g.o[j], "fine giornata"
    h, l = g.h[i_start:fine], g.l[i_start:fine]
    if lato == "short":
        colpo_stop, colpo_target = h >= stop, l <= target
    else:
        colpo_stop, colpo_target = l <= stop, h >= target
    i_s = int(np.argmax(colpo_stop)) if colpo_stop.any() else None
    i_t = int(np.argmax(colpo_target)) if colpo_target.any() else None
    # a parità di minuto vince lo stop (ipotesi pessimista)
    if i_s is not None and (i_t is None or i_s <= i_t):
        return g.ore[i_start + i_s], stop, "stop"
    if i_t is not None:
        return g.ore[i_start + i_t], target, "target"
    if fine < len(g.c):
        return g.ore[fine], g.o[fine], "fine giornata"
    return g.ore[-1], g.c[-1], "fine dati"


def _trade_del_giorno(g: Giorno, p: Parametri):
    m = g.minuto
    londra = (m >= _m(p.londra_inizio)) & (m < _m(p.londra_fine))
    if londra.sum() < 60:  # sessione di Londra incompleta: salta il giorno
        return []
    lh, ll = g.h[londra].max(), g.l[londra].min()
    pre = (m >= _m(p.londra_fine)) & (m < _m(p.entrata_inizio))
    i0 = int(np.searchsorted(m, _m(p.entrata_inizio)))
    i1 = int(np.searchsorted(m, _m(p.entrata_fine)))
    if i1 - i0 < 30:
        return []

    lati = ["short", "long"] if p.lati == "entrambi" else [p.lati]
    trades = []
    for lato in lati:
        livello = lh if lato == "short" else ll
        if p.salta_se_gia_preso and pre.any():
            gia_preso = g.h[pre].max() > livello if lato == "short" else g.l[pre].min() < livello
            if gia_preso:
                continue
        tr = _entra(g, i0, i1, lato, livello, p)
        if tr:
            trades.append(tr)
    # se nello stesso giorno scattano entrambi i lati teniamo solo il primo (un trade al giorno)
    trades.sort(key=lambda x: x.ora_entrata)
    return trades[:1]


def _entra(g: Giorno, i0, i1, lato, livello, p: Parametri):
    segno = 1 if lato == "short" else -1  # +1: il livello è sopra il prezzo, -1: sotto
    o, h, l, c = g.o, g.h, g.l, g.c

    if p.modalita == "limite":
        k = livello / p.prezzo_video if p.scala_col_prezzo else 1.0
        stop_punti = p.stop_punti * k
        prezzo = livello + segno * p.offset_punti * k
        # l'ordine limite si considera eseguito solo se il prezzo lo SUPERA di un tick
        toccato = h[i0:i1] >= prezzo + TICK if lato == "short" else l[i0:i1] <= prezzo - TICK
        if not toccato.any():
            return None
        i = i0 + int(np.argmax(toccato))
        # se la barra apre già oltre il prezzo (gap), il limite viene eseguito all'apertura
        entrata = max(prezzo, o[i]) if lato == "short" else min(prezzo, o[i])
        stop = entrata + segno * stop_punti
        target = entrata - segno * p.rr * stop_punti
        # stessa barra dell'entrata: se ha toccato anche lo stop, pessimisticamente è stop
        if (h[i] >= stop) if lato == "short" else (l[i] <= stop):
            ora_u, uscita, motivo = g.ore[i], stop, "stop"
        else:
            ora_u, uscita, motivo = _gestisci_posizione(g, i + 1, lato, stop, target, p)
        return Trade(g.data, lato, g.ore[i], entrata, stop, target, ora_u, uscita, motivo, livello)

    if p.modalita == "conferma":
        oltre = h[i0:i1] > livello if lato == "short" else l[i0:i1] < livello
        if not oltre.any():
            return None
        i_sweep = i0 + int(np.argmax(oltre))
        estremo = h[i_sweep] if lato == "short" else l[i_sweep]
        for i in range(i_sweep, min(i1, i_sweep + p.minuti_conferma + 1)):
            estremo = max(estremo, h[i]) if lato == "short" else min(estremo, l[i])
            rientrato = c[i] < livello if lato == "short" else c[i] > livello
            if rientrato:
                entrata = c[i]
                stop = estremo + segno * p.buffer_stop_conferma
                target = entrata - segno * p.rr * abs(stop - entrata)
                ora_u, uscita, motivo = _gestisci_posizione(g, i + 1, lato, stop, target, p)
                return Trade(g.data, lato, g.ore[i], entrata, stop, target, ora_u, uscita, motivo, livello)
        return None

    raise ValueError(f"modalità sconosciuta: {p.modalita}")


def esegui(giorni: list[Giorno], p: Parametri) -> pd.DataFrame:
    """Esegue il backtest su tutti i giorni (output di prepara())."""
    trades = []
    for g in giorni:
        trades += _trade_del_giorno(g, p)
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
    dev = r.std(ddof=1) if len(r) > 2 else 0
    st["t_stat"] = round(r.mean() / (dev / np.sqrt(len(r))), 2) if dev > 0 else np.nan
    return st
