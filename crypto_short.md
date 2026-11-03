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
- 2020-2021: delle 100 monete più scambiate, il 48.1% scende nei 3 giorni successivi (variazione media +1.68%, mediana +0.39%); tenerle tutte in parti uguali: +239.1% annuo, perdita massima -65%.
- 2022-fine: delle 100 monete più scambiate, il 53.9% scende nei 3 giorni successivi (variazione media -0.25%, mediana -0.67%); tenerle tutte in parti uguali: -44.6% annuo, perdita massima -95%.

## Le regole pre-registrate
| variante | IS_CAGR_% | OOS_CAGR_% | OOS_Sharpe | OOS_Sharpe_IC95 | OOS_maxDD_% | OOS_operazioni | OOS_vincenti_% | OOS_media_op_% | OOS_funding_medio_op_% | OOS_stop_% |
|---|---|---|---|---|---|---|---|---|---|---|
| SH1, 1 giorni | -44.48 | -32.46 | -1.354 | [-2.38, -0.25] | -91.6 | 2197 | 51.71 | -0.785 | 0 | 25.49 |
| SH1, 2 giorni | -67.2 | -40.64 | -1.352 | [-2.43, -0.33] | -96.43 | 2142 | 49.25 | -1.037 | 0 | 35.9 |
| SH1, 3 giorni | -71.31 | -34.57 | -0.9046 | [-1.87, 0.16] | -93.18 | 2078 | 47.21 | -0.8003 | 0 | 40.95 |
| SH2, 1 giorni | -6.052 | -0.1457 | 0.07107 | [-0.73, 0.87] | -33.5 | 767 | 53.59 | 0.07531 | 0 | 25.95 |
| SH2, 2 giorni | -9.383 | 0.1981 | 0.1147 | [-0.67, 0.87] | -48.29 | 765 | 52.16 | 0.1598 | 0 | 35.16 |
| SH2, 3 giorni | -8.614 | 5.424 | 0.3393 | [-0.40, 0.99] | -38.92 | 755 | 48.61 | 0.5449 | 0 | 40 |
| SS1, 1 giorni | -86.33 | -51.21 | -1.173 | [-2.17, -0.23] | -97.71 | 8815 | 52.32 | -0.3165 | 0 | 12.98 |
| SS1, 2 giorni | -86.75 | -43.64 | -0.6358 | [-1.61, 0.27] | -96.89 | 6353 | 51.36 | -0.2905 | 0 | 21.83 |
| SS1, 3 giorni | -89.68 | -31.98 | -0.2401 | [-1.17, 0.68] | -94.87 | 5164 | 50.37 | -0.1429 | 0 | 27.83 |
| SN1, 1 giorni | 2.129 | 2.875 | 0.276 | [-0.56, 1.13] | -21.44 | 526 | 55.51 | 0.3452 | 0 | 25.86 |
| SN1, 2 giorni | 4.683 | 2.729 | 0.2426 | [-0.69, 1.14] | -33.36 | 526 | 51.9 | 0.3768 | 0 | 36.31 |
| SN1, 3 giorni | 10.77 | 6.038 | 0.3956 | [-0.53, 1.20] | -40.31 | 526 | 49.43 | 0.7082 | 0 | 41.44 |
| SF1, 1 giorni | 0 | 0 |  | [0.00, 0.00] | 0 | 0 |  |  |  |  |
| SF1, 2 giorni | 0 | 0 |  | [0.00, 0.00] | 0 | 0 |  |  |  |  |
| SF1, 3 giorni | 0 | 0 |  | [0.00, 0.00] | 0 | 0 |  |  |  |  |
| SB1, 1 giorni | -26.54 | -26.89 | -0.6931 | [-1.50, 0.03] | -85.21 | 4230 | 48.35 | -0.2792 | 0 | 8.085 |
| SB1, 2 giorni | -34.03 | -21.03 | -0.3592 | [-1.12, 0.31] | -80.12 | 2762 | 49.6 | -0.258 | 0 | 14.48 |
| SB1, 3 giorni | -29.68 | -18.35 | -0.2205 | [-0.98, 0.49] | -81.9 | 2221 | 49.57 | -0.2005 | 0 | 20.71 |

Positive fuori campione: **5 su 18**.

## Verifiche sulle combinazioni positive fuori campione

