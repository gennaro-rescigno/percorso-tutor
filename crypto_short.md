# Studio storico: scommettere sulla discesa (short sui perpetui), tenuta 1-3 giorni (Binance 2020-2026)

Pre-registrazione (testo originale):

```
(written before looking at any result):
  * universe each day: the 100 perpetuals with the highest 30-day average volume known the day before, >= 30 days
    of history (new listings have their own rule); quarterly contracts and stablecoins excluded;
  * short entry at the daily close (00:00 UTC) after the signal; exit at the close 1, 2 or 3 days later, or earlier
    at a +15% stop on the daily high (filled at the stop, or at the open if the day opens above it); a position
    cannot lose more than its collateral (no leverage: 1x);
  * funding: the real Binance funding of each day held is credited to the short when positive and charged when
    negative (on the notional at the previous close); days without funding data count as zero;
  * costs per side: 0.05% fee + slippage 0.05% (volume rank 1-30) or 0.20% (rank 31-100 and new listings);
  * rules (strongest signal first, at most 10 positions of 10% of equity):
      SH1 fade the hype: day return >= +10% and volume >= 3x its 30-day average;
      SH2 SH1 only while BTC is below its 50-day average;
      SS1 fade strength: the 5 best 3-day returns of the top 50;
      SN1 new listings: short at the close of the second day of trading (the first day is partial) when that day
          traded >= 20 million USDT;
      SF1 crowded longs: the day's funding >= 0.10% and a positive 3-day return;
      SB1 follow weakness: BTC below its 50-day average, coin below its 50-day average, the 5 worst 7-day
          returns of the top 50;
  * periods: 2020-2021 (in sample; perpetuals on most coins start in 2020) and 2022-01-01 .. end (out of sample);
  * every rule and hold with a positive out-of-sample result is re-run with: costs doubled, entry one day late,
    stop at +25%, funding ignored; plus its results year by year;
  * verdict "regge" only with: positive in both periods, out-of-sample 95% interval of the Sharpe above zero, and
    still positive with costs doubled and with the late entry.
```
Perpetui USDT: **918** (di cui 31 chiusi o delistati prima della fine), dati fino al 2026-10-31; con dati di funding: 918. Memecoin dell'elenco presenti: 36.
Giorni di contrattazione con dato di funding: **93.5%**; nelle 100 più scambiate funding giornaliero medio -0.0054%, mediano +0.0250%, giorni >= 0,10%: 9.4%.
- 2020-2021: delle 100 monete più scambiate, il 48.1% scende nei 3 giorni successivi (variazione media +1.68%, mediana +0.39%); tenerle tutte in parti uguali: +239.1% annuo, perdita massima -65%.
- 2022-fine: delle 100 monete più scambiate, il 53.9% scende nei 3 giorni successivi (variazione media -0.25%, mediana -0.67%); tenerle tutte in parti uguali: -44.6% annuo, perdita massima -95%.

