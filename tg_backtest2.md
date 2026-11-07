# Backtest dei segnali del canale Telegram @BINANCE_CRYPTO_SIGNALS_ML (Binance futures, candele da 1 minuto): verifica fuori campione (dal 31 ottobre, tenuta massima 24 ore)

Pre-registrazione (testo originale):

```
(written before looking at any result):
  * a signal = a post with LONG/SHORT, a USDT pair, Entry, TP1 and TP2 (Stop when written); the pair must be a
    Binance USDT-M perpetual; signals whose 7 days after the post are not fully in the archive are left out;
  * entry: (M) at the open of the first minute after the post, plus 0.02% slippage; (L) a limit order at the
    written Entry, valid 60 minutes, filled at the first minute that touches it (at that minute's open if better);
  * exits, all closed after 7 days at the latest:
      V1 as written: half at TP1, half at TP2, stop as written (posts without a stop: -3%, the channel's own earlier
         default);
      V2 V1 plus the stop moved to the entry after TP1 (the channel's later instruction);
      V3 no stop before TP1, half at TP1, then the rest with the stop at the entry, otherwise held to 7 days;
      V4 everything at TP1 with the V1 stop (the "TP1 hit = win" reading);
    when one minute touches both a stop and a target, the stop counts first (conservative; the count is reported);
  * costs: 0.05% taker fee per side and 0.02% slippage on market fills (entry M and stops); funding not counted
    (the average holding time is reported);
  * comparison: the same pairs, sides and exits with the entry at a random minute in the 3 days BEFORE the post
    (seed 7; before, so that the 7-day hold fits in the downloaded candles):
    does the timing of the signal add anything over chance?
  * results per trade (no leverage): mean, 95% bootstrap interval, median, winners, profit factor, how trades end;
    by period (with / without a written stop), side, month and score; leverage multiplies both gains and losses
    (and without a stop a -10% move wipes out a 10x position).
```
Messaggi visibili: 2,975 (id da 1 a 5013, mancanti 2,038); segnali riconosciuti: **2,927** (1,721 LONG, 1,206 SHORT; con stop scritto 1,320, senza 1,607); coppie diverse: 239.

## Numeri di messaggio mancanti per settimana (cancellati o non pubblici)
| week | visibili | mancanti_prima |
|---|---|---|
| 2026-W37 | 1 | 0 |
| 2026-W41 | 343 | 2038 |
| 2026-W42 | 817 | 0 |
| 2026-W43 | 827 | 0 |
| 2026-W44 | 523 | 0 |
| 2026-W45 | 464 | 0 |

Segnali su coppie che esistono come perpetui USDT-M su Binance: 2,927 su 2,927 (non trovate: nessuna).
Solo i segnali dal 2026-10-31: 586; tenuta massima 24 ore.

Segnali con 7 giorni completi di candele: **493** (dal 2026-10-31 al 2026-11-05). Scarto mediano tra il prezzo d'entrata scritto e il primo minuto dopo il messaggio: +0.012% (in valore assoluto 0.919%).