### SH2, 2 giorni
| variante | IS_CAGR_% | OOS_CAGR_% | OOS_Sharpe | OOS_Sharpe_IC95 | OOS_maxDD_% | OOS_operazioni | OOS_vincenti_% | OOS_media_op_% | OOS_funding_medio_op_% | OOS_stop_% |
|---|---|---|---|---|---|---|---|---|---|---|
| SH2, 2 giorni | -9.383 | 0.1981 | 0.1147 | [-0.67, 0.87] | -48.29 | 765 | 52.16 | 0.1598 | 0 | 35.16 |
| SH2, 2 giorni: costi doppi | -12.92 | -6.567 | -0.212 | [-0.95, 0.56] | -59.24 | 765 | 50.59 | -0.2802 | 0 | 35.16 |
| SH2, 2 giorni: entrata un giorno dopo | -10.58 | -7.423 | -0.2998 | [-1.20, 0.51] | -54.84 | 711 | 50.49 | -0.3688 | 0 | 33.33 |
| SH2, 2 giorni: stop a +25% | -3.535 | -3.316 | -0.005916 | [-0.77, 0.73] | -54.91 | 739 | 57.92 | 0.009693 | 0 | 22.33 |
| SH2, 2 giorni: senza funding | -9.383 | 0.1981 | 0.1147 | [-0.65, 0.82] | -48.29 | 765 | 52.16 | 0.1598 | 0 | 35.16 |

Anno per anno (%): 2020 +0.6, 2021 -18.4, 2022 +61.2, 2023 +0.4, 2024 -18.3, 2025 -10.4, 2026 -14.7
Fuori campione, solo descrittivo: 34 operazioni su memecoin (media -1.18%), 731 sulle altre (media +0.22%).

### SH2, 3 giorni
| variante | IS_CAGR_% | OOS_CAGR_% | OOS_Sharpe | OOS_Sharpe_IC95 | OOS_maxDD_% | OOS_operazioni | OOS_vincenti_% | OOS_media_op_% | OOS_funding_medio_op_% | OOS_stop_% |
|---|---|---|---|---|---|---|---|---|---|---|
| SH2, 3 giorni | -8.614 | 5.424 | 0.3393 | [-0.40, 0.99] | -38.92 | 755 | 48.61 | 0.5449 | 0 | 40 |
| SH2, 3 giorni: costi doppi | -12.12 | -1.607 | 0.05169 | [-0.75, 0.75] | -49.27 | 755 | 47.42 | 0.1048 | 0 | 40 |
| SH2, 3 giorni: entrata un giorno dopo | -19.16 | -6.703 | -0.1953 | [-1.16, 0.67] | -57.75 | 710 | 48.17 | -0.273 | 0 | 39.15 |
| SH2, 3 giorni: stop a +25% | -3.662 | 2.492 | 0.2288 | [-0.43, 0.87] | -44.85 | 717 | 54.95 | 0.4769 | 0 | 26.36 |
| SH2, 3 giorni: senza funding | -8.614 | 5.424 | 0.3393 | [-0.43, 0.99] | -38.92 | 755 | 48.61 | 0.5449 | 0 | 40 |

Anno per anno (%): 2020 +0.3, 2021 -16.8, 2022 +57.3, 2023 +0.2, 2024 -21.5, 2025 -9.7, 2026 +15.6
Fuori campione, solo descrittivo: 32 operazioni su memecoin (media -3.14%), 723 sulle altre (media +0.71%).

### SN1, 1 giorni
| variante | IS_CAGR_% | OOS_CAGR_% | OOS_Sharpe | OOS_Sharpe_IC95 | OOS_maxDD_% | OOS_operazioni | OOS_vincenti_% | OOS_media_op_% | OOS_funding_medio_op_% | OOS_stop_% |
|---|---|---|---|---|---|---|---|---|---|---|
| SN1, 1 giorni | 2.129 | 2.875 | 0.276 | [-0.56, 1.13] | -21.44 | 526 | 55.51 | 0.3452 | 0 | 25.86 |
| SN1, 1 giorni: costi doppi | 0.2935 | -2.557 | -0.1218 | [-0.97, 0.70] | -25.49 | 526 | 53.04 | -0.1527 | 0 | 25.86 |
| SN1, 1 giorni: entrata un giorno dopo | 2.078 | -3.549 | -0.2369 | [-1.02, 0.65] | -34.98 | 526 | 49.81 | -0.2642 | 0 | 23.76 |
| SN1, 1 giorni: stop a +25% | 0.04832 | 1.985 | 0.2048 | [-0.73, 1.17] | -29.9 | 526 | 58.37 | 0.2891 | 0 | 13.69 |
| SN1, 1 giorni: senza funding | 2.129 | 2.875 | 0.276 | [-0.58, 1.10] | -21.44 | 526 | 55.51 | 0.3452 | 0 | 25.86 |