## Le regole pre-registrate
| variante | IS_CAGR_% | OOS_CAGR_% | OOS_Sharpe | OOS_Sharpe_IC95 | OOS_maxDD_% | OOS_operazioni | OOS_vincenti_% | OOS_media_op_% | OOS_funding_medio_op_% | OOS_stop_% |
|---|---|---|---|---|---|---|---|---|---|---|
| SH1, 1 giorni | -41.77 | -37.78 | -1.691 | [-2.70, -0.61] | -94.28 | 2198 | 51.23 | -0.9667 | -0.185 | 25.48 |
| SH1, 2 giorni | -64.61 | -47.55 | -1.743 | [-2.79, -0.73] | -98.01 | 2142 | 48.37 | -1.32 | -0.2832 | 35.9 |
| SH1, 3 giorni | -68.62 | -43.27 | -1.296 | [-2.25, -0.25] | -96.52 | 2078 | 46.92 | -1.139 | -0.339 | 40.95 |
| SH2, 1 giorni | -6.295 | -5.841 | -0.2986 | [-1.15, 0.57] | -45.69 | 767 | 52.54 | -0.2966 | -0.3719 | 25.95 |
| SH2, 2 giorni | -9.666 | -8.415 | -0.3192 | [-1.12, 0.49] | -63.87 | 765 | 50.2 | -0.4152 | -0.575 | 35.16 |
| SH2, 3 giorni | -8.906 | -5.346 | -0.1191 | [-0.85, 0.56] | -56.63 | 755 | 47.68 | -0.1605 | -0.7053 | 40 |
| SS1, 1 giorni | -85.05 | -58.38 | -1.505 | [-2.52, -0.54] | -98.9 | 8815 | 52 | -0.4046 | -0.08807 | 12.98 |
| SS1, 2 giorni | -85.01 | -53.4 | -0.9549 | [-1.97, -0.04] | -98.69 | 6353 | 51.19 | -0.4367 | -0.1461 | 21.83 |
| SS1, 3 giorni | -87.94 | -44.7 | -0.5534 | [-1.52, 0.39] | -98 | 5164 | 50.14 | -0.3396 | -0.1967 | 27.83 |
| SN1, 1 giorni | 2.282 | 1.263 | 0.1601 | [-0.69, 0.99] | -22.73 | 526 | 54.94 | 0.1994 | -0.1458 | 25.86 |
| SN1, 2 giorni | 4.909 | 0.5685 | 0.1184 | [-0.82, 1.06] | -35.91 | 526 | 51.71 | 0.1805 | -0.1963 | 36.31 |
| SN1, 3 giorni | 11.04 | 3.683 | 0.2818 | [-0.66, 1.09] | -42.57 | 526 | 49.05 | 0.5004 | -0.2078 | 41.44 |
| SF1, 1 giorni | -64.68 | -37.45 | -1.401 | [-2.57, -0.33] | -89.64 | 2612 | 49.85 | -0.7831 | 0.1231 | 20.83 |
| SF1, 2 giorni | -47.71 | -31.1 | -0.935 | [-1.86, -0.05] | -84.41 | 1830 | 48.42 | -0.8345 | 0.197 | 32.62 |
| SF1, 3 giorni | -47.61 | -26.03 | -0.6746 | [-1.78, 0.34] | -80.02 | 1562 | 46.22 | -0.7327 | 0.244 | 39.88 |
| SB1, 1 giorni | -25.82 | -30.38 | -0.8327 | [-1.60, -0.13] | -88.34 | 4230 | 47.87 | -0.3354 | -0.05615 | 8.085 |
| SB1, 2 giorni | -33.13 | -25.33 | -0.4935 | [-1.27, 0.19] | -84.83 | 2762 | 49.17 | -0.356 | -0.09795 | 14.48 |
| SB1, 3 giorni | -28.66 | -23.19 | -0.3545 | [-1.10, 0.36] | -86.12 | 2221 | 49.17 | -0.3335 | -0.1331 | 20.71 |

Positive fuori campione: **3 su 18**.

## Verifiche sulle combinazioni positive fuori campione

### SN1, 1 giorni
| variante | IS_CAGR_% | OOS_CAGR_% | OOS_Sharpe | OOS_Sharpe_IC95 | OOS_maxDD_% | OOS_operazioni | OOS_vincenti_% | OOS_media_op_% | OOS_funding_medio_op_% | OOS_stop_% |
|---|---|---|---|---|---|---|---|---|---|---|
| SN1, 1 giorni | 2.282 | 1.263 | 0.1601 | [-0.69, 0.99] | -22.73 | 526 | 54.94 | 0.1994 | -0.1458 | 25.86 |
| SN1, 1 giorni: costi doppi | 0.4439 | -4.085 | -0.2389 | [-1.14, 0.65] | -29.2 | 526 | 52.66 | -0.2985 | -0.1458 | 25.86 |
| SN1, 1 giorni: entrata un giorno dopo | 2.313 | -4.266 | -0.2984 | [-1.08, 0.59] | -36.49 | 526 | 49.62 | -0.3328 | -0.06854 | 23.76 |
| SN1, 1 giorni: stop a +25% | 0.3399 | -0.1909 | 0.06409 | [-0.81, 0.98] | -32.07 | 526 | 57.79 | 0.09007 | -0.1991 | 13.69 |
| SN1, 1 giorni: senza funding | 2.129 | 2.875 | 0.276 | [-0.59, 1.11] | -21.44 | 526 | 55.51 | 0.3452 | 0 | 25.86 |

