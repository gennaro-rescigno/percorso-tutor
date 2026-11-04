# I progetti (link social, descrizione) predicono il diploma? (pump.fun, 8 maggio - 10 giugno 2026)

Data: AratiKamat/red-pump-2026 (CC BY 4.0): 860,213 launches with the metadata known at creation (X / website /
Telegram link present, description length, initial market cap) and a collector-recorded label (bonding curve
filled within 24 hours or not). It answers "evaluate the projects" with data that exist at the moment of the
decision. Limit: there are no prices, so it measures the probability of a graduation, not a profit (section 9.2
showed that the curve price already reflects that probability).

PRE-REGISTERED (written before looking at any result): days split by creation time: May 8-31 (model fitted) and
June 1-10 (measured); graduation rate by link presence, description length (0, 1-50, 51-200, > 200 characters) and
initial market cap tercile; AUC of each signal and of a logistic regression on all of them (fitted on May, measured
on June), with a 95% interval; lift of the model's top 10% over the base rate.
Lanci: 860,194; esiti leggibili: 833,079 (righe senza esito o mint riconoscibili: 100).
Con esito: 833,079 (maggio 602,279, giugno 230,800); diplomati: 0.20% (maggio 0.18%, giugno 0.23%).

## Tasso di diploma per caratteristica del progetto (giugno, mai usato per adattare nulla)
| caratteristica | valore | lanci | diplomati_% |
|---|---|---|---|
| link X | 0 | 92167 | 0.1823 |
| link X | 1 | 138633 | 0.2698 |
| sito | 0 | 148641 | 0.1823 |
| sito | 1 | 82159 | 0.3298 |
| Telegram | 0 | 225130 | 0.1977 |
| Telegram | 1 | 5670 | 1.711 |
| numero di link | 0 | 83098 | 0.1673 |
| numero di link | 1 | 72660 | 0.2188 |
| numero di link | 2 | 71324 | 0.2089 |
| numero di link | 3 | 3718 | 2.555 |
| lunghezza della descrizione | 0 | 113847 | 0.1651 |
| lunghezza della descrizione | 1-50 | 88090 | 0.1805 |
| lunghezza della descrizione | 51-200 | 18174 | 0.8694 |
| lunghezza della descrizione | > 200 | 10689 | 0.3462 |
| capitalizzazione iniziale (terzile di maggio) | 1 | 59701 | 0.08543 |
| capitalizzazione iniziale (terzile di maggio) | 2 | 94753 | 0.08549 |
| capitalizzazione iniziale (terzile di maggio) | 3 | 76346 | 0.537 |


## Capacità di previsione (AUC su giugno; 0,5 = nessuna informazione)
| segnale | AUC | IC95 |
|---|---|---|
| tw | 0.5448 | [0.520, 0.570] |
| web | 0.5722 | [0.547, 0.597] |
| tg | 0.5774 | [0.552, 0.603] |
| links | 0.6001 | [0.575, 0.625] |
| desc | 0.6218 | [0.596, 0.647] |
| mcap0 | 0.8051 | [0.783, 0.827] |
| regressione logistica su tutti | 0.7342 | [0.710, 0.758] |

Il 10% dei lanci con la previsione più alta si diploma nel **1.30%** dei casi, contro il 0.23% di tutti (x5.6).
