# Studio storico: il filtro di trend sulle memecoin già quotate (perpetui Binance, 2021-2026)

Pre-registrazione (testo originale):

```
(written before looking at any result):
  * coins: the memecoin list below (written now, failures included: whoever is in the list and has a Binance USDT
    perpetual enters from its 50th candle, delisted contracts exit at their last price); a coin is "in the basket"
    while it has >= 50 candles of history and is still trading;
  * portfolio: each basket coin gets 1/N of the equity (N = basket size), held only while its close is above the
    average of its last 50 closes, otherwise that share stays in cash (USDC); shares re-set every 7 days; decisions
    at the candle close, executed at that close; costs 0.30% per side (on-chain swap of liquid memecoins or CEX
    fee + slippage);
  * variants: M1 daily candles, 50-day average; M2 daily, 20-day average; M3 4-hour candles, average of 50 candles
    (about 8 days, shorter holds); the benchmark is the same basket always held (same re-set, same costs);
  * checks for each variant: costs doubled (0.60% per side) and execution one candle late;
  * periods reported: 2021, 2022-2026 and the whole; per year; per coin (filter vs held); every round trip
    (count, length, winners, average, median, profit factor, share of the gains from the best 10%);
  * verdict "regge" only if, on 2022-2026: positive return, better than holding in both return and worst drawdown,
    95% block-bootstrap interval of the Sharpe above zero, and still positive with costs doubled and one candle late.
```
Memecoin dell'elenco con un perpetuo Binance: **60**: 1000000MOG, 1000BONK, 1000CAT, 1000CHEEMS, 1000FLOKI, 1000LUNC, 1000PEPE, 1000RATS, 1000SATS, 1000SHIB, 1000WHY, 1000X, 1MBABYDOGE, ACT, AI16Z, AIXBT, BANANAS31, BAN, BOME, BRETT, BROCCOLI714, BROCCOLIF3B, CATI, CHILLGUY, DEGEN, DOGE, DOGS, FARTCOIN, GOAT, GRIFFAIN, HIPPO, HMSTR, JELLYJELLY, KOMA, MELANIA, MEMEFI, MEME, MEW, MOODENG, MUBARAK, MYRO, NEIROETH, NEIRO, NOT, PENGU, PEOPLE, PIPPIN, PNUT, PONKE, POPCAT, SLERF, SPX, TRUMP, TURBO, TUT, USELESS, VINE, WEN, WIF, ZEREBRO.
Dati giornalieri fino al 2026-10-31; chiusi o delistati prima della fine: 0 (nessuno).

## Portafogli (rendimento annuo composto e perdita massima)
| variante | 2021_CAGR_% | 2021_maxDD_% | 2022-2026_CAGR_% | 2022-2026_maxDD_% | 2022-2026_Sharpe | 2022-2026_Sharpe_IC95 | tutto_CAGR_% | tutto_maxDD_% |
|---|---|---|---|---|---|---|---|---|
| M1 giornaliero, media 50 | 7965 | -76.61 | 4.623 | -60.16 | 0.346 | [-0.78, 1.31] | 120.4 | -76.61 |
| M1 giornaliero, media 50: sempre tenute | 1.022e+04 | -75.44 | -23.06 | -83.87 | 0.1921 | [-0.65, 1.07] | 78.18 | -89.88 |
| M1 giornaliero, media 50: costi doppi | 7485 | -77.65 | -2.855 | -65.15 | 0.2074 | [-0.86, 1.18] | 105.1 | -77.65 |
| M1 giornaliero, media 50: una candela dopo | 1.249e+04 | -64.68 | 4.612 | -65.44 | 0.3446 | [-0.64, 1.23] | 137.8 | -65.44 |
| M2 giornaliero, media 20 | 3093 | -59.22 | -14.34 | -74.56 | -0.009073 | [-1.11, 1.05] | 59.29 | -81.78 |
| M2 giornaliero, media 20: sempre tenute | 1.201e+04 | -71.16 | -24.2 | -85.54 | 0.1878 | [-0.71, 1.17] | 80.92 | -89.57 |
| M2 giornaliero, media 20: costi doppi | 2797 | -60.9 | -24.25 | -79.53 | -0.2289 | [-1.32, 0.85] | 41.49 | -85.72 |
| M2 giornaliero, media 20: una candela dopo | 1447 | -68.25 | -8.22 | -72.66 | 0.1169 | [-0.93, 1.21] | 48.96 | -73.54 |
| M3 4 ore, media di 50 candele | 5302 | -69.01 | -11.13 | -74.73 | 0.09423 | [-0.96, 1.04] | 79.71 | -76.26 |
| M3 4 ore, media di 50 candele: sempre tenute | 1.097e+04 | -73.26 | -26.65 | -85.37 | 0.1563 | [-0.76, 1.08] | 73.36 | -91.53 |
| M3 4 ore, media di 50 candele: costi doppi | 3203 | -75.43 | -43.1 | -95.26 | -0.636 | [-1.93, 0.47] | 14.16 | -96.71 |
| M3 4 ore, media di 50 candele: una candela dopo | 7711 | -61.98 | -14 | -79.4 | 0.03561 | [-1.02, 1.04] | 86.31 | -79.4 |

