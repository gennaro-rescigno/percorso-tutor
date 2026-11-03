# Studio storico: ciclo di vita dei lanci e regole d'ingresso sulla curva (loopholetape, set-ott 2026)

Pre-registrazione (scritta prima di vedere i risultati, testo originale):

```
(written before looking at any result; do not tune after reading the output):
  * universe: classic launches only (quoted in SOL, not mayhem), outcome settled, row before migration, not a
    repaired row, recorder lag <= 10 s (or unknown), decoder complete;
  * one trade per mint: the first row (the bot scans once a minute) that meets the rule;
  * price on the curve from the real SOL reserve: virtual SOL = 30 + real, price ~ (30 + real)^2 (constant
    product with 30 SOL virtual, verified on our own chain fixtures);
  * costs: entry price 3% worse than the row (latency), pump.fun fee 1.25% on buy and on sell, 0.001 SOL priority
    fees per round trip on a 0.1 SOL position (1%); a graduation exit sells in the new pool with a haircut H
    (base 30%, sensitivity 10% and 50%);
  * exits: X1 hold until graduation (sell in the pool, haircut H) or until the curve dies (sell at the terminal
    reserve); X2 take profit on the curve at 60 SOL of real reserve (if the curve's peak reached it), otherwise
    as X1 for a dead curve;
  * statistics: mean net return per trade with a 95% bootstrap interval (resampling mints), p-value of mean <= 0,
    Benjamini-Hochberg over all strategy x exit tests; the verdict needs BOTH halves of the period positive;
  * known approximation (stated in the report): X2 uses the peak of the whole path, so a peak reached before the
    entry row would count as hit; measured as the share of entries whose own earlier rows already exceeded 60.
```

## 1. Cosa succede ai lanci

### 31 ago - 26 set (decoder incompleto: acquisti sottostimati): 541,752 lanci classici (SOL, non mayhem)
- diplomati: 3.56% · rug (regola loopholetape, sui risolti): 60.4% · rug entro 5 min: 52.4%
- il creatore vende: 66.6% dei lanci; tempo mediano alla prima vendita 22 s (25° 3 s, 75° 179 s); entro 60 s nel 40.5% dei lanci
- tempo al diploma: mediana 0.0 min; entro 1 min 75.6%, entro 10 min 89.3%, oltre 1 ora 3.1%
- picco della curva (SOL reali): mediana 1.30; >= 5 SOL 34.9%, >= 20 SOL 12.0%, >= 60 SOL 4.52%

Per acquisto iniziale del creatore (SOL):
| acquisto_creatore | lanci | diploma_% | rug_% | creatore_vende_<60s_% |
|---|---|---|---|---|
| 0 | 98446 | 0.8868 | 9.631 | 6.895 |
| <0.5 | 195660 | 2.158 | 51.64 | 25.42 |
| 0.5-1 | 66521 | 1.643 | 83.31 | 52.45 |
| 1-2 | 55517 | 1.639 | 89.65 | 61.79 |
| 2-5 | 94274 | 1.961 | 96.61 | 82.54 |
| >5 | 31334 | 33.03 | 66.48 | 50.23 |

Per fascia oraria UTC (3 ore):
| ora_UTC | lanci | diploma_% | rug_% | creatore_vende_<60s_% |
|---|---|---|---|---|
| 0 | 70594 | 3.479 | 58.88 | 39.6 |
| 3 | 53484 | 4.476 | 59.47 | 41.15 |
| 6 | 39770 | 5.461 | 59.04 | 38.98 |
| 9 | 46306 | 4.285 | 58.02 | 38.32 |
| 12 | 71294 | 3.434 | 58.98 | 42.14 |
| 15 | 83418 | 3.138 | 61.72 | 41.08 |
| 18 | 90533 | 3.008 | 63 | 41.23 |
| 21 | 86353 | 2.899 | 61.43 | 39.84 |

Per metadati (uri):
| uri | lanci | diploma_% | rug_% | creatore_vende_<60s_% |
|---|---|---|---|---|
| altro | 58 | 0 | 22.41 | 1.724 |
| altro http | 203095 | 1.367 | 66.24 | 58.11 |
| arweave | 515 | 19.61 | 48.37 | 24.27 |
| ipfs | 333620 | 4.879 | 56.89 | 29.8 |
| nessuno | 4464 | 3.203 | 59.65 | 38.33 |

