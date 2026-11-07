# La tua regola sui segnali di @BINANCE_CRYPTO_SIGNALS_ML: stop oltre l'ultima candela opposta, obiettivo 1:1

Pre-registrazione (testo originale):

```
(written before looking at any result):
  * signals: every LONG/SHORT post of the channel on a Binance USDT-M perpetual (Oct 9 - Nov 6 2026), 1-minute candles
    (data.binance.vision); a signal needs candles from 60 minutes before the post to 24 hours after;
  * the impulse and the stop, from the candles BEFORE the post only (what was visible when the signal arrived):
      LONG: the impulse starts at the lowest low of the last K minutes; the stop is the low of the last red candle
      (close < open) at or before that minute (the lowest low itself if there is no red candle);
      SHORT: mirror - highest high of the last K minutes, high of the last green candle at or before it;
    K = 30 minutes (main), 15 and 60 (checks);
  * entry: (M) market at the open of the first minute after the post + 0.02% slippage; (L) limit at the written entry,
    valid 60 minutes; stop distance d measured from the fill; trades with d below 0.3% or above 10% are skipped
    (counted);
  * target: entry + d for a long, entry - d for a short (1:1); checks with 1.5:1 and 2:1; close after 24 hours at most;
    a minute touching both stop and target counts as a stop (conservative; counted);
  * costs: 0.05% fee per side, 0.02% slippage on market entry and on the stop; funding not counted;
  * comparison: the same rule at a random minute in the 3 days before the post (seed 11): does the channel's timing
    add anything to the 1:1 rule?
  * results per trade (no leverage), with the 95% bootstrap interval, separately for Oct 9-30 and Oct 31 - Nov 6;
    break-even needs more than 50% winners plus the costs.
```
Segnali con candele complete (60 minuti prima, 24 ore dopo): **2,706** (9-30 ottobre 2,213, 31 ottobre - 6 novembre 493).

