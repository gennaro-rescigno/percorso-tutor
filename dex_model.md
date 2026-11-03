# Studio storico: un modello portabile per i token quotati, tenuta 1 e 4 ore

Pre-registrazione (testo originale):

```
(written before looking at any result):
  * features, all unit-free so they exist for any token on any DEX: age since listing (h), return over 5 minutes,
    1 hour and 6 hours, return since listing, distance from the highest price so far, 1-hour volume / liquidity,
    5-minute volume / 1-hour volume (acceleration), buys / (buys + sells) in the last hour (count), log of the
    trades in the last hour, market cap / liquidity;
  * targets: net return of a 0.1 SOL trade held 1 and 4 hours, exit at the first observation at or after that time;
    (correction after the first run, before reading any corrected number: both trades go through the pool's
    constant product with its reserve at that moment, so a price spike in an empty pool cannot be cashed);
    costs: 3% latency, 1% pool fee per side, 1% priority fees; a token with no later observation is valued at its
    last observation (optimistic) and, as a second reading, at -100% (pessimistic): both are reported;
  * model: scikit-learn HistGradientBoostingRegressor (fixed settings), target clipped to [-100%, +300%];
    A: walk-forward by day (first 14 days for training, retrained every 3 days); B: trained once on all of A;
  * selections, one trade per token and day (first selected moment): every moment (reference), predicted > 0,
    top 5%, top 1% of the training predictions;
  * verdict "positive" only with q (Benjamini-Hochberg over all tests) < 0.05 and both halves of A positive; a rule
    is "portable" only if it is also positive on B (the other period).
```
A (giugno-luglio): 1,002,433 momenti di decisione di 5,067 token, 28 giorni.
B (settembre, altra fonte): 152,656 momenti orari di 28,721 token.
| dati | tenuta_h | selezione | lettura | n | media_% | IC95_basso_% | IC95_alto_% | p | mediana_% | vincenti_% | 1a_metà_% | 2a_metà_% | q_BH | verdetto |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A giu-lug | 1 | P0 ogni momento | ottimistica | 10317 | -41.59 | -43.66 | -39.12 | 1 | -41.92 | 5.99 | -22.89 | -48.68 | 1 | non dimostrata |
| A giu-lug | 1 | P0 ogni momento | pessimistica | 10317 | -42.78 | -44.92 | -40.27 | 1 | -51.07 | 5.961 | -24 | -49.9 | 1 | non dimostrata |
| A giu-lug | 1 | P1 previsto > 0 | ottimistica | 1006 | -2.869 | -15.5 | 17.15 | 0.6725 | -19.95 | 25.94 | -17.76 | 12.26 | 1 | non dimostrata |
| A giu-lug | 1 | P1 previsto > 0 | pessimistica | 1006 | -3.054 | -15.97 | 16.09 | 0.69 | -20.33 | 25.94 | -17.95 | 12.08 | 1 | non dimostrata |
| A giu-lug | 1 | P2 5% più alto | ottimistica | 1699 | -11.31 | -15.75 | -6.483 | 1 | -11.43 | 22.42 | -20.37 | -7.679 | 1 | non dimostrata |
| A giu-lug | 1 | P2 5% più alto | pessimistica | 1699 | -12.38 | -16.52 | -7.558 | 1 | -12.17 | 22.37 | -20.56 | -9.099 | 1 | non dimostrata |
| A giu-lug | 1 | P3 1% più alto | ottimistica | 430 | -6.303 | -18.93 | 9.708 | 0.811 | -19.72 | 27.21 | -16.12 | -2.804 | 1 | non dimostrata |
| A giu-lug | 1 | P3 1% più alto | pessimistica | 430 | -6.896 | -20.82 | 8.154 | 0.8365 | -20.49 | 27.21 | -16.12 | -3.608 | 1 | non dimostrata |
| A giu-lug | 4 | P0 ogni momento | ottimistica | 10317 | -43.45 | -46.41 | -40.23 | 1 | -65.31 | 5.001 | -21.49 | -51.78 | 1 | non dimostrata |
| A giu-lug | 4 | P0 ogni momento | pessimistica | 10317 | -47.26 | -50.24 | -43.72 | 1 | -78.91 | 4.817 | -25.82 | -55.39 | 1 | non dimostrata |
| A giu-lug | 4 | P1 previsto > 0 | ottimistica | 915 | -21.49 | -29.63 | -11.7 | 1 | -31.49 | 17.6 | -17.16 | -26.77 | 1 | non dimostrata |
| A giu-lug | 4 | P1 previsto > 0 | pessimistica | 915 | -22.33 | -30.5 | -12.37 | 1 | -32.88 | 17.38 | -18.67 | -26.8 | 1 | non dimostrata |
| A giu-lug | 4 | P2 5% più alto | ottimistica | 1640 | -16.1 | -20.79 | -10.83 | 1 | -13.94 | 15.61 | -17.38 | -15.6 | 1 | non dimostrata |
| A giu-lug | 4 | P2 5% più alto | pessimistica | 1640 | -20.95 | -25.85 | -15.48 | 1 | -17.74 | 15.49 | -17.7 | -22.19 | 1 | non dimostrata |
| A giu-lug | 4 | P3 1% più alto | ottimistica | 266 | -22.73 | -35.68 | -7.255 | 0.998 | -46.29 | 19.92 | -31.61 | -18.42 | 1 | non dimostrata |
| A giu-lug | 4 | P3 1% più alto | pessimistica | 266 | -23.47 | -36.67 | -7.469 | 0.999 | -48.59 | 19.92 | -31.61 | -19.51 | 1 | non dimostrata |
| B settembre | 1 | P0 ogni momento | ottimistica | 47566 | -20.33 | -20.57 | -20.08 | 1 | -9.962 | 1.787 |  |  | 1 | non dimostrata |
| B settembre | 1 | P0 ogni momento | pessimistica | 47566 | -53.2 | -53.6 | -52.8 | 1 | -42.64 | 1.77 |  |  | 1 | non dimostrata |
| B settembre | 1 | P1 previsto > 0 | ottimistica | 169 | -13.99 | -16.48 | -11.8 | 1 | -12.62 | 4.142 |  |  | 1 | non dimostrata |
| B settembre | 1 | P1 previsto > 0 | pessimistica | 169 | -35.59 | -41.53 | -29.65 | 1 | -14.02 | 4.142 |  |  | 1 | non dimostrata |
| B settembre | 1 | P2 5% più alto | ottimistica | 6912 | -9.422 | -9.648 | -9.169 | 1 | -8.545 | 2.112 |  |  | 1 | non dimostrata |
| B settembre | 1 | P2 5% più alto | pessimistica | 6912 | -30.42 | -31.37 | -29.44 | 1 | -9.653 | 2.098 |  |  | 1 | non dimostrata |
| B settembre | 1 | P3 1% più alto | ottimistica | 412 | -11.89 | -13.39 | -10.47 | 1 | -7.361 | 2.913 |  |  | 1 | non dimostrata |
| B settembre | 1 | P3 1% più alto | pessimistica | 412 | -28.88 | -32.44 | -25.49 | 1 | -9.858 | 2.913 |  |  | 1 | non dimostrata |
| B settembre | 4 | P0 ogni momento | ottimistica | 47566 | -20.66 | -20.93 | -20.37 | 1 | -10.42 | 2.357 |  |  | 1 | non dimostrata |
| B settembre | 4 | P0 ogni momento | pessimistica | 47566 | -56.68 | -57.12 | -56.24 | 1 | -96.84 | 2.292 |  |  | 1 | non dimostrata |
| B settembre | 4 | P1 previsto > 0 | ottimistica | 499 | -23.18 | -25.38 | -21.11 | 1 | -11.3 | 2.806 |  |  | 1 | non dimostrata |
| B settembre | 4 | P1 previsto > 0 | pessimistica | 499 | -50.19 | -54.1 | -46.22 | 1 | -20.79 | 2.605 |  |  | 1 | non dimostrata |
| B settembre | 4 | P2 5% più alto | ottimistica | 12504 | -10.85 | -11.18 | -10.33 | 1 | -9.719 | 2.375 |  |  | 1 | non dimostrata |
| B settembre | 4 | P2 5% più alto | pessimistica | 12504 | -37.17 | -37.98 | -36.28 | 1 | -12.12 | 2.287 |  |  | 1 | non dimostrata |
| B settembre | 4 | P3 1% più alto | ottimistica | 881 | -18.63 | -20.08 | -17.21 | 1 | -7.743 | 3.519 |  |  | 1 | non dimostrata |
| B settembre | 4 | P3 1% più alto | pessimistica | 881 | -42.49 | -45.46 | -39.48 | 1 | -12.25 | 3.292 |  |  | 1 | non dimostrata |

