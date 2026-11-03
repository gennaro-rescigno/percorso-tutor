# Studio storico: dove finisce il vantaggio dei wallet migliori (jocry, giu-lug 2026)

Pre-registrazione (testo originale):

```
variants (each also run on the random control group with the same rule):
  V0 perfect copy (delay 0: the wallet's own entry and first-sale prices): NOT feasible, measures what the delay costs;
  V1 delay 1 s, exit 1 s after the wallet's first sale (needs fast infrastructure, not ours: an upper bound);
  V2 slow leaders: leaders as before but with <= 10% of positions held under 60 s and <= 30% under 5 minutes;
     delay 3 s, exit 3 s after their first sale;
  V3 fixed exit: delay 3 s, exit 120 s after the entry whatever the wallet does;
  V4 consensus: only tokens bought by >= 2 leaders within 10 minutes; entry 3 s after the second buy, exit 3 s
     after the first sale of either, at the latest 60 minutes after the entry.
Costs, prices, statistics and verdict as in jocry_copy (fee 1.25% + 0.5% impact per side, 1% priority fees).
```
Operazioni nel corpus: 33,581,765; usabili dopo la pulizia documentata: 23,396,637 (69.7%).
| variante | gruppo | copie | giorni | media_% | IC95_basso_% | IC95_alto_% | p | mediana_% | vincenti_% | 1a_metà_% | 2a_metà_% | q_BH | verdetto |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V0 copia perfetta (impossibile) | controllo | 7618 | 34 | -6.014 | -7.065 | -4.953 | 1 | -8.865 | 29.3 | -6.468 | -5.597 | 1 | controllo |
| V0 copia perfetta (impossibile) | migliori | 4163 | 34 | 9.052 | 7.414 | 10.73 | 0.0005 | -2.309 | 45.54 | 10.12 | 8.482 | 0.0045 | positiva, stabile e sopra il controllo |
| V1 ritardo 1 s | controllo | 7618 | 34 | -8.568 | -9.625 | -7.507 | 1 | -11.33 | 25.95 | -9.538 | -7.678 | 1 | controllo |
| V1 ritardo 1 s | migliori | 4163 | 34 | -5.396 | -6.724 | -3.962 | 1 | -13.02 | 28.66 | -4.18 | -6.046 | 1 | non dimostrata |
| V2 wallet lenti, 3 s | migliori | 300 | 17 | -5.379 | -12.47 | 2.027 | 0.922 | -13.3 | 34 | -10.09 | -4.715 | 1 | non dimostrata |
| V3 uscita fissa a 120 s | controllo | 7618 | 34 | -8.363 | -9.43 | -7.151 | 1 | -7.422 | 29.71 | -9.347 | -7.459 | 1 | controllo |
| V3 uscita fissa a 120 s | migliori | 4163 | 34 | -4.181 | -5.491 | -2.904 | 1 | -8.18 | 35.91 | -3.413 | -4.591 | 1 | non dimostrata |
| V4 consenso di 2 wallet | controllo | 1040 | 33 | -11.76 | -13.2 | -10.29 | 1 | -4.457 | 10.96 | -14.24 | -10.02 | 1 | controllo |
| V4 consenso di 2 wallet | migliori | 1553 | 34 | -10.48 | -11.93 | -9.074 | 1 | -4.668 | 14.36 | -12.64 | -9.385 | 1 | non dimostrata |

