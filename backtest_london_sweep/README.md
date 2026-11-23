# Backtest: "London High sweep" sul Nasdaq

Replica meccanica della strategia vista in un video TikTok (@usynq, trade short su MNQ del 22/10/2026)
e test su circa 10 anni di dati a 1 minuto.

## La strategia, tradotta in regole

| Cosa | Nel video | Nel codice (`Parametri` in `strategia.py`) |
|---|---|---|
| Livello | London High segnato con l'indicatore "ICT Essentials" | massimo 02:00-05:00 ora di New York |
| Quando | ~10:00 NY, dopo l'apertura | entrata solo tra 9:30 e 11:00 NY |
| Entrata | ordine limite short a 29.586, poco sopra il London High | limite a London High + 10 punti (`offset_punti`) |
| Stop | 29.606 → 20 punti | `stop_punti = 20` |
| Target | 29.398,5 → ~187 punti (~9R) | `rr = 9` |
| Uscita | "TIF: End of day" | chiusura forzata alle 15:55 |
| Size | 4 MNQ (2 $ a punto) | i risultati sono in R e punti; 1R = 20 pt = 160 $ con 4 MNQ |

In più: se il London High era già stato rotto prima delle 9:30, quel giorno non si opera
(la liquidità è già stata presa). C'è anche una modalità `conferma` (si aspetta che il prezzo
rompa il livello e richiuda sotto prima di entrare) e il lato `long` simmetrico (sweep del London Low).

Ipotesi prudenti: l'ordine limite è eseguito solo se il prezzo supera il livello di 1 tick;
se nello stesso minuto si toccano stop e target vale lo stop; 0,75 punti di costi a trade.

## Dati

Il CFD sull'indice Nasdaq-100 di Dukascopy (`USATECHIDXUSD`), a 1 minuto, gratuito. Non è il future NQ,
ma durante la giornata si muove allo stesso modo: la strategia usa solo livelli della stessa serie,
quindi la differenza fissa tra future e indice non conta.

Il feed non è raggiungibile dall'ambiente cloud di Claude, quindi lo scarica il workflow
`.github/workflows/london-sweep-data.yml` (parte da solo a ogni modifica di `scarica_dati.py`)
e committa i file in `dati/`. In locale: `python scarica_dati.py 2016 2026`.

## Come si lancia

```bash
pip install pandas pyarrow matplotlib requests
python backtest.py
```

Risultati in `risultati/RISULTATI.md`.

## File

- `strategia.py`: le regole e il motore di backtest
- `scarica_dati.py`: download dei dati
- `backtest.py`: parametri del video, confronto con entrate casuali, griglia di varianti, divisione in-sample/out-of-sample