Anno per anno (%): 2020 +9.5, 2021 -4.4, 2022 +4.0, 2023 -2.9, 2024 +4.0, 2025 +12.8, 2026 -10.3
Fuori campione, solo descrittivo: 33 operazioni su memecoin (media -0.01%), 493 sulle altre (media +0.21%).

### SN1, 2 giorni
| variante | IS_CAGR_% | OOS_CAGR_% | OOS_Sharpe | OOS_Sharpe_IC95 | OOS_maxDD_% | OOS_operazioni | OOS_vincenti_% | OOS_media_op_% | OOS_funding_medio_op_% | OOS_stop_% |
|---|---|---|---|---|---|---|---|---|---|---|
| SN1, 2 giorni | 4.909 | 0.5685 | 0.1184 | [-0.82, 1.06] | -35.91 | 526 | 51.71 | 0.1805 | -0.1963 | 36.31 |
| SN1, 2 giorni: costi doppi | 3.031 | -4.748 | -0.197 | [-1.12, 0.62] | -42.37 | 526 | 50.38 | -0.3174 | -0.1963 | 36.31 |
| SN1, 2 giorni: entrata un giorno dopo | 11.89 | -0.6706 | 0.03732 | [-0.76, 0.80] | -36.09 | 526 | 49.05 | 0.05051 | -0.09047 | 33.46 |
| SN1, 2 giorni: stop a +25% | 2.678 | -2.206 | -0.008554 | [-0.96, 0.98] | -49.92 | 526 | 57.22 | -0.02079 | -0.2627 | 21.29 |
| SN1, 2 giorni: senza funding | 4.683 | 2.729 | 0.2426 | [-0.63, 1.09] | -33.36 | 526 | 51.9 | 0.3768 | 0 | 36.31 |

Anno per anno (%): 2020 +16.5, 2021 -5.5, 2022 +8.7, 2023 -11.7, 2024 +11.7, 2025 -0.8, 2026 -3.4
Fuori campione, solo descrittivo: 33 operazioni su memecoin (media -0.56%), 493 sulle altre (media +0.23%).

### SN1, 3 giorni
| variante | IS_CAGR_% | OOS_CAGR_% | OOS_Sharpe | OOS_Sharpe_IC95 | OOS_maxDD_% | OOS_operazioni | OOS_vincenti_% | OOS_media_op_% | OOS_funding_medio_op_% | OOS_stop_% |
|---|---|---|---|---|---|---|---|---|---|---|
| SN1, 3 giorni | 11.04 | 3.683 | 0.2818 | [-0.66, 1.09] | -42.57 | 526 | 49.05 | 0.5004 | -0.2078 | 41.44 |
| SN1, 3 giorni: costi doppi | 9.068 | -1.789 | 0.007785 | [-0.82, 0.87] | -47.7 | 526 | 48.48 | 0.00343 | -0.2078 | 41.44 |
| SN1, 3 giorni: entrata un giorno dopo | 12.77 | -0.6077 | 0.06189 | [-0.67, 0.89] | -39.48 | 526 | 49.43 | 0.08339 | -0.1229 | 38.59 |
| SN1, 3 giorni: stop a +25% | 10.3 | -0.3512 | 0.103 | [-0.87, 1.07] | -56.24 | 526 | 55.13 | 0.2245 | -0.2918 | 26.81 |
| SN1, 3 giorni: senza funding | 10.77 | 6.038 | 0.3956 | [-0.44, 1.25] | -40.31 | 526 | 49.43 | 0.7082 | 0 | 41.44 |

Anno per anno (%): 2020 +25.1, 2021 -1.4, 2022 +10.8, 2023 -3.8, 2024 +20.4, 2025 -0.4, 2026 -6.8
Fuori campione, solo descrittivo: 33 operazioni su memecoin (media +0.64%), 493 sulle altre (media +0.49%).

## Verdetto
- SN1, 1 giorni: **non regge**
- SN1, 2 giorni: **non regge**
- SN1, 3 giorni: **non regge**