## Operazioni (andata e ritorno, entrate dal 2022)
| variante | operazioni_2022+ | giorni_mediani | vincenti_% | media_% | mediana_% | profit_factor | quota_dal_10%_migliore |
|---|---|---|---|---|---|---|---|
| M1 giornaliero, media 50 | 1474 | 3 | 14.9 | -1.02 | -5.24 | 0.85 | 97.7 |
| M2 giornaliero, media 20 | 2593 | 3 | 19.1 | -0.34 | -4.96 | 0.95 | 93.4 |
| M3 4 ore, media di 50 candele | 9762 | 0.7 | 14.2 | -0.35 | -2.28 | 0.88 | 98.1 |

## M1 anno per anno
| anno | filtro_% | sempre_tenute_% |
|---|---|---|
| 2021 | 7965 | 1.022e+04 |
| 2022 | -44.47 | -63.56 |
| 2023 | 46.05 | 6.228 |
| 2024 | 98.45 | 128.8 |
| 2025 | -12.65 | -63.92 |
| 2026 | -11.51 | -11.86 |

## M1 per moneta (operazioni dal 2022: rendimento composto)
| moneta | operazioni | vincenti | composto_% |
|---|---|---|---|
| 1000RATSUSDT | 46 | 8 | -98.98 |
| JELLYJELLYUSDT | 40 | 1 | -95.85 |
| 1000SATSUSDT | 40 | 4 | -94.57 |
| MEMEUSDT | 39 | 4 | -93.05 |
| BANUSDT | 39 | 2 | -91.03 |
| NOTUSDT | 36 | 3 | -86.93 |
| HIPPOUSDT | 10 | 0 | -83.89 |
| HMSTRUSDT | 29 | 2 | -83.17 |
| MEWUSDT | 33 | 3 | -82.12 |
| DOGSUSDT | 30 | 3 | -81.48 |
| 1MBABYDOGEUSDT | 27 | 3 | -80.47 |
| BROCCOLIF3BUSDT | 24 | 3 | -77.26 |
| CATIUSDT | 29 | 4 | -76.65 |
| ZEREBROUSDT | 24 | 2 | -76.53 |
| 1000CHEEMSUSDT | 31 | 5 | -75.83 |
| 1000CATUSDT | 23 | 3 | -73.95 |
| PNUTUSDT | 26 | 4 | -73.8 |
| ACTUSDT | 22 | 1 | -72.08 |
| DEGENUSDT | 20 | 1 | -70.61 |
| BROCCOLI714USDT | 20 | 3 | -68.77 |
| VINEUSDT | 12 | 1 | -67.61 |
| KOMAUSDT | 19 | 3 | -63.38 |
| AIXBTUSDT | 22 | 4 | -62.97 |
| TRUMPUSDT | 14 | 1 | -62.6 |
| PIPPINUSDT | 27 | 2 | -62.17 |
| MYROUSDT | 21 | 5 | -61.51 |
| MELANIAUSDT | 24 | 2 | -61.03 |
| 1000WHYUSDT | 10 | 0 | -60.47 |
| SPXUSDT | 27 | 6 | -60.46 |
| TURBOUSDT | 31 | 5 | -60.02 |
| 1000XUSDT | 11 | 1 | -58.73 |
| POPCATUSDT | 22 | 4 | -56.25 |
| 1000LUNCUSDT | 51 | 9 | -53.83 |
| MUBARAKUSDT | 21 | 1 | -52.94 |
| 1000000MOGUSDT | 21 | 3 | -51.15 |
| WIFUSDT | 30 | 6 | -48.31 |
| GRIFFAINUSDT | 19 | 4 | -43.2 |
| NEIROETHUSDT | 12 | 2 | -40.25 |
| BOMEUSDT | 26 | 4 | -38.88 |
| GOATUSDT | 16 | 2 | -38.04 |
| BRETTUSDT | 20 | 4 | -38.03 |
| FARTCOINUSDT | 18 | 4 | -35.71 |
| NEIROUSDT | 17 | 3 | -32.38 |
| AI16ZUSDT | 7 | 1 | -27.52 |
| 1000SHIBUSDT | 53 | 9 | -26.73 |
| 1000BONKUSDT | 35 | 8 | -26.34 |
| SLERFUSDT | 11 | 2 | -24.58 |
| PEOPLEUSDT | 55 | 14 | -20.43 |
| DOGEUSDT | 55 | 13 | -18.03 |
| PONKEUSDT | 8 | 2 | -15.53 |
| CHILLGUYUSDT | 15 | 3 | -12.18 |
| WENUSDT | 2 | 0 | -5.913 |
| TUTUSDT | 20 | 3 | 8.309 |
| MOODENGUSDT | 22 | 3 | 12.17 |
| BANANAS31USDT | 14 | 2 | 26.38 |
| PENGUUSDT | 21 | 4 | 29.28 |
| MEMEFIUSDT | 1 | 1 | 76.15 |
| USELESSUSDT | 7 | 4 | 216.4 |
| 1000PEPEUSDT | 36 | 7 | 402.3 |
| 1000FLOKIUSDT | 33 | 9 | 480.9 |


## Verdetto
- M1 giornaliero, media 50: **non regge**
- M2 giornaliero, media 20: **non regge**
- M3 4 ore, media di 50 candele: **non regge**
