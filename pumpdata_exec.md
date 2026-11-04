# Operazioni fallite su pump.fun e PumpSwap per età del token (15 ottobre 2026, dati reali)

Data: pumpdatafun/pump-fun-trades-sample (CC BY 4.0): every curve and PumpSwap trade of 2026-10-15 that the
archive ties to a coin, the transactions that failed on chain kept beside the ones that landed, with the fee each
failed transaction paid and its error. Descriptive only (no strategy): it gives the backtests a measured
"orders not executable" rate and the cost of a failed attempt instead of an assumption.

Method (fixed before reading the data): a transaction is one (slot, idx); a token's age is the block time of the
trade minus the block time of its creation (the day's launches table; tokens created before the day are reported
apart); age buckets 0-10 s, 10-30 s, 30-60 s, 1-5 min, 5-60 min, 1-24 h; failure share = failed transactions /
(failed + landed) per venue, side and bucket; a failed transaction's fee is counted once.
Lanci del giorno: 46,540.

## Quota di transazioni fallite per mercato, lato ed età del token
| venue | side | bucket | riuscite | fallite | commissioni_fallite_SOL | fallite_% | commissione_media_fallita_SOL |
|---|---|---|---|---|---|---|---|
| curve | buy | 0-10 s | 3.579e+05 | 2.069e+06 | 162.7 | 85.25 | 7.863e-05 |
| curve | buy | 10-30 s | 3.264e+05 | 1.467e+06 | 50.06 | 81.8 | 3.412e-05 |
| curve | buy | 30-60 s | 2.989e+05 | 5.753e+05 | 22.81 | 65.81 | 3.965e-05 |
| curve | buy | 1-5 min | 7.416e+05 | 8.201e+05 | 49.63 | 52.51 | 6.051e-05 |
| curve | buy | 5-60 min | 4.637e+05 | 3.071e+05 | 35.22 | 39.84 | 0.0001147 |
| curve | buy | 1-24 h | 9.46e+04 | 2.832e+04 | 8.332 | 23.04 | 0.0002942 |
| curve | buy | creato prima del giorno | 1.269e+05 | 6.368e+04 | 12.17 | 33.41 | 0.0001912 |
| curve | sell | 0-10 s | 1.96e+05 | 6.148e+04 | 5.565 | 23.87 | 9.052e-05 |
| curve | sell | 10-30 s | 2.85e+05 | 5.582e+04 | 4.49 | 16.38 | 8.044e-05 |
| curve | sell | 30-60 s | 2.723e+05 | 5.108e+04 | 2.409 | 15.8 | 4.717e-05 |
| curve | sell | 1-5 min | 6.778e+05 | 2.663e+06 | 22.36 | 79.72 | 8.397e-06 |
| curve | sell | 5-60 min | 4.284e+05 | 1.69e+06 | 15.26 | 79.78 | 9.027e-06 |
| curve | sell | 1-24 h | 9.182e+04 | 1.804e+05 | 2.483 | 66.27 | 1.376e-05 |
| curve | sell | creato prima del giorno | 1.233e+05 | 2.429e+05 | 5.321 | 66.34 | 2.19e-05 |
| pumpswap | buy | 0-10 s | 9831 | 5.097e+04 | 2.756 | 83.83 | 5.408e-05 |
| pumpswap | buy | 10-30 s | 2.661e+04 | 1.177e+05 | 1.394 | 81.56 | 1.185e-05 |
| pumpswap | buy | 30-60 s | 5.299e+04 | 1.001e+05 | 6.875 | 65.38 | 6.871e-05 |
| pumpswap | buy | 1-5 min | 4.794e+05 | 1.046e+06 | 14.35 | 68.58 | 1.371e-05 |
| pumpswap | buy | 5-60 min | 2.866e+06 | 3.151e+06 | 57.72 | 52.37 | 1.832e-05 |
| pumpswap | buy | 1-24 h | 1.313e+06 | 5.65e+05 | 21.2 | 30.08 | 3.752e-05 |
| pumpswap | buy | creato prima del giorno | 5.724e+06 | 7.85e+05 | 62.74 | 12.06 | 7.992e-05 |
| pumpswap | sell | 0-10 s | 2127 | 1026 | 0.2882 | 32.54 | 0.0002809 |
| pumpswap | sell | 10-30 s | 1.486e+04 | 1.478e+04 | 1.349 | 49.87 | 9.131e-05 |
| pumpswap | sell | 30-60 s | 3.666e+04 | 6.04e+04 | 2.104 | 62.23 | 3.483e-05 |
| pumpswap | sell | 1-5 min | 3.36e+05 | 6.143e+05 | 17.45 | 64.64 | 2.841e-05 |
| pumpswap | sell | 5-60 min | 2.316e+06 | 1.905e+06 | 37.46 | 45.12 | 1.967e-05 |
| pumpswap | sell | 1-24 h | 9.447e+05 | 5.299e+05 | 11.9 | 35.93 | 2.247e-05 |
| pumpswap | sell | creato prima del giorno | 2.88e+06 | 1.074e+06 | 38.86 | 27.17 | 3.617e-05 |


