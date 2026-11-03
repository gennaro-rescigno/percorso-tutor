# Studio storico: cosa succede dopo il diploma e le entrate su PumpSwap

Pre-registrazione (testo originale):

```
(written before looking at any result):
  * entries at a fixed delay after the graduation: 1, 5, 10 and 30 minutes (jocry `price_at_*m_usd`);
  * exits: 1, 6 and 24 hours after the ENTRY, at the first pool snapshot at or after that moment; a token with no
    snapshot that late is closed at its last snapshot (the pool stopped trading or the collector stopped);
  * filters: P0 all graduates; P1 organic graduation (>= 5 minutes on the curve); P2 survived the first dump
    (price at 10 min >= 50% of the graduation price, entries at 10 and 30 min only); P3 dip buy (price at 10 min
    <= 20% of the graduation price, entries at 10 and 30 min only);
  * costs: entry 3% worse than the snapshot (latency), pool fee 0.3% per side, priority fees 1% per round trip;
  * statistics as in loop_curve: bootstrap 95% interval of the mean, Benjamini-Hochberg over all tests, verdict
    "positive and stable" only with q < 0.05 and both halves of the period positive (split on 2026-06-25).
```

## 2. Primi 30 minuti dei pool (settembre-ottobre 2026, loopholetape): 27,096 pool completi
- prezzo dopo 30 min rispetto al primo scambio nel pool: mediana ×0.020; <= ×0,1 nel 58.9%; >= ×1 nel 27.5%; >= ×2 nel 11.5%
- crollo a un decimo del prezzo iniziale: 61.2% dei pool, tempo mediano 516 s
- comprare al primo scambio e vendere dopo 30 minuti (costi inclusi): media 70748074.3% [-20579925.5%, 162635089.8%], vincenti 23.7%

## 1. Dopo il diploma (giugno-luglio 2026, jocry): 5,669 token diplomati con prezzo al diploma
- prezzo a 1 min dal diploma rispetto al diploma: mediana ×1.00; sotto ×0,5 nel 20.5%; sotto ×0,2 nel 12.4%; sopra ×2 nel 10.6%
- prezzo a 5 min dal diploma rispetto al diploma: mediana ×0.92; sotto ×0,5 nel 36.0%; sotto ×0,2 nel 25.8%; sopra ×2 nel 10.4%
- prezzo a 10 min dal diploma rispetto al diploma: mediana ×0.80; sotto ×0,5 nel 40.5%; sotto ×0,2 nel 30.3%; sopra ×2 nel 10.9%
- prezzo a 30 min dal diploma rispetto al diploma: mediana ×0.58; sotto ×0,5 nel 48.0%; sotto ×0,2 nel 36.9%; sopra ×2 nel 11.1%
- massimo dopo il diploma: mediana ×1.05; almeno ×2 nel 29.5%; almeno ×10 nel 7.8%
- ancora liquidi dopo 24 h: 31.0%; rug segnalato: 3.2%
- esiti (etichette del dataset): dead 2692, pump_dump 1072, slow_bleed 784, major_pump 607, minor_pump 320, sustained 194
- copertura istantanee: mediana 256 istantanee per token