## Risultato per operazione (senza leva, commissioni comprese)
| regole | entrata | n | media_% | IC95_basso_% | IC95_alto_% | mediana_% | vincenti_% | vincita_media_% | perdita_media_% | profit_factor | somma_% | minuti_medi | minuti_ambigui |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V1 come scritto (metà TP1, metà TP2, stop scritto o -3%) | a mercato subito | 493 | -0.4864 | -0.8648 | -0.1769 | 0.3096 | 59.84 | 1.085 | -2.828 | 0.5717 | -239.8 | 257 | 0 |
| V1 come scritto (metà TP1, metà TP2, stop scritto o -3%) | limite al prezzo scritto | 372 | -0.2242 | -0.8149 | 0.2878 | 1.401 | 82.8 | 1.554 | -8.783 | 0.8517 | -83.39 | 390.9 | 0 |
| V1 come scritto (metà TP1, metà TP2, stop scritto o -3%) | a un minuto CASUALE nei 3 giorni prima (confronto) | 493 | -0.4713 | -0.6083 | -0.3371 | -0.2829 | 44.22 | 0.9582 | -1.605 | 0.4734 | -232.4 |  |  |
| V2 V1 + stop all'entrata dopo TP1 | a mercato subito | 493 | -0.5155 | -0.8534 | -0.2236 | -0.0852 | 45.84 | 0.9473 | -1.754 | 0.4572 | -254.2 | 132.9 | 102 |
| V2 V1 + stop all'entrata dopo TP1 | limite al prezzo scritto | 372 | -0.2416 | -0.7687 | 0.2344 | 0.5049 | 87.63 | 1.035 | -9.291 | 0.7897 | -89.88 | 226.9 | 29 |
| V2 V1 + stop all'entrata dopo TP1 | a un minuto CASUALE nei 3 giorni prima (confronto) | 493 | -0.4761 | -0.599 | -0.3487 | -0.2133 | 35.9 | 0.8611 | -1.225 | 0.3937 | -234.7 |  |  |
| V3 senza stop prima di TP1, poi stop all'entrata, max 7 giorni | a mercato subito | 493 | -0.5155 | -0.8352 | -0.2266 | -0.0852 | 45.84 | 0.9473 | -1.754 | 0.4572 | -254.2 | 132.9 | 102 |
| V3 senza stop prima di TP1, poi stop all'entrata, max 7 giorni | limite al prezzo scritto | 372 | -0.2416 | -0.7818 | 0.2303 | 0.5049 | 87.63 | 1.035 | -9.291 | 0.7897 | -89.88 | 226.9 | 29 |
| V3 senza stop prima di TP1, poi stop all'entrata, max 7 giorni | a un minuto CASUALE nei 3 giorni prima (confronto) | 493 | -0.7639 | -1.254 | -0.3474 | -0.1027 | 44.42 | 0.9527 | -2.136 | 0.3565 | -376.6 |  |  |
| V4 tutto a TP1 con lo stop di V1 | a mercato subito | 493 | -0.654 | -0.9853 | -0.3819 | -0.113 | 44.83 | 0.939 | -1.948 | 0.3916 | -322.4 | 126.5 | 0 |
| V4 tutto a TP1 con lo stop di V1 | limite al prezzo scritto | 372 | -0.1811 | -0.7253 | 0.2865 | 0.9012 | 90.32 | 1.057 | -11.74 | 0.8406 | -67.38 | 215.9 | 0 |
| V4 tutto a TP1 con lo stop di V1 | a un minuto CASUALE nei 3 giorni prima (confronto) | 493 | -0.6276 | -0.7606 | -0.4936 | -0.2637 | 36.51 | 0.802 | -1.45 | 0.3181 | -309.4 |  |  |


## Come finiscono le operazioni (entrata a mercato)
| index | V1 | V2 | V3 | V4 |
|---|---|---|---|---|
| TP2 | 88.64 | 51.72 | 51.72 | 0 |
| tempo scaduto | 11.36 | 5.882 | 5.882 | 5.882 |
| stop dopo TP1 | 0 | 42.39 | 42.39 | 0 |
| TP1 | 0 | 0 | 0 | 94.12 |


## Per periodo, direzione, mese e punteggio (V1 e V3, entrata a mercato)
| periodo | V1_n | V1_media_% | V1_IC95_basso_% | V1_IC95_alto_% | V1_vincenti_% | V3_media_% | V3_vincenti_% |
|---|---|---|---|---|---|---|---|
| senza stop scritto | 493 | -0.4864 | -0.8551 | -0.1756 | 59.84 | -0.5155 | 45.84 |

| side | V1_n | V1_media_% | V1_IC95_basso_% | V1_IC95_alto_% | V1_vincenti_% | V3_media_% | V3_vincenti_% |
|---|---|---|---|---|---|---|---|
| LONG | 261 | -0.7643 | -1.392 | -0.2804 | 55.17 | -0.7441 | 45.59 |
| SHORT | 232 | -0.1738 | -0.6079 | 0.1842 | 65.09 | -0.2584 | 46.12 |

| mese | n | media_% | vincenti_% | somma_% |
|---|---|---|---|---|
| 2026-10 | 58 | -0.2707 | 58.62 | -15.7 |
| 2026-11 | 435 | -0.5152 | 60 | -224.1 |


## Con la leva
- 5x: risultato medio per operazione sul margine -2.4%; con V3 (senza stop) una mossa contraria del 20% azzera la posizione.
- 10x: risultato medio per operazione sul margine -4.9%; con V3 (senza stop) una mossa contraria del 10% azzera la posizione.
- 20x: risultato medio per operazione sul margine -9.7%; con V3 (senza stop) una mossa contraria del 5% azzera la posizione.