Anno per anno (%): 2020 +9.7, 2021 -4.9, 2022 +4.2, 2023 -1.3, 2024 +3.6, 2025 +17.4, 2026 -8.4
Fuori campione, solo descrittivo: 33 operazioni su memecoin (media -0.12%), 493 sulle altre (media +0.38%).

### SN1, 2 giorni
| variante | IS_CAGR_% | OOS_CAGR_% | OOS_Sharpe | OOS_Sharpe_IC95 | OOS_maxDD_% | OOS_operazioni | OOS_vincenti_% | OOS_media_op_% | OOS_funding_medio_op_% | OOS_stop_% |
|---|---|---|---|---|---|---|---|---|---|---|
| SN1, 2 giorni | 4.683 | 2.729 | 0.2426 | [-0.69, 1.14] | -33.36 | 526 | 51.9 | 0.3768 | 0 | 36.31 |
| SN1, 2 giorni: costi doppi | 2.809 | -2.7 | -0.07296 | [-0.92, 0.85] | -38.55 | 526 | 51.14 | -0.1211 | 0 | 36.31 |
| SN1, 2 giorni: entrata un giorno dopo | 11.52 | 0.3161 | 0.09936 | [-0.66, 0.84] | -34.15 | 526 | 49.24 | 0.141 | 0 | 33.46 |
| SN1, 2 giorni: stop a +25% | 2.152 | 0.6175 | 0.132 | [-0.90, 1.15] | -47.35 | 526 | 57.79 | 0.242 | 0 | 21.29 |
| SN1, 2 giorni: senza funding | 4.683 | 2.729 | 0.2426 | [-0.66, 1.13] | -33.36 | 526 | 51.9 | 0.3768 | 0 | 36.31 |

Anno per anno (%): 2020 +16.9, 2021 -6.3, 2022 +9.1, 2023 -10.1, 2024 +11.0, 2025 +5.7, 2026 -1.0
Fuori campione, solo descrittivo: 33 operazioni su memecoin (media -0.76%), 493 sulle altre (media +0.45%).

### SN1, 3 giorni
| variante | IS_CAGR_% | OOS_CAGR_% | OOS_Sharpe | OOS_Sharpe_IC95 | OOS_maxDD_% | OOS_operazioni | OOS_vincenti_% | OOS_media_op_% | OOS_funding_medio_op_% | OOS_stop_% |
|---|---|---|---|---|---|---|---|---|---|---|
| SN1, 3 giorni | 10.77 | 6.038 | 0.3956 | [-0.53, 1.20] | -40.31 | 526 | 49.43 | 0.7082 | 0 | 41.44 |
| SN1, 3 giorni: costi doppi | 8.805 | 0.4436 | 0.1213 | [-0.85, 0.96] | -45.17 | 526 | 48.67 | 0.2112 | 0 | 41.44 |
| SN1, 3 giorni: entrata un giorno dopo | 12.39 | 0.7297 | 0.1328 | [-0.65, 0.90] | -37.61 | 526 | 50 | 0.2063 | 0 | 38.59 |
| SN1, 3 giorni: stop a +25% | 9.643 | 2.855 | 0.2372 | [-0.78, 1.19] | -54.02 | 526 | 56.08 | 0.5163 | 0 | 26.81 |
| SN1, 3 giorni: senza funding | 10.77 | 6.038 | 0.3956 | [-0.50, 1.24] | -40.31 | 526 | 49.43 | 0.7082 | 0 | 41.44 |

Anno per anno (%): 2020 +25.7, 2021 -2.3, 2022 +11.3, 2023 -2.1, 2024 +19.0, 2025 +7.0, 2026 -4.4
Fuori campione, solo descrittivo: 33 operazioni su memecoin (media +0.36%), 493 sulle altre (media +0.73%).

## Verdetto
- SH2, 2 giorni: **non regge**
- SH2, 3 giorni: **non regge**
- SN1, 1 giorni: **non regge**
- SN1, 2 giorni: **non regge**
- SN1, 3 giorni: **non regge**
