# Studio storico: operazioni brevi (1-3 giorni) su moltissime monete, memecoin comprese (Binance 2018-2026)

Pre-registrazione (testo originale):

```
(written before looking at any result):
  * universe each day: the 100 most traded USDT pairs by 30-day average volume known the day before (memecoins
    such as DOGE, SHIB, PEPE, WIF, BONK, FLOKI included whenever they are in it), >= 60 days of history,
    stablecoins and leveraged tokens excluded, delisted pairs included with their real losses;
  * entries at the daily close (00:00 UTC) after the signal; exit at the close 1, 2 or 3 days later, or earlier at
    a -15% stop on the daily low (filled at the stop, or at the open if the day opens below it);
  * rules:
      H1 hype burst: day return >= +10% and volume >= 3x its 30-day average;
      H2 H1 only while BTC is above its 50-day average;
      P1 pullback in an uptrend: coin above its 50-day average and day return <= -7%;
      B1 breakout: close above the previous 20-day high, volume >= 2x average, BTC above its 50-day average;
      S1 short-term strength: the 5 best 3-day returns of the top 50, BTC above its 50-day average;
      M1 model: gradient-boosted trees on 15 daily features (returns 1/3/7/30 days, volume vs average,
         distance from the 20/50/200-day averages, 14-day volatility, age, liquidity rank, BTC's return and
         trend), trained on the past only (expanding window, retrained every 90 days from 2021-01-01), entering
         the 5 best predictions of the day when the prediction is above zero;
  * portfolio: at most 10 positions at once, 10% of equity each, a new signal is skipped when full (strongest
    first); costs per side: 0.10% fee + slippage 0.05% (top 30) or 0.20% (rank 31-100);
  * periods: 2018-2021 (in sample) and 2022-01-01 .. end (out of sample); verdict "regge" only with a positive
    out-of-sample CAGR, a 95% interval of the daily Sharpe above zero and positive results in both periods.
```
Universo: le 100 più scambiate di ogni giorno; memecoin presenti in media 3.3 al giorno (DOGE, SHIB, PEPE, WIF, BONK, FLOKI, BOME, 1000SATS, MEME, TRUMP).
| regola | giorni | IS_CAGR_% | IS_maxDD_% | OOS_CAGR_% | OOS_Sharpe | OOS_Sharpe_IC95 | OOS_maxDD_% | OOS_operazioni | OOS_media_op_% | OOS_vincenti_% | verdetto |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 1 | -18.35 | -59.49 | -30.13 | -0.8559 | [-1.68, -0.08] | -83.89 | 2224 | -0.6509 | 37.37 | non regge |
| H1 | 2 | -8.673 | -58.92 | -20.98 | -0.3459 | [-1.25, 0.52] | -69.95 | 1906 | -0.4112 | 37.15 | non regge |
| H1 | 3 | 10.02 | -55.88 | -20.24 | -0.2393 | [-1.21, 0.63] | -77.49 | 1725 | -0.3385 | 35.88 | non regge |
| H2 | 1 | -8.257 | -50.63 | -11.09 | -0.276 | [-1.10, 0.38] | -56.45 | 1620 | -0.2336 | 38.95 | non regge |
| H2 | 2 | 4.76 | -44.2 | 7.647 | 0.3813 | [-0.50, 1.19] | -44.35 | 1371 | 0.4522 | 40.63 | non regge |
| H2 | 3 | 24.11 | -41.64 | 11.66 | 0.4712 | [-0.50, 1.35] | -51.22 | 1216 | 0.7643 | 38.9 | non regge |
| P1 | 1 | -12.11 | -58.76 | -52.04 | -1.472 | [-2.34, -0.61] | -97.18 | 3946 | -0.7834 | 41.33 | non regge |
| P1 | 2 | -17.78 | -78.22 | -58.63 | -1.35 | [-2.16, -0.56] | -98.68 | 3378 | -1.075 | 38.57 | non regge |
| P1 | 3 | -10.81 | -68.64 | -57.54 | -1.13 | [-1.92, -0.30] | -98.6 | 2941 | -1.13 | 38.35 | non regge |
| B1 | 1 | -7.685 | -64.1 | -29.54 | -0.7102 | [-1.66, 0.12] | -83.02 | 3715 | -0.3585 | 39.54 | non regge |
| B1 | 2 | 27.37 | -33.24 | -8.352 | 0.02116 | [-1.09, 1.04] | -57.43 | 2432 | 0.03345 | 40.71 | non regge |
| B1 | 3 | 41.8 | -56.88 | -12.78 | -0.05669 | [-1.02, 0.87] | -68.87 | 1919 | -0.07884 | 40.07 | non regge |
| S1 | 1 | -4.099 | -65.65 | -41.25 | -1.252 | [-2.37, -0.24] | -92.73 | 4580 | -0.4893 | 40.22 | non regge |
| S1 | 2 | 5.084 | -71.96 | -39.99 | -0.8835 | [-1.99, 0.11] | -92.53 | 3208 | -0.5948 | 40.43 | non regge |
| S1 | 3 | 8.318 | -72.01 | -44.42 | -0.9168 | [-2.05, 0.21] | -94.42 | 2550 | -0.8457 | 38.59 | non regge |
| M1 | 1 | 15.04 | -54.42 | -55.62 | -1.534 | [-2.49, -0.73] | -98.2 | 6847 | -0.5057 | 40.22 | non regge |
| M1 | 2 | 23.77 | -63.96 | -54.54 | -0.8556 | [-1.79, 0.03] | -97.95 | 5517 | -0.5004 | 40.95 | non regge |
| M1 | 3 | 29.06 | -66.63 | -64.87 | -1.089 | [-2.01, -0.20] | -99.41 | 4446 | -0.8693 | 39.97 | non regge |

