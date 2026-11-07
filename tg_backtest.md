# Backtest dei segnali del canale Telegram @BINANCE_CRYPTO_SIGNALS_ML (Binance futures, candele da 1 minuto)

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

Segnali con 7 giorni completi di candele: **1,624** (dal 2026-10-09 al 2026-10-30). Scarto mediano tra il prezzo d'entrata scritto e il primo minuto dopo il messaggio: +0.000% (in valore assoluto 0.696%).

## Risultato per operazione (senza leva, commissioni comprese)
| regole | entrata | n | media_% | IC95_basso_% | IC95_alto_% | mediana_% | vincenti_% | vincita_media_% | perdita_media_% | profit_factor | somma_% | minuti_medi | minuti_ambigui |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V1 come scritto (metà TP1, metà TP2, stop scritto o -3%) | a mercato subito | 1624 | -0.2104 | -0.3331 | -0.09597 | 0.2192 | 53.76 | 1.142 | -1.783 | 0.7448 | -341.6 | 331.4 | 4 |
| V1 come scritto (metà TP1, metà TP2, stop scritto o -3%) | limite al prezzo scritto | 1370 | 0.0859 | -0.06541 | 0.2274 | 1.399 | 62.04 | 1.552 | -2.311 | 1.098 | 117.7 | 425.8 | 9 |
| V1 come scritto (metà TP1, metà TP2, stop scritto o -3%) | a un minuto CASUALE nei 3 giorni prima (confronto) | 1560 | -0.3595 | -0.4455 | -0.2773 | -0.14 | 47.05 | 1.138 | -1.691 | 0.5984 | -560.9 |  |  |
| V2 V1 + stop all'entrata dopo TP1 | a mercato subito | 1624 | -0.1719 | -0.2766 | -0.0823 | -0.07381 | 47.97 | 0.9875 | -1.241 | 0.7338 | -279.1 | 139.5 | 282 |
| V2 V1 + stop all'entrata dopo TP1 | limite al prezzo scritto | 1370 | 0.1254 | -0.02662 | 0.2473 | 0.4218 | 73.58 | 1.086 | -2.548 | 1.186 | 171.8 | 222.6 | 48 |
| V2 V1 + stop all'entrata dopo TP1 | a un minuto CASUALE nei 3 giorni prima (confronto) | 1560 | -0.3435 | -0.4192 | -0.2655 | -0.14 | 43.08 | 0.9855 | -1.349 | 0.5527 | -535.9 |  |  |
| V3 senza stop prima di TP1, poi stop all'entrata, max 7 giorni | a mercato subito | 1624 | -0.3559 | -0.6204 | -0.09837 | 0.3597 | 61.82 | 1.246 | -2.95 | 0.6839 | -578 | 709.3 | 290 |
| V3 senza stop prima di TP1, poi stop all'entrata, max 7 giorni | limite al prezzo scritto | 1370 | -0.1352 | -0.485 | 0.1766 | 1.399 | 93.14 | 1.279 | -19.33 | 0.8981 | -185.2 | 1007 | 50 |
| V3 senza stop prima di TP1, poi stop all'entrata, max 7 giorni | a un minuto CASUALE nei 3 giorni prima (confronto) | 1560 | -0.4715 | -0.8332 | -0.1528 | 0.3808 | 62.24 | 1.311 | -3.411 | 0.6339 | -735.6 |  |  |
| V4 tutto a TP1 con lo stop di V1 | a mercato subito | 1624 | -0.2613 | -0.3697 | -0.1658 | -0.04376 | 48.34 | 0.9406 | -1.386 | 0.6351 | -424.3 | 127.5 | 2 |
| V4 tutto a TP1 con lo stop di V1 | limite al prezzo scritto | 1370 | 0.1204 | -0.02007 | 0.2417 | 0.9001 | 73.94 | 1.073 | -2.582 | 1.179 | 165 | 204.9 | 9 |
| V4 tutto a TP1 con lo stop di V1 | a un minuto CASUALE nei 3 giorni prima (confronto) | 1560 | -0.4456 | -0.5272 | -0.3649 | -0.14 | 43.46 | 0.9208 | -1.496 | 0.4732 | -695.1 |  |  |


## Come finiscono le operazioni (entrata a mercato)
| index | V1 | V2 | V3 | V4 |
|---|---|---|---|---|
| TP2 | 70.81 | 42.12 | 51.42 | 0 |
| stop | 18.17 | 18.17 | 0 | 18.17 |
| stop dopo TP1 | 9.544 | 39.47 | 44.33 | 0 |
| tempo scaduto | 1.478 | 0.2463 | 4.249 | 0.2463 |
| TP1 | 0 | 0 | 0 | 81.59 |


## Per periodo, direzione, mese e punteggio (V1 e V3, entrata a mercato)
| periodo | V1_n | V1_media_% | V1_IC95_basso_% | V1_IC95_alto_% | V1_vincenti_% | V3_media_% | V3_vincenti_% |
|---|---|---|---|---|---|---|---|
| con stop scritto | 1320 | -0.211 | -0.3049 | -0.117 | 50.53 | -0.4507 | 63.79 |
| senza stop scritto | 304 | -0.2076 | -0.7281 | 0.2329 | 67.76 | 0.05568 | 53.29 |

| side | V1_n | V1_media_% | V1_IC95_basso_% | V1_IC95_alto_% | V1_vincenti_% | V3_media_% | V3_vincenti_% |
|---|---|---|---|---|---|---|---|
| LONG | 980 | -0.2667 | -0.4447 | -0.1138 | 52.96 | -0.5611 | 61.43 |
| SHORT | 644 | -0.1246 | -0.2739 | 0.01315 | 54.97 | -0.04366 | 62.42 |

| mese | n | media_% | vincenti_% | somma_% |
|---|---|---|---|---|
| 2026-10 | 1624 | -0.2104 | 53.76 | -341.6 |

| punteggio | n | media_% | vincenti_% |
|---|---|---|---|
| <= 70 | 839 | -0.189 | 51.73 |
| 71-72 | 394 | -0.3115 | 46.95 |
| 73-75 | 81 | 0.03236 | 55.56 |
| > 75 | 6 | 0.02891 | 50 |


## Con la leva
- 5x: risultato medio per operazione sul margine -1.1%; con V3 (senza stop) una mossa contraria del 20% azzera la posizione.
- 10x: risultato medio per operazione sul margine -2.1%; con V3 (senza stop) una mossa contraria del 10% azzera la posizione.
- 20x: risultato medio per operazione sul margine -4.2%; con V3 (senza stop) una mossa contraria del 5% azzera la posizione.