### Entrate dopo il diploma (costi inclusi, una operazione per token)
| filtro | ingresso_min | tenuta_h | n | media_% | IC95_basso_% | IC95_alto_% | p | mediana_% | vincenti_% | 1a_metà_% | 2a_metà_% | q_BH | verdetto |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P0 tutti | 1 | 1 | 5669 | 15.12 | -9.709 | 56.37 | 0.3 | -38.22 | 15.61 | 162.9 | 5.862 | 1 | non dimostrata |
| P0 tutti | 1 | 6 | 5669 | -2.967 | -21.72 | 23.32 | 0.6255 | -69.9 | 9.473 | 301 | -21.99 | 1 | non dimostrata |
| P0 tutti | 1 | 24 | 5669 | 4.236 | -19.33 | 32.79 | 0.404 | -91.74 | 9.049 | 286.1 | -13.41 | 1 | non dimostrata |
| P0 tutti | 5 | 1 | 5667 | -0.3587 | -9.212 | 10.84 | 0.5705 | -10.66 | 15.33 | 51.6 | -3.613 | 1 | non dimostrata |
| P0 tutti | 5 | 6 | 5667 | -6.25 | -18.43 | 10.54 | 0.7845 | -36.68 | 9.299 | 181.4 | -18 | 1 | non dimostrata |
| P0 tutti | 5 | 24 | 5667 | 19.2 | -12.68 | 59.73 | 0.138 | -76.52 | 8.788 | 209.5 | 7.285 | 1 | non dimostrata |
| P0 tutti | 10 | 1 | 5664 | 0.4815 | -7.895 | 12.94 | 0.505 | -6.011 | 14.92 | 44.07 | -2.25 | 1 | non dimostrata |
| P0 tutti | 10 | 6 | 5664 | -4.284 | -15.87 | 12.49 | 0.749 | -23.74 | 9.34 | 167.1 | -15.02 | 1 | non dimostrata |
| P0 tutti | 10 | 24 | 5664 | 14.02 | -12.52 | 45.84 | 0.1605 | -67.83 | 9.04 | 205.2 | 2.038 | 1 | non dimostrata |
| P0 tutti | 30 | 1 | 5638 | -1.958 | -6.694 | 4.064 | 0.7685 | -4.494 | 13.59 | 46.73 | -5.024 | 1 | non dimostrata |
| P0 tutti | 30 | 6 | 5638 | -3.648 | -14.44 | 12.01 | 0.718 | -10.73 | 9.649 | 126.4 | -11.84 | 1 | non dimostrata |
| P0 tutti | 30 | 24 | 5638 | 13.43 | -10.74 | 43.86 | 0.171 | -52.03 | 9.028 | 145.9 | 5.092 | 1 | non dimostrata |
| P1 diploma organico (>= 5 min sulla curva) | 1 | 1 | 976 | -1.462 | -27.36 | 31.86 | 0.5665 | -77.18 | 14.34 | 175.5 | -5.543 | 1 | non dimostrata |
| P1 diploma organico (>= 5 min sulla curva) | 1 | 6 | 976 | 26.25 | -46.76 | 159 | 0.3875 | -88.04 | 8.402 | 505.7 | 15.2 | 1 | non dimostrata |
| P1 diploma organico (>= 5 min sulla curva) | 1 | 24 | 976 | -20.37 | -53.78 | 21.59 | 0.8455 | -92.49 | 6.762 | 255.6 | -26.73 | 1 | non dimostrata |
| P1 diploma organico (>= 5 min sulla curva) | 5 | 1 | 976 | -4.034 | -18.45 | 12.67 | 0.7015 | -49.47 | 16.91 | 80.9 | -5.993 | 1 | non dimostrata |
| P1 diploma organico (>= 5 min sulla curva) | 5 | 6 | 976 | -16.97 | -37.76 | 10.22 | 0.908 | -69.12 | 10.04 | 190.4 | -21.76 | 1 | non dimostrata |
| P1 diploma organico (>= 5 min sulla curva) | 5 | 24 | 976 | -28.36 | -51.42 | 5.917 | 0.955 | -79.94 | 6.762 | 94.54 | -31.19 | 1 | non dimostrata |
| P1 diploma organico (>= 5 min sulla curva) | 10 | 1 | 975 | -3.355 | -17.1 | 12.84 | 0.688 | -34.07 | 17.64 | 66.26 | -4.962 | 1 | non dimostrata |
| P1 diploma organico (>= 5 min sulla curva) | 10 | 6 | 975 | -14.62 | -32.87 | 9.991 | 0.884 | -56.19 | 11.08 | 114.2 | -17.59 | 1 | non dimostrata |
| P1 diploma organico (>= 5 min sulla curva) | 10 | 24 | 975 | -22.46 | -44.54 | 9.123 | 0.927 | -70.62 | 7.795 | 92.15 | -25.1 | 1 | non dimostrata |
| P1 diploma organico (>= 5 min sulla curva) | 30 | 1 | 970 | -7.454 | -13.63 | 0.003061 | 0.9745 | -13.56 | 16.49 | 63.79 | -9.107 | 1 | non dimostrata |
| P1 diploma organico (>= 5 min sulla curva) | 30 | 6 | 970 | -19.44 | -27.19 | -11.25 | 1 | -33.55 | 12.68 | 73.33 | -21.6 | 1 | non dimostrata |
| P1 diploma organico (>= 5 min sulla curva) | 30 | 24 | 970 | -28.69 | -39.78 | -15.97 | 0.9995 | -52.41 | 8.763 | 33.25 | -30.13 | 1 | non dimostrata |
| P2 ha retto il primo crollo (a 10 min >= 50% del diploma) | 10 | 1 | 3368 | -6.313 | -10.13 | -2.112 | 0.999 | -4.494 | 16.09 | 37.31 | -10.8 | 1 | non dimostrata |
| P2 ha retto il primo crollo (a 10 min >= 50% del diploma) | 10 | 6 | 3368 | -15.74 | -21.32 | -9.596 | 1 | -5.002 | 9.204 | 57.29 | -23.25 | 1 | non dimostrata |
| P2 ha retto il primo crollo (a 10 min >= 50% del diploma) | 10 | 24 | 3368 | 11.91 | -18.12 | 54.48 | 0.2915 | -91.39 | 10.21 | 77.99 | 5.113 | 1 | non dimostrata |
| P2 ha retto il primo crollo (a 10 min >= 50% del diploma) | 30 | 1 | 3351 | -6.357 | -9.451 | -2.701 | 0.999 | -4.494 | 15.43 | 10.9 | -8.14 | 1 | non dimostrata |
| P2 ha retto il primo crollo (a 10 min >= 50% del diploma) | 30 | 6 | 3351 | -12.84 | -17.75 | -7.328 | 1 | -4.494 | 9.699 | 23.14 | -16.56 | 1 | non dimostrata |
| P2 ha retto il primo crollo (a 10 min >= 50% del diploma) | 30 | 24 | 3351 | 18.63 | -13.26 | 64.41 | 0.182 | -79.71 | 10.12 | 49.35 | 15.45 | 1 | non dimostrata |
| P3 compra il crollo (a 10 min <= 20% del diploma) | 10 | 1 | 1714 | 1.516 | -8.21 | 14.14 | 0.43 | -14.38 | 13.77 | 25.12 | 1.336 | 1 | non dimostrata |
| P3 compra il crollo (a 10 min <= 20% del diploma) | 10 | 6 | 1714 | -0.3701 | -15.08 | 17.73 | 0.5395 | -24.65 | 10.5 | 1.665 | -0.3856 | 1 | non dimostrata |
| P3 compra il crollo (a 10 min <= 20% del diploma) | 10 | 24 | 1714 | 8.659 | -23.87 | 60.64 | 0.375 | -34.11 | 7.643 | 5.881 | 8.681 | 1 | non dimostrata |
| P3 compra il crollo (a 10 min <= 20% del diploma) | 30 | 1 | 1707 | 0.176 | -7.357 | 11.15 | 0.516 | -5.317 | 11.01 | -2.479 | 0.1964 | 1 | non dimostrata |
| P3 compra il crollo (a 10 min <= 20% del diploma) | 30 | 6 | 1707 | -1.44 | -15.26 | 17.02 | 0.5955 | -13.08 | 9.842 | -6.599 | -1.401 | 1 | non dimostrata |
| P3 compra il crollo (a 10 min <= 20% del diploma) | 30 | 24 | 1707 | -0.7319 | -23.89 | 40.48 | 0.5785 | -23.23 | 7.206 | -6.419 | -0.6882 | 1 | non dimostrata |

