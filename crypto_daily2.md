# Robustezza di H2: hype con BTC in salita, tenuta 2-3 giorni (Binance 2018-2026)

```
crypto_daily found H2 the only short-trade rule positive in both periods (+11.7%/yr out of sample at 3 days) with
a very wide interval. Written before running, every variant is reported (none is picked):
  * thresholds around the original: day return >= 5% / 10% / 15%, volume >= 2x / 3x / 5x the 30-day average;
  * BTC filter on the 50- or 100-day average; stop at -10% / -15% / -25%;
  * costs doubled; entry one day late (the close after the signal day);
  * memecoins only vs everything else;
  * per-year results of the original H2 (3 days).
"Robust" would need most neighbouring variants positive out of sample and the late entry still positive.
```
| variante | IS_CAGR_% | OOS_CAGR_% | OOS_Sharpe | OOS_Sharpe_IC95 | OOS_maxDD_% | OOS_operazioni | OOS_media_op_% |
|---|---|---|---|---|---|---|---|
| H2 originale, 2 giorni | 4.76 | 7.647 | 0.3813 | [-0.50, 1.19] | -44.35 | 1371 | 0.4522 |
| H2 originale, 3 giorni | 24.11 | 11.66 | 0.4712 | [-0.43, 1.32] | -51.22 | 1216 | 0.7643 |
| soglie: prezzo >= 5%, volume >= 2x | 22.1 | -29.6 | -0.4439 | [-1.50, 0.49] | -87.79 | 2125 | -0.5098 |
| soglie: prezzo >= 5%, volume >= 3x | 17.21 | -8.228 | 0.02105 | [-0.92, 0.86] | -63.62 | 1531 | 0.03414 |
| soglie: prezzo >= 5%, volume >= 5x | 8.199 | -1.475 | 0.1078 | [-0.76, 0.96] | -47.57 | 774 | 0.2184 |
| soglie: prezzo >= 10%, volume >= 2x | 28.87 | -14.72 | -0.131 | [-1.11, 0.77] | -77.43 | 1672 | -0.1669 |
| soglie: prezzo >= 10%, volume >= 5x | 4.663 | -1.108 | 0.1064 | [-0.71, 0.98] | -54.25 | 652 | 0.24 |
| soglie: prezzo >= 15%, volume >= 2x | 38.95 | -13.95 | -0.227 | [-1.11, 0.64] | -67.61 | 1143 | -0.3666 |
| soglie: prezzo >= 15%, volume >= 3x | 22.97 | 2.167 | 0.2283 | [-0.64, 1.00] | -45.2 | 882 | 0.4173 |
| soglie: prezzo >= 15%, volume >= 5x | 8.03 | -3.783 | -0.01803 | [-0.89, 0.76] | -48.36 | 529 | -0.05972 |
| filtro BTC a 100 giorni | 29.53 | -5.523 | 0.02885 | [-0.94, 0.98] | -50.54 | 1069 | 0.0465 |
| stop a -10% | -0.8678 | -1.969 | 0.1186 | [-0.83, 0.95] | -61.95 | 1250 | 0.1402 |
| stop a -25% | 35.96 | 6.009 | 0.3475 | [-0.52, 1.17] | -64.27 | 1197 | 0.587 |
| costi doppi | 9.211 | -2.382 | 0.1347 | [-0.76, 1.05] | -63.91 | 1216 | 0.7643 |
| entrata un giorno dopo | 60.62 | -2.213 | 0.1346 | [-0.82, 1.10] | -47.61 | 1224 | 0.1792 |
| solo memecoin | 1.976 | 11.97 | 0.8068 | [-0.30, 1.49] | -16.52 | 130 | 4.814 |
| senza memecoin | 21.42 | 10.28 | 0.4431 | [-0.49, 1.23] | -49.12 | 1131 | 0.7098 |

Varianti positive fuori campione: **6 su 17**.

## H2 originale (3 giorni), anno per anno (%)
| anno | rendimento_% |
|---|---|
| 2018 | 0.3556 |
| 2019 | -3.329 |
| 2020 | -1.829 |
| 2021 | 149.2 |
| 2022 | -4.588 |
| 2023 | 24.04 |
| 2024 | 41.71 |
| 2025 | -43.73 |
| 2026 | 80.61 |