Copie (stesso nome normalizzato già usato prima nel dataset):
| copia | lanci | diploma_% | rug_% | creatore_vende_<60s_% |
|---|---|---|---|---|
| originale | 180599 | 2.32 | 59.14 | 33.02 |
| 2a | 57773 | 2.669 | 63.78 | 42.38 |
| 3a-6a | 99090 | 2.732 | 61.27 | 43.95 |
| oltre | 200062 | 5.382 | 59.94 | 44.73 |

Per wallet bundle nei primi 10 s (solo lanci campionati, popolazione distorta: vedi KI-01):
| bundle | lanci | diploma_% | rug_% | creatore_vende_<60s_% |
|---|---|---|---|---|
| 0 | 87611 | 1.112 | 70.48 | 51.13 |
| 1-2 | 73424 | 2.206 | 85 | 60 |
| 3-5 | 34087 | 3.045 | 96.55 | 84.52 |
| 6-10 | 3406 | 6.283 | 94.4 | 79.15 |
| >10 | 470 | 21.28 | 79.11 | 25.32 |

Per storico del creatore (lanci precedenti):
| lanci_precedenti | lanci | diploma_% | rug_% | creatore_vende_<60s_% |
|---|---|---|---|---|
| primo | 63989 | 3.027 | 76.55 | 50.2 |
| 1-5 | 26008 | 1.88 | 72.28 | 47.65 |
| 6-50 | 36591 | 1.681 | 79.11 | 61.17 |
| >50 | 72410 | 1.25 | 88.17 | 73.99 |


### 27 set - 27 ott (decoder completo): 814,165 lanci classici (SOL, non mayhem)
- diplomati: 2.79% · rug (regola loopholetape, sui risolti): 61.6% · rug entro 5 min: 56.7%
- il creatore vende: 67.6% dei lanci; tempo mediano alla prima vendita 16 s (25° 3 s, 75° 120 s); entro 60 s nel 44.2% dei lanci
- tempo al diploma: mediana 0.0 min; entro 1 min 66.7%, entro 10 min 85.8%, oltre 1 ora 4.4%
- picco della curva (SOL reali): mediana 1.60; >= 5 SOL 35.0%, >= 20 SOL 10.9%, >= 60 SOL 3.47%

Per acquisto iniziale del creatore (SOL):
| acquisto_creatore | lanci | diploma_% | rug_% | creatore_vende_<60s_% |
|---|---|---|---|---|
| 0 | 182149 | 0.5424 | 8.371 | 4.551 |
| <0.5 | 257384 | 1.581 | 57.23 | 31.59 |
| 0.5-1 | 113733 | 2.029 | 87.61 | 59.47 |
| 1-2 | 89933 | 1.18 | 93.08 | 66.39 |
| 2-5 | 121669 | 2.031 | 97.46 | 89.15 |
| >5 | 49297 | 23.93 | 76.72 | 70.5 |

Per fascia oraria UTC (3 ore):
| ora_UTC | lanci | diploma_% | rug_% | creatore_vende_<60s_% |
|---|---|---|---|---|
| 0 | 97922 | 2.92 | 58.73 | 40.3 |
| 3 | 80013 | 3.174 | 58.45 | 40.88 |
| 6 | 69281 | 3.18 | 58.16 | 40.64 |
| 9 | 77239 | 2.65 | 56.78 | 41.02 |
| 12 | 107262 | 2.637 | 62.46 | 47.08 |
| 15 | 130780 | 2.613 | 64.04 | 46.6 |
| 18 | 134006 | 2.665 | 65.27 | 47.14 |
| 21 | 117662 | 2.743 | 63.4 | 45.52 |

Per metadati (uri):
| uri | lanci | diploma_% | rug_% | creatore_vende_<60s_% |
|---|---|---|---|---|
| altro | 121 | 0 | 37.82 | 28.1 |
| altro http | 301410 | 1.193 | 66.11 | 60.55 |
| arweave | 1366 | 4.832 | 64.16 | 44.22 |
| ipfs | 510819 | 3.725 | 58.92 | 34.65 |
| nessuno | 449 | 0.6682 | 38.08 | 12.47 |

Copie (stesso nome normalizzato già usato prima nel dataset):
| copia | lanci | diploma_% | rug_% | creatore_vende_<60s_% |
|---|---|---|---|---|
| originale | 213608 | 1.58 | 59.82 | 37.62 |
| 2a | 68166 | 1.875 | 59.05 | 39.5 |
| 3a-6a | 132960 | 1.996 | 61 | 44.2 |
| oltre | 392307 | 3.889 | 62.88 | 48.31 |

