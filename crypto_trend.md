# Studio storico: strategie con una logica sulle crypto affermate (Binance, 2018-2026)

Pre-registrazione (testo originale):

```
(written before looking at any result):
  * universe at each date: the most traded pairs by 30-day average USDT volume known the day before (top 10 for the
    trend baskets, top 30 for momentum), at least 60 days of history; stablecoins and leveraged tokens excluded;
    a pair that stops trading is exited at its last price;
  * timing: a signal computed on the close of day t is held from the close of day t to the close of day t+1;
  * costs: 0.15% per side on every change of weight (0.10% fee + 0.05% slippage); cash earns nothing;
  * benchmarks: BTC buy & hold; equal-weight top 10, rebalanced monthly;
  * strategies:
      TF-BTC-N   BTC only while its close is above its N-day average (N = 50, 100, 200), otherwise cash;
      TF-10-N    top 10, each with a 1/10 slot held while the coin is above its own N-day average;
      XM-L       every Monday the 5 coins of the top 30 with the best L-day return (L = 7, 28, 90), equal weight;
      XMF-L      XM-L, only coins with a positive L-day return, and only while BTC is above its 100-day average;
      DON        top 10 Donchian: enter above the 50-day high, exit below the 20-day low, 1/10 slots;
  * walk-forward: each family's parameter is chosen on 2018-2021 (best Sharpe), and judged on 2022-01-01 .. the
    end of the data, never seen when choosing; every parameter's out-of-sample result is shown anyway;
  * statistics: CAGR, volatility, Sharpe (365 days), maximum drawdown, yearly returns; 95% interval of the
    out-of-sample Sharpe by block bootstrap (20-day blocks); verdict "regge" only when the chosen parameter has a
    positive out-of-sample CAGR with the Sharpe interval above zero.
```
Dati: 697 coppie USDT, dal 2017-08-17 al 2026-10-31 (803,352 candele giornaliere).

## Tutte le strategie: dentro il campione (2018-2021) e fuori campione (2022 - fine dati)
| strategia | IS_CAGR_% | IS_Sharpe | IS_maxDD_% | OOS_CAGR_% | OOS_Sharpe | OOS_Sharpe_IC95 | OOS_maxDD_% | OOS_vol_% | OOS_finale_x |
|---|---|---|---|---|---|---|---|---|---|
| BH-BTC | 35.46 | 0.788 | -81.18 | 11.31 | 0.4644 | [-0.51, 1.36] | -66.93 | 50.34 | 1.679 |
| BH-TOP10 | 17.27 | 0.6557 | -88.81 | -33.28 | -0.215 | [-0.99, 0.76] | -91.19 | 70.58 | 0.1414 |
| TF-BTC-50 | 75.09 | 1.34 | -60.13 | 20.04 | 0.7145 | [-0.27, 1.72] | -51.2 | 33.29 | 2.419 |
| TF-10-50 | 60.37 | 1.172 | -42.64 | -7.602 | -0.03018 | [-1.13, 0.92] | -68.27 | 36.85 | 0.6823 |
| TF-BTC-100 | 55.54 | 1.084 | -60.22 | 20.78 | 0.7437 | [-0.24, 1.67] | -36.8 | 32.37 | 2.491 |
| TF-10-100 | 34.11 | 0.8086 | -57.29 | -16.64 | -0.2552 | [-1.16, 0.70] | -77.85 | 39.93 | 0.4147 |
| TF-BTC-200 | 21.41 | 0.6355 | -64.41 | 27.34 | 0.8883 | [-0.04, 1.72] | -32.1 | 33.44 | 3.217 |
| TF-10-200 | 28.61 | 0.7335 | -62.08 | -17.44 | -0.2707 | [-1.19, 0.72] | -62.68 | 40.38 | 0.396 |
| XM-7 | 14 | 0.6969 | -92.14 | -66.63 | -0.7812 | [-1.60, 0.07] | -99.68 | 89.25 | 0.004953 |
| XMF-7 | 108.9 | 1.298 | -66.56 | -33.85 | -0.2868 | [-1.13, 0.50] | -90.61 | 66.7 | 0.1355 |
| XM-28 | 45.17 | 0.9118 | -92.56 | -68.62 | -0.7312 | [-1.53, 0.10] | -99.66 | 95.81 | 0.00368 |
| XMF-28 | 132.8 | 1.415 | -62.94 | -29.31 | -0.1481 | [-0.99, 0.65] | -84.08 | 70.07 | 0.1869 |
| XM-90 | 42.09 | 0.8799 | -87.5 | -72.37 | -0.8218 | [-1.62, 0.02] | -99.82 | 97.76 | 0.001991 |
| XMF-90 | 137.7 | 1.482 | -51.85 | -29.03 | -0.1446 | [-0.97, 0.59] | -83.93 | 69.66 | 0.1905 |
| DON | 47.27 | 1.172 | -34.29 | 3.725 | 0.2711 | [-0.68, 1.27] | -43.79 | 26.32 | 1.193 |

