# Ogni operazione del filtro di trend a 50 giorni su BTC, ETH e SOL (Binance, 2018-2026)

Answers "how many operations, and is it valid": round trips (entry when the close goes above its 50-day average,
exit when it goes below), their length, win rate, average and median result, profit concentration in the best
trades, per year, in sample (2018-2021) and out of sample (2022 - end). Costs 0.15% per side, as in the study.

## Riepilogo delle operazioni (andata e ritorno; ogni operazione = un acquisto e la sua vendita)
| moneta | periodo | operazioni | giorni_medi | giorni_mediani | vincenti_% | media_% | mediana_% | migliore_% | peggiore_% | profit_factor | quota_guadagno_dal_10%_migliore | rendimento_composto_% |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BTC | 2018-2021 (in campione) | 37 | 20.2 | 4 | 21.6 | 15 | -2.11 | 412.4 | -10.3 | 5.59 | 93.4 | 879.1 |
| BTC | 2022-fine (fuori campione) | 51 | 18 | 4 | 23.5 | 2.59 | -1.93 | 54 | -10.2 | 2.01 | 79.8 | 142.5 |
| BTC | tutto | 88 | 18.9 | 4 | 22.7 | 7.81 | -1.97 | 412.4 | -10.3 | 3.73 | 89.6 | 2275 |
| ETH | 2018-2021 (in campione) | 38 | 19.8 | 3 | 26.3 | 11.46 | -3.08 | 290.7 | -16.2 | 3.92 | 79.4 | 780.2 |
| ETH | 2022-fine (fuori campione) | 41 | 20.6 | 6 | 26.8 | 3.83 | -2.36 | 62.9 | -9.4 | 2.26 | 63.8 | 202.9 |
| ETH | tutto | 79 | 20.2 | 5 | 26.6 | 7.5 | -2.72 | 290.7 | -16.2 | 3.16 | 74.3 | 2566 |
| SOL | 2018-2021 (in campione) | 14 | 20.4 | 2 | 14.3 | 134.6 | -6.01 | 1502 | -29.9 | 17.98 | 75.3 | 2732 |
| SOL | 2022-fine (fuori campione) | 49 | 16.8 | 6 | 22.4 | 7.24 | -3.5 | 291.1 | -15.4 | 2.72 | 88 | 332 |
| SOL | tutto | 63 | 17.6 | 4 | 20.6 | 35.53 | -3.78 | 1502 | -29.9 | 8.05 | 95.9 | 1.214e+04 |
| BTC+ETH+SOL | 2018-2021 (in campione) | 89 | 20.1 | 3 | 22.5 | 32.3 | -2.8 | 1502 | -29.9 | 8.54 | 94.1 | 2.44e+05 |
| BTC+ETH+SOL | 2022-fine (fuori campione) | 141 | 18.3 | 5 | 24.1 | 4.57 | -2.16 | 291.1 | -15.4 | 2.39 | 80.6 | 3074 |
| BTC+ETH+SOL | tutto | 230 | 19 | 4 | 23.5 | 15.3 | -2.55 | 1502 | -29.9 | 5.17 | 90.8 | 7.747e+06 |

## Per anno
| moneta | anno | operazioni | vincenti | rendimento_composto_% |
|---|---|---|---|---|
| BTC | 2018 | 12 | 0 | -41.3 |
| BTC | 2019 | 10 | 2 | 80.5 |
| BTC | 2020 | 7 | 4 | 697.1 |
| BTC | 2021 | 8 | 2 | 15.9 |
| BTC | 2022 | 11 | 0 | -50.5 |
| BTC | 2023 | 7 | 4 | 134.6 |
| BTC | 2024 | 10 | 3 | 78.4 |
| BTC | 2025 | 13 | 3 | 3.1 |
| BTC | 2026 | 10 | 2 | 13.6 |
| ETH | 2018 | 5 | 1 | -36.2 |
| ETH | 2019 | 10 | 1 | 19 |
| ETH | 2020 | 11 | 4 | 663 |
| ETH | 2021 | 12 | 4 | 51.8 |
| ETH | 2022 | 8 | 1 | -30.8 |
| ETH | 2023 | 12 | 3 | 56.5 |
| ETH | 2024 | 11 | 3 | 20.3 |
| ETH | 2025 | 6 | 2 | 87.9 |
| ETH | 2026 | 4 | 2 | 23.7 |
| SOL | 2020 | 4 | 0 | -35.1 |
| SOL | 2021 | 10 | 2 | 4264 |
| SOL | 2022 | 8 | 1 | -29.5 |
| SOL | 2023 | 10 | 3 | 438.3 |
| SOL | 2024 | 10 | 3 | 33.2 |
| SOL | 2025 | 8 | 3 | 2.4 |
| SOL | 2026 | 13 | 1 | -16.6 |

## Le 10 operazioni migliori e le 10 peggiori fuori campione
| moneta | entrata | uscita | giorni | ret |
|---|---|---|---|---|
| SOL | 2023-09-30 | 2024-01-22 | 114 | 291.1 |
| SOL | 2023-01-03 | 2023-02-25 | 53 | 66.8 |
| ETH | 2025-07-06 | 2025-09-22 | 78 | 62.9 |
| BTC | 2023-09-28 | 2024-01-14 | 108 | 54 |
| SOL | 2024-02-07 | 2024-04-12 | 65 | 51 |
| BTC | 2024-10-11 | 2024-12-27 | 77 | 50.3 |
| SOL | 2024-10-11 | 2024-12-16 | 66 | 48.1 |
| BTC | 2024-02-06 | 2024-04-13 | 67 | 47.9 |
| ETH | 2023-10-21 | 2024-01-22 | 93 | 41.6 |
| ETH | 2024-02-06 | 2024-04-02 | 56 | 37.8 |
| SOL | 2026-03-23 | 2026-03-27 | 4 | -9.4 |
| ETH | 2022-02-15 | 2022-02-17 | 2 | -9.4 |
| BTC | 2022-07-27 | 2022-08-19 | 23 | -9.5 |
| BTC | 2022-02-28 | 2022-03-04 | 4 | -9.6 |
| BTC | 2022-09-12 | 2022-09-13 | 1 | -10.2 |
| SOL | 2024-07-15 | 2024-08-03 | 19 | -10.8 |
| SOL | 2022-09-12 | 2022-09-13 | 1 | -12.1 |
| SOL | 2022-11-04 | 2022-11-07 | 3 | -12.5 |
| SOL | 2024-08-08 | 2024-08-11 | 3 | -13.5 |
| SOL | 2025-10-01 | 2025-10-10 | 9 | -15.4 |