Per wallet bundle nei primi 10 s (solo lanci campionati, popolazione distorta: vedi KI-01):
| bundle | lanci | diploma_% | rug_% | creatore_vende_<60s_% |
|---|---|---|---|---|
| 0 | 365362 | 2.774 | 36.81 | 21.72 |
| 1-2 | 194666 | 0.8368 | 74.23 | 50.03 |
| 3-5 | 145482 | 2.924 | 92.92 | 77.4 |
| 6-10 | 54950 | 6.974 | 92.78 | 77.58 |
| >10 | 12838 | 13.9 | 85.81 | 70.06 |

Per storico del creatore (lanci precedenti):
| lanci_precedenti | lanci | diploma_% | rug_% | creatore_vende_<60s_% |
|---|---|---|---|---|
| primo | 281960 | 6.161 | 60.61 | 39.22 |
| 1-5 | 120271 | 1.058 | 53.42 | 31.94 |
| 6-50 | 125123 | 0.7113 | 60.95 | 42.7 |
| >50 | 245944 | 0.8539 | 66.61 | 56.32 |


## 2. Regole d'ingresso sulla curva (una operazione per token, costi inclusi)
Righe utilizzabili: 2,209,856 (istantanee al minuto) di 547,350 token classici.
| regola | uscita | taglio_pool | n | media_% | IC95_basso_% | IC95_alto_% | p | mediana_% | vincenti_% | diplomati_% | 1a_metà_media_% | 1a_metà_n | 2a_metà_media_% | 2a_metà_n | q_BH | verdetto |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S0 qualsiasi riga < 5 min | X1 | 0.1 | 542683 | -13.63 | -13.78 | -13.48 | 1 | -10.06 | 1.435 | 1.453 | -12.52 | 297849 | -14.99 | 244834 | 1 | non dimostrata |
| S0 qualsiasi riga < 5 min | X1 | 0.3 | 542683 | -14.98 | -15.1 | -14.86 | 1 | -10.11 | 1.287 | 1.453 | -13.96 | 297849 | -16.21 | 244834 | 1 | non dimostrata |
| S0 qualsiasi riga < 5 min | X1 | 0.5 | 542683 | -16.33 | -16.41 | -16.24 | 1 | -10.18 | 1.136 | 1.453 | -15.41 | 297849 | -17.44 | 244834 | 1 | non dimostrata |
| S0 qualsiasi riga < 5 min | X2 | 0.3 | 542683 | -13.24 | -13.36 | -13.11 | 1 | -9.879 | 2.063 | 1.453 | -12.22 | 297849 | -14.47 | 244834 | 1 | non dimostrata |
| S1 1-2 min, riserva 0.5-10, senza segnali negativi | X1 | 0.1 | 13399 | -16.1 | -17.34 | -14.87 | 1 | -20.46 | 0.8135 | 0.7986 | -15.01 | 8194 | -17.81 | 5205 | 1 | non dimostrata |
| S1 1-2 min, riserva 0.5-10, senza segnali negativi | X1 | 0.3 | 13399 | -17.67 | -18.58 | -16.66 | 1 | -20.46 | 0.8135 | 0.7986 | -16.7 | 8194 | -19.19 | 5205 | 1 | non dimostrata |
| S1 1-2 min, riserva 0.5-10, senza segnali negativi | X1 | 0.5 | 13399 | -19.24 | -19.88 | -18.57 | 1 | -20.46 | 0.8135 | 0.7986 | -18.39 | 8194 | -20.58 | 5205 | 1 | non dimostrata |
| S1 1-2 min, riserva 0.5-10, senza segnali negativi | X2 | 0.3 | 13399 | -17.25 | -18.13 | -16.27 | 1 | -20.42 | 1.015 | 0.7986 | -16.39 | 8194 | -18.61 | 5205 | 1 | non dimostrata |
| S2 2-5 min, riserva 0.5-10, senza segnali negativi | X1 | 0.1 | 12435 | -15.82 | -16.94 | -14.54 | 1 | -18.61 | 0.6755 | 0.6594 | -15.06 | 7450 | -16.96 | 4985 | 1 | non dimostrata |
| S2 2-5 min, riserva 0.5-10, senza segnali negativi | X1 | 0.3 | 12435 | -17.15 | -18.06 | -16.23 | 1 | -18.61 | 0.6755 | 0.6594 | -16.43 | 7450 | -18.22 | 4985 | 1 | non dimostrata |
| S2 2-5 min, riserva 0.5-10, senza segnali negativi | X1 | 0.5 | 12435 | -18.47 | -19.09 | -17.82 | 1 | -18.61 | 0.6755 | 0.6594 | -17.79 | 7450 | -19.49 | 4985 | 1 | non dimostrata |
| S2 2-5 min, riserva 0.5-10, senza segnali negativi | X2 | 0.3 | 12435 | -16.75 | -17.61 | -15.85 | 1 | -18.57 | 0.8444 | 0.6594 | -16.08 | 7450 | -17.75 | 4985 | 1 | non dimostrata |
| S3 30 s-5 min, >= 20 acquisti, riserva < 10, senza segnali | X1 | 0.1 | 6261 | -17.04 | -19.27 | -14.81 | 1 | -30.02 | 1.485 | 1.469 | -16.49 | 4299 | -18.24 | 1962 | 1 | non dimostrata |
| S3 30 s-5 min, >= 20 acquisti, riserva < 10, senza segnali | X1 | 0.3 | 6261 | -19.73 | -21.44 | -17.92 | 1 | -30.02 | 1.485 | 1.469 | -19 | 4299 | -21.34 | 1962 | 1 | non dimostrata |
| S3 30 s-5 min, >= 20 acquisti, riserva < 10, senza segnali | X1 | 0.5 | 6261 | -22.43 | -23.68 | -21.25 | 1 | -30.02 | 1.485 | 1.469 | -21.51 | 4299 | -24.45 | 1962 | 1 | non dimostrata |
| S3 30 s-5 min, >= 20 acquisti, riserva < 10, senza segnali | X2 | 0.3 | 6261 | -19.13 | -20.72 | -17.37 | 1 | -29.84 | 1.853 | 1.469 | -18.06 | 4299 | -21.48 | 1962 | 1 | non dimostrata |
| S4 S3 + il creatore detiene ancora >= 1% | X1 | 0.1 | 3723 | -18.8 | -21.84 | -15.32 | 1 | -33.5 | 1.692 | 1.692 | -17.44 | 2372 | -21.18 | 1351 | 1 | non dimostrata |
| S4 S3 + il creatore detiene ancora >= 1% | X1 | 0.3 | 3723 | -21.9 | -24.25 | -19.32 | 1 | -33.5 | 1.692 | 1.692 | -20.55 | 2372 | -24.28 | 1351 | 1 | non dimostrata |
| S4 S3 + il creatore detiene ancora >= 1% | X1 | 0.5 | 3723 | -25.01 | -26.62 | -23.2 | 1 | -33.5 | 1.692 | 1.692 | -23.66 | 2372 | -27.37 | 1351 | 1 | non dimostrata |
| S4 S3 + il creatore detiene ancora >= 1% | X2 | 0.3 | 3723 | -21.06 | -23.3 | -18.72 | 1 | -33.37 | 2.149 | 1.692 | -19.31 | 2372 | -24.13 | 1351 | 1 | non dimostrata |
| S5 S3 + creatore con un diploma precedente | X1 | 0.1 | 79 | -19.88 | -32.8 | 3.538 | 0.9285 | -31.99 | 1.266 | 1.266 | -6.893 | 37 | -31.33 | 42 | 1 | non dimostrata |
| S5 S3 + creatore con un diploma precedente | X1 | 0.3 | 79 | -22.56 | -32.53 | -4.738 | 0.983 | -31.99 | 1.266 | 1.266 | -12.6 | 37 | -31.33 | 42 | 1 | non dimostrata |
| S5 S3 + creatore con un diploma precedente | X1 | 0.5 | 79 | -25.23 | -32.6 | -12.15 | 0.9995 | -31.99 | 1.266 | 1.266 | -18.31 | 37 | -31.33 | 42 | 1 | non dimostrata |
| S5 S3 + creatore con un diploma precedente | X2 | 0.3 | 79 | -23.73 | -32.55 | -7.9 | 0.996 | -31.99 | 1.266 | 1.266 | -15.1 | 37 | -31.33 | 42 | 1 | non dimostrata |
| S6 S3 + insider < 10% e <= 2 wallet bundle | X1 | 0.1 | 3635 | -16.76 | -19.1 | -14.18 | 1 | -23.61 | 0.9354 | 0.9354 | -17.42 | 2663 | -14.97 | 972 | 1 | non dimostrata |
| S6 S3 + insider < 10% e <= 2 wallet bundle | X1 | 0.3 | 3635 | -18.52 | -20.45 | -16.58 | 1 | -23.61 | 0.9354 | 0.9354 | -18.7 | 2663 | -18.05 | 972 | 1 | non dimostrata |
| S6 S3 + insider < 10% e <= 2 wallet bundle | X1 | 0.5 | 3635 | -20.29 | -21.53 | -18.88 | 1 | -23.61 | 0.9354 | 0.9354 | -19.98 | 2663 | -21.14 | 972 | 1 | non dimostrata |
| S6 S3 + insider < 10% e <= 2 wallet bundle | X2 | 0.3 | 3635 | -18.13 | -19.84 | -16.16 | 1 | -23.52 | 1.155 | 0.9354 | -17.67 | 2663 | -19.4 | 972 | 1 | non dimostrata |