## Walk-forward: il parametro scelto solo sul 2018-2021, giudicato dopo
| famiglia | scelto | OOS_CAGR_% | OOS_Sharpe | OOS_Sharpe_IC95 | OOS_maxDD_% | verdetto |
|---|---|---|---|---|---|---|
| TF-BTC | TF-BTC-50 | 20.04 | 0.7145 | [-0.27, 1.72] | -51.2 | non regge |
| TF-10 | TF-10-50 | -7.602 | -0.03018 | [-1.13, 0.92] | -68.27 | non regge |
| XM | XM-28 | -68.62 | -0.7312 | [-1.53, 0.10] | -99.66 | non regge |
| XMF | XMF-90 | -29.03 | -0.1446 | [-0.97, 0.59] | -83.93 | non regge |
| DON | DON | 3.725 | 0.2711 | [-0.68, 1.27] | -43.79 | non regge |
| riferimento | BH-BTC | 11.31 | 0.4644 | [-0.51, 1.36] | -66.93 | - |
| riferimento | BH-TOP10 | -33.28 | -0.215 | [-0.99, 0.76] | -91.19 | - |

## Rendimento anno per anno (%)
| strategia | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|
| BH-BTC | -73 | 94.31 | 302 | 59.79 | -64.21 | 155.6 | 121.3 | -6.335 | -11.48 |
| BH-TOP10 | -77.97 | 13.77 | 124.8 | 235.8 | -89.19 | 54.88 | 70.12 | -36.31 | -22.09 |
| TF-BTC-50 | -43.46 | 80.37 | 311 | 124.5 | -50.55 | 138 | 75.7 | 3.035 | 13.54 |
| TF-10-50 | -28.86 | 49.54 | 83.15 | 239.9 | -53.82 | 17.08 | 34.65 | -7.371 | 1.182 |
| TF-BTC-100 | -46.5 | 133 | 166.1 | 76.64 | -21.14 | 81.38 | 63.43 | 3.797 | 2.677 |
| TF-10-100 | -16.9 | 57.14 | 5.133 | 135.8 | -61.62 | -7.089 | 52.46 | -16.92 | -8.192 |
| TF-BTC-200 | -35.14 | 56.84 | 173.2 | -21.77 | 0 | 93.72 | 80.75 | -17.76 | 11.73 |
| TF-10-200 | -11.17 | 13.25 | 31.61 | 106.8 | -46.39 | 13.91 | 29.22 | -36.82 | -20.58 |
| XM-7 | -80.22 | -12.47 | 231.4 | 194.5 | -91.16 | -17.86 | -22.71 | -74.17 | -65.84 |
| XMF-7 | -29.31 | -7.538 | 348 | 551.3 | -40.75 | -45.2 | -22.32 | -45.92 | -0.6383 |
| XM-28 | -83.33 | 6.356 | 277.2 | 564.8 | -92.84 | -10.32 | 74.52 | -68.32 | -89.64 |
| XMF-28 | -36.55 | 4.077 | 437.3 | 729.8 | -37.03 | -47.63 | 17.89 | -28.86 | -32.44 |
| XM-90 | -77.93 | 44.69 | 140.3 | 431.8 | -95.58 | -2.952 | 18.09 | -64.66 | -88.88 |
| XMF-90 | -10.38 | 64.97 | 140 | 802.4 | -34.22 | -43.77 | 20.2 | -34.51 | -34.56 |
| DON | -10.98 | 49.84 | 67.15 | 111.2 | -37.81 | 40.23 | 50.6 | -0.6318 | -8.561 |