## Errori più frequenti delle transazioni fallite
| venue | side | bucket | errore | transazioni | quota_pct |
|---|---|---|---|---|---|
| curve | buy | 0-10 s | InstructionError(0, Custom(7)) | 8.92e+05 | 43.11 |
| curve | buy | 0-10 s | InstructionError(3, Custom(7)) | 4.067e+05 | 19.66 |
| curve | buy | 0-10 s | InstructionError(3, Custom(6042)) | 1.077e+05 | 5.203 |
| curve | buy | 0-10 s | InstructionError(0, Custom(408)) | 9.85e+04 | 4.761 |
| curve | buy | 30-60 s | InstructionError(0, Custom(7)) | 2.797e+05 | 48.61 |
| curve | buy | 30-60 s | InstructionError(4, Custom(6001)) | 5.006e+04 | 8.702 |
| curve | buy | 30-60 s | InstructionError(0, Custom(408)) | 2.974e+04 | 5.17 |
| curve | buy | 30-60 s | InstructionError(1, Custom(6001)) | 2.85e+04 | 4.955 |
| curve | buy | 5-60 min | InstructionError(2, Custom(6001)) | 9.723e+04 | 31.66 |
| curve | buy | 5-60 min | InstructionError(0, Custom(408)) | 3.905e+04 | 12.72 |
| curve | buy | 5-60 min | InstructionError(0, Custom(412)) | 3.348e+04 | 10.9 |
| curve | buy | 5-60 min | InstructionError(4, Custom(6001)) | 3.237e+04 | 10.54 |
| curve | sell | 0-10 s | InstructionError(3, Custom(6003)) | 2.472e+04 | 40.2 |
| curve | sell | 0-10 s | InstructionError(1, Custom(6003)) | 7987 | 12.99 |
| curve | sell | 0-10 s | InstructionError(2, Custom(6001)) | 6167 | 10.03 |
| curve | sell | 0-10 s | InstructionError(2, Custom(6003)) | 3988 | 6.487 |
| curve | sell | 30-60 s | InstructionError(0, Custom(12)) | 1.18e+04 | 23.1 |
| curve | sell | 30-60 s | InstructionError(2, Custom(6001)) | 1.022e+04 | 20 |
| curve | sell | 30-60 s | InstructionError(2, Custom(6003)) | 9907 | 19.39 |
| curve | sell | 30-60 s | InstructionError(0, Custom(6001)) | 3516 | 6.883 |
| curve | sell | 5-60 min | InstructionError(2, Custom(6001)) | 9.919e+05 | 58.68 |
| curve | sell | 5-60 min | InstructionError(0, Custom(4)) | 1.713e+05 | 10.14 |
| curve | sell | 5-60 min | InstructionError(0, Custom(12)) | 1.483e+05 | 8.776 |
| curve | sell | 5-60 min | InstructionError(0, Custom(23)) | 1.319e+05 | 7.803 |
| pumpswap | buy | 0-10 s | InstructionError(7, Custom(6040)) | 4.474e+04 | 87.77 |
| pumpswap | buy | 0-10 s | InstructionError(3, Custom(6040)) | 3331 | 6.536 |
| pumpswap | buy | 0-10 s | InstructionError(4, Custom(6040)) | 971 | 1.905 |
| pumpswap | buy | 0-10 s | InstructionError(5, Custom(6040)) | 369 | 0.724 |
| pumpswap | buy | 30-60 s | InstructionError(4, Custom(6040)) | 3.049e+04 | 30.48 |
| pumpswap | buy | 30-60 s | InstructionError(5, Custom(6040)) | 1.645e+04 | 16.44 |
| pumpswap | buy | 30-60 s | InstructionError(4, Custom(6004)) | 1.25e+04 | 12.49 |
| pumpswap | buy | 30-60 s | InstructionError(7, Custom(6040)) | 1.172e+04 | 11.72 |
| pumpswap | buy | 5-60 min | InstructionError(1, Custom(6040)) | 6.586e+05 | 20.9 |
| pumpswap | buy | 5-60 min | InstructionError(5, Custom(6040)) | 5.818e+05 | 18.47 |
| pumpswap | buy | 5-60 min | InstructionError(0, Custom(6040)) | 4.783e+05 | 15.18 |
| pumpswap | buy | 5-60 min | InstructionError(0, Custom(100)) | 2.615e+05 | 8.3 |
| pumpswap | sell | 0-10 s | InstructionError(3, Custom(3012)) | 338 | 32.94 |
| pumpswap | sell | 0-10 s | InstructionError(3, Custom(6063)) | 311 | 30.31 |
| pumpswap | sell | 0-10 s | InstructionError(3, Custom(1)) | 228 | 22.22 |
| pumpswap | sell | 0-10 s | InstructionError(2, Custom(6001)) | 50 | 4.873 |
| pumpswap | sell | 30-60 s | InstructionError(3, Custom(6004)) | 2.999e+04 | 49.64 |
| pumpswap | sell | 30-60 s | InstructionError(4, Custom(6004)) | 1.664e+04 | 27.55 |
| pumpswap | sell | 30-60 s | InstructionError(3, Custom(1)) | 3601 | 5.962 |
| pumpswap | sell | 30-60 s | InstructionError(1, Custom(6004)) | 2612 | 4.324 |
| pumpswap | sell | 5-60 min | InstructionError(3, Custom(6004)) | 4.756e+05 | 24.97 |
| pumpswap | sell | 5-60 min | InstructionError(4, Custom(6004)) | 4.702e+05 | 24.69 |
| pumpswap | sell | 5-60 min | InstructionError(2, Custom(6004)) | 1.651e+05 | 8.668 |
| pumpswap | sell | 5-60 min | InstructionError(1, Custom(6004)) | 1.283e+05 | 6.735 |


## Acquisti sulla curva nei primi 60 secondi: per wallet
| wallet | mai_riusciti | quota_fallita_mediana | tentativi_falliti_medi |
|---|---|---|---|
| 96722 | 1405 | 0 | 42.51 |