Controllo X2 (S3): ingressi con un picco precedente già >= 60 SOL nelle righe campionate: 0.00%

## 3. Mappa descrittiva: età × riserva al momento dell'ingresso (X1, taglio 30%)
| età | riserva_SOL | n | media_% | mediana_% | diplomati_% | pareggio_diploma_% |
|---|---|---|---|---|---|---|
| <30s | 0-2 | 268216 | -7.627 | -6.448 | 0.08314 | 0.9683 |
| <30s | 2-5 | 42885 | -20.03 | -22.76 | 0.4734 | 3.262 |
| <30s | 5-10 | 28819 | -31.48 | -38.36 | 1.263 | 6.711 |
| <30s | 10-20 | 21853 | -39.46 | -54.55 | 4.05 | 13.33 |
| <30s | 20-40 | 9066 | -38.16 | -71.53 | 14.88 | 29.26 |
| <30s | 40-85 | 2282 | -37.73 | -83.44 | 48.64 | 76.69 |
| 30-60s | 0-2 | 79255 | -9.131 | -9.097 | 0.1009 | 1.182 |
| 30-60s | 2-5 | 27143 | -19.79 | -22.36 | 0.4495 | 3.187 |
| 30-60s | 5-10 | 15122 | -29.93 | -37.84 | 1.488 | 6.638 |
| 30-60s | 10-20 | 13426 | -40.33 | -55.86 | 4.104 | 13.81 |
| 30-60s | 20-40 | 8294 | -40.49 | -72.26 | 14.76 | 30.37 |
| 30-60s | 40-85 | 2915 | -38.98 | -83.82 | 45.25 | 74.5 |
| 1-2m | 0-2 | 196683 | -8.81 | -7.756 | 0.06864 | 1.107 |
| 1-2m | 2-5 | 48096 | -19.81 | -22.07 | 0.4034 | 3.138 |
| 1-2m | 5-10 | 22555 | -29.86 | -37.72 | 1.494 | 6.619 |
| 1-2m | 10-20 | 19673 | -39.98 | -55.77 | 4.173 | 13.8 |
| 1-2m | 20-40 | 13725 | -39.56 | -72.44 | 15.47 | 30.69 |
| 1-2m | 40-85 | 6118 | -36.79 | -83.4 | 48.5 | 76.51 |
| 2-5m | 0-2 | 268761 | -8.406 | -7.141 | 0.07107 | 1.058 |
| 2-5m | 2-5 | 52998 | -19.57 | -22.27 | 0.4547 | 3.164 |
| 2-5m | 5-10 | 27718 | -29.18 | -37.51 | 1.569 | 6.58 |
| 2-5m | 10-20 | 22332 | -39.17 | -55.51 | 4.348 | 13.73 |
| 2-5m | 20-40 | 16362 | -39.9 | -71.58 | 15 | 29.94 |
| 2-5m | 40-85 | 8470 | -35.51 | -83.42 | 47.21 | 73.41 |
| 5-15m | 0-2 | 265410 | -7.121 | -6.325 | 0.04672 | 0.8696 |
| 5-15m | 2-5 | 18470 | -18.5 | -22.05 | 0.5631 | 3.121 |
| 5-15m | 5-10 | 9363 | -27.84 | -37.37 | 1.752 | 6.545 |
| 5-15m | 10-20 | 7664 | -34.99 | -55.55 | 5.467 | 13.82 |
| 5-15m | 20-40 | 6533 | -37.62 | -72.15 | 16.67 | 30.96 |
| 5-15m | 40-85 | 3796 | -33.85 | -28.86 | 52.42 | 77.98 |

`pareggio_diploma_%` = quota di diplomi necessaria per andare in pari in quella cella (con i costi).