## Risultato per operazione (senza leva, commissioni comprese)
| regola | periodo | n | media_% | IC95_basso_% | IC95_alto_% | vincenti_% | vincita_media_% | perdita_media_% | profit_factor | somma_% | minuti_medi | minuti_ambigui |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| regola principale: 30 min, 1:1, entrata subito | 9-30 ottobre | 2000 | 0.002272 | -0.1858 | 0.1875 | 50.9 | 3.488 | -3.611 | 1.001 | 4.544 | 169.3 | 2 |
| regola principale: 30 min, 1:1, entrata subito | 31 ottobre - 6 novembre | 451 | -0.3255 | -0.7482 | 0.07567 | 47.01 | 3.856 | -4.035 | 0.8478 | -146.8 | 198.8 | 0 |
| regola principale: 30 min, 1:1, entrata subito | tutto | 2451 | -0.05804 | -0.2227 | 0.1162 | 50.18 | 3.552 | -3.694 | 0.9685 | -142.3 | 174.8 | 2 |
| 30 min, 1:1, limite al prezzo scritto | 9-30 ottobre | 1631 | 0.07211 | -0.1089 | 0.2528 | 52.91 | 3.093 | -3.322 | 1.046 | 117.6 | 123.1 | 8 |
| 30 min, 1:1, limite al prezzo scritto | 31 ottobre - 6 novembre | 346 | -0.1353 | -0.5902 | 0.2955 | 49.42 | 3.571 | -3.757 | 0.9288 | -46.8 | 143.3 | 2 |
| 30 min, 1:1, limite al prezzo scritto | tutto | 1977 | 0.03582 | -0.145 | 0.1999 | 52.3 | 3.172 | -3.403 | 1.022 | 70.81 | 126.6 | 10 |
| 15 min, 1:1, entrata subito | 9-30 ottobre | 2020 | -0.02668 | -0.1902 | 0.1351 | 51.04 | 3.033 | -3.217 | 0.9831 | -53.89 | 118.2 | 2 |
| 15 min, 1:1, entrata subito | 31 ottobre - 6 novembre | 466 | -0.2992 | -0.621 | 0.05689 | 46.57 | 3.287 | -3.425 | 0.8365 | -139.4 | 113.3 | 0 |
| 15 min, 1:1, entrata subito | tutto | 2486 | -0.07776 | -0.2185 | 0.06641 | 50.2 | 3.077 | -3.258 | 0.9521 | -193.3 | 117.3 | 2 |
| 60 min, 1:1, entrata subito | 9-30 ottobre | 1928 | 0.007238 | -0.2013 | 0.2193 | 50.16 | 3.944 | -3.954 | 1.004 | 13.96 | 254.7 | 1 |
| 60 min, 1:1, entrata subito | 31 ottobre - 6 novembre | 420 | -0.5355 | -1.01 | -0.07439 | 45 | 4.328 | -4.515 | 0.7843 | -224.9 | 298.4 | 0 |
| 60 min, 1:1, entrata subito | tutto | 2348 | -0.08985 | -0.2746 | 0.09732 | 49.23 | 4.007 | -4.063 | 0.9564 | -211 | 262.5 | 1 |
| 30 min, 1,5:1, entrata subito | 9-30 ottobre | 2000 | -0.06435 | -0.2857 | 0.1573 | 40.75 | 5.064 | -3.591 | 0.9698 | -128.7 | 241.8 | 1 |
| 30 min, 1,5:1, entrata subito | 31 ottobre - 6 novembre | 451 | -0.4173 | -0.9294 | 0.1087 | 37.03 | 5.726 | -4.03 | 0.8356 | -188.2 | 270.3 | 0 |
| 30 min, 1,5:1, entrata subito | tutto | 2451 | -0.1293 | -0.3281 | 0.06364 | 40.07 | 5.177 | -3.676 | 0.9413 | -316.9 | 247.1 | 1 |
| 30 min, 2:1, entrata subito | 9-30 ottobre | 2000 | -0.09598 | -0.3345 | 0.1444 | 34.95 | 6.39 | -3.581 | 0.9588 | -192 | 304.7 | 0 |
| 30 min, 2:1, entrata subito | 31 ottobre - 6 novembre | 451 | -0.1185 | -0.7096 | 0.4655 | 32.82 | 7.742 | -3.958 | 0.9554 | -53.45 | 321.9 | 0 |
| 30 min, 2:1, entrata subito | tutto | 2451 | -0.1001 | -0.3434 | 0.1314 | 34.56 | 6.626 | -3.652 | 0.9581 | -245.4 | 307.8 | 0 |
| stessa regola a un minuto CASUALE (confronto) | 9-30 ottobre | 1486 | -0.1044 | -0.197 | -0.0104 | 49.66 | 1.262 | -1.452 | 0.8572 | -155.2 |  |  |
| stessa regola a un minuto CASUALE (confronto) | 31 ottobre - 6 novembre | 367 | -0.05164 | -0.2937 | 0.2005 | 49.59 | 1.774 | -1.847 | 0.9445 | -18.95 |  |  |
| stessa regola a un minuto CASUALE (confronto) | tutto | 1853 | -0.09397 | -0.1871 | -0.003961 | 49.65 | 1.363 | -1.531 | 0.8781 | -174.1 |  |  |

Operazioni saltate (stop non valido): K15_rr1_M stop troppo vicino o troppo lontano: 220; K30_rr1.5_M stop troppo vicino o troppo lontano: 255; K30_rr1_L stop troppo vicino o troppo lontano: 218; K30_rr1_M stop troppo vicino o troppo lontano: 255; K30_rr2_M stop troppo vicino o troppo lontano: 255; K60_rr1_M stop troppo vicino o troppo lontano: 358

## Come finiscono (regola principale)
| K30_rr1_M_fine | quota_% |
|---|---|
| obiettivo | 49.29 |
| stop | 48.35 |
| 24 ore | 2.366 |


## Per direzione (regola principale)
| direzione | n | media_% | IC95_basso_% | IC95_alto_% | vincenti_% | vincita_media_% | perdita_media_% | profit_factor | somma_% |
|---|---|---|---|---|---|---|---|---|---|
| LONG | 1437 | -0.1523 | -0.3589 | 0.06501 | 48.71 | 3.428 | -3.553 | 0.9164 | -218.9 |
| SHORT | 1014 | 0.07556 | -0.198 | 0.3542 | 52.27 | 3.715 | -3.91 | 1.04 | 76.61 |


## Con la leva (regola principale, media per operazione sul margine)
5x: -0.29%, 10x: -0.58%, 20x: -1.16%
