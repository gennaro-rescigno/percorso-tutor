"""
Scarica le candele a 1 minuto dell'indice Nasdaq-100 (CFD "USATECHIDXUSD")
dal feed storico gratuito di Dukascopy e le salva in Parquet (orari UTC),
un file per anno: dati/USATECHIDXUSD_1m_<anno>.parquet

Perché non il future NQ? Lo storico intraday gratuito dei future non esiste;
il CFD sull'indice si muove in modo quasi identico al future durante la
giornata (cambia solo la differenza fissa tra future e indice, che a noi non
interessa: la strategia ragiona su livelli della stessa serie).

Teniamo solo le ore 04:00-21:00 UTC (= da mezzanotte a fine sessione di New York),
così i file restano piccoli.

Uso:
    python scarica_dati.py 2024          # un anno
    python scarica_dati.py 2016 2026     # più anni
"""

import lzma
import struct
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

SIMBOLO = "USATECHIDXUSD"
URL = "https://datafeed.dukascopy.com/datafeed/{sym}/{y}/{m:02d}/{d:02d}/BID_candles_min_1.bi5"
DIVISORE_PREZZO = 1000  # Dukascopy salva i prezzi degli indici come interi * 1000
CARTELLA = Path(__file__).parent / "dati"
ORA_UTC_DA, ORA_UTC_A = 4, 21


def scarica_giorno(giorno: date, sessione: requests.Session) -> pd.DataFrame | None:
    """Scarica un giorno (UTC). Restituisce None se il giorno è vuoto (festivo)."""
    # Attenzione: nell'URL di Dukascopy i mesi partono da 0 (gennaio = 00)
    url = URL.format(sym=SIMBOLO, y=giorno.year, m=giorno.month - 1, d=giorno.day)
    attesa = 5
    for _ in range(10):
        try:
            r = sessione.get(url, timeout=30)
        except requests.RequestException:
            time.sleep(attesa)
            attesa = min(attesa * 2, 120)
            continue
        if r.status_code == 200:
            break
        if r.status_code == 404:
            return None
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(attesa)  # il server ci chiede di rallentare
            attesa = min(attesa * 2, 120)
            continue
        r.raise_for_status()
    else:
        raise RuntimeError(f"Troppi tentativi falliti per {giorno}")

    if not r.content:
        return None
    grezzo = lzma.decompress(r.content)
    # Ogni candela = 24 byte: secondi dall'inizio del giorno, open, close, low, high, volume
    righe = list(struct.iter_unpack(">5if", grezzo))
    df = pd.DataFrame(righe, columns=["sec", "open", "close", "low", "high", "volume"])
    inizio = pd.Timestamp(datetime(giorno.year, giorno.month, giorno.day, tzinfo=timezone.utc))
    df["time"] = inizio + pd.to_timedelta(df["sec"], unit="s")
    for col in ["open", "high", "low", "close"]:
        df[col] = (df[col] / DIVISORE_PREZZO).astype("float32")
    # Dukascopy riempie i minuti senza scambi con candele piatte a volume 0: le togliamo
    df = df[(df["volume"] > 0) & df["time"].dt.hour.between(ORA_UTC_DA, ORA_UTC_A - 1)]
    df = df[["time", "open", "high", "low", "close", "volume"]].astype({"volume": "float32"})
    return df if len(df) else None


def scarica_anno(anno: int) -> Path:
    CARTELLA.mkdir(parents=True, exist_ok=True)
    g = date(anno, 1, 1)
    fine = min(date(anno, 12, 31), date.today() - timedelta(days=1))
    sessione = requests.Session()
    sessione.headers["User-Agent"] = "percorso-tutor-backtest/1.0 (python-requests)"
    pezzi = []
    while g <= fine:
        if g.weekday() < 5:  # niente weekend
            df = scarica_giorno(g, sessione)
            if df is not None:
                pezzi.append(df)
            print(g, "vuoto" if df is None else f"{len(df)} candele", flush=True)
            time.sleep(0.3)  # gentilezza verso il server
        g += timedelta(days=1)
    out = CARTELLA / f"{SIMBOLO}_1m_{anno}.parquet"
    pd.concat(pezzi).to_parquet(out, index=False, compression="zstd")
    print(f"Salvato {out}")
    return out


def carica(cartella: Path = CARTELLA) -> pd.DataFrame:
    """Legge tutti i file annuali e li restituisce in un unico DataFrame."""
    file = sorted(cartella.glob(f"{SIMBOLO}_1m_*.parquet"))
    if not file:
        raise FileNotFoundError(f"Nessun dato in {cartella}: lancia prima scarica_dati.py")
    return pd.concat(pd.read_parquet(f) for f in file).sort_values("time")


if __name__ == "__main__":
    anni = [int(a) for a in sys.argv[1:]]
    for a in range(anni[0], anni[-1] + 1):
        scarica_anno(a)
