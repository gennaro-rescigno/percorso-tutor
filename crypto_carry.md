# Studio storico: incassare il funding dell'hype senza scommettere sul prezzo (spot + short perpetuo, 1-3 giorni)

When a coin is in a frenzy, leveraged buyers on perpetual futures pay a funding fee to the sellers every 8 hours.
Holding the coin (spot) and selling the same amount of its perpetual cancels the price move and collects that fee.
It is a known trade ("cash and carry"; Schmeling, Schrimpf and Todorov, "Crypto carry", BIS 2023, document large
and time-varying carry in crypto); the question is whether it survives our costs with holds of 1-3 days on many
coins and memecoins. Free data: Binance spot and USDT perpetual daily candles and funding (data.binance.vision).

Pre-registrazione (testo originale):

```
(written before looking at any result):
  * coins: every USDT perpetual with a Binance spot pair of the same coin (exact name, or the perpetual's "1000" /
    "1000000" / "1M" multiplier removed), accepted only if the daily returns of the two correlate >= 0.9; universe
    each day: the 100 with the highest 30-day perpetual volume known the day before, >= 30 days of history;
  * signal at the daily close (00:00 UTC): the funding of the day just ended (its 3 payments, all known by then);
    position = half of the slot in spot, half as 1x collateral of an equal short on the perpetual; it earns the
    funding of each following day (or pays it when negative) plus the change in the spot-perpetual gap; exit at the
    close 1, 2 or 3 days later (7 days shown only for information: it is outside the 3-day limit);
  * costs per side and leg: spot 0.10% fee, perpetual 0.05% fee, plus slippage 0.05% (rank 1-30) or 0.20% (31-100)
    on each leg; the short leg cannot lose more than its collateral;
  * rules (strongest funding first, at most 10 positions of 10% of equity):
      C1 the day's funding >= 0.03% (above the base rate of 0.01% every 8 hours);
      C2 the day's funding >= 0.10% (frenzy);
      C3 funding >= 0.05% on each of the last 3 days (persistent);
      C0 BTC and ETH only, whenever their funding >= 0.03% (the classic, liquid version);
  * periods: 2020-2021 (in sample) and 2022-01-01 .. end (out of sample); every rule and hold positive out of sample
    is re-run with costs doubled and with entry one day late; verdict "regge" only with positive results in both
    periods, an out-of-sample 95% interval of the Sharpe above zero, and still positive with costs doubled and late.
```
Perpetui: 918; con una coppia spot Binance della stessa moneta: 476; accettati (correlazione >= 0,9): **451**.
- 2020-2021: funding giornaliero nelle 100 più scambiate: medio +0.0836%, mediano +0.0347%; giorni >= 0,03%: 71.0%, >= 0,10%: 26.7%; negativi: 11.8%.
- 2022-fine: funding giornaliero nelle 100 più scambiate: medio -0.0257%, mediano +0.0200%; giorni >= 0,03%: 34.2%, >= 0,10%: 3.0%; negativi: 27.9%.

## Le regole pre-registrate
| variante | IS_CAGR_% | OOS_CAGR_% | OOS_Sharpe | OOS_Sharpe_IC95 | OOS_maxDD_% | OOS_operazioni | OOS_vincenti_% | OOS_media_op_% | OOS_funding_medio_op_% | OOS_liquidazioni |
|---|---|---|---|---|---|---|---|---|---|---|
| C0, 1 giorni | -12.4 | -3.788 | -11.12 | [-12.95, -9.26] | -17.02 | 812 | 0 | -0.2298 | 0.01928 | 0 |
| C0, 2 giorni | -6.581 | -2.194 | -12.9 | [-15.00, -11.04] | -10.17 | 505 | 0 | -0.2122 | 0.03571 | 0 |
| C0, 3 giorni | -2.582 | -1.542 | -9.726 | [-10.90, -8.58] | -7.238 | 379 | 0.5277 | -0.1979 | 0.04977 | 0 |
| C0, 7 giorni | -1.479 | -0.6259 | -4.973 | [-5.81, -4.09] | -2.991 | 209 | 6.22 | -0.1448 | 0.1018 | 0 |
| C1, 1 giorni | -59.9 | -72.34 | -22.66 | [-33.85, -16.85] | -99.8 | 12796 | 0.2892 | -0.4836 | 0.01786 | 4 |
| C1, 2 giorni | -31.13 | -52.92 | -15.1 | [-27.41, -10.92] | -97.37 | 7415 | 0.6069 | -0.4884 | 0.03108 | 8 |
| C1, 3 giorni | -14.09 | -39.56 | -6.443 | [-15.63, -3.71] | -91.2 | 5154 | 1.203 | -0.468 | 0.03986 | 11 |
| C1, 7 giorni | 4.324 | -18.22 | -1.56 | [-6.41, -0.34] | -65.25 | 2309 | 4.331 | -0.4024 | 0.06773 | 23 |
| C2, 1 giorni | -31.49 | -10.28 | -3.672 | [-6.79, -2.25] | -40.81 | 1184 | 1.351 | -0.4411 | 0.069 | 1 |
| C2, 2 giorni | -11.68 | -4.102 | -0.575 | [-4.70, 0.35] | -26.98 | 713 | 4.628 | -0.2686 | 0.1107 | 4 |
| C2, 3 giorni | -2.699 | -2.688 | -0.3633 | [-3.74, 0.39] | -21.28 | 526 | 9.506 | -0.2296 | 0.1499 | 7 |
| C2, 7 giorni | 7.517 | -1.08 | -0.1217 | [-2.07, 0.53] | -13.79 | 321 | 28.04 | -0.1271 | 0.2779 | 11 |
| C3, 1 giorni | -28.94 | -13.7 | -3.219 | [-7.04, -2.11] | -50.94 | 1427 | 1.191 | -0.4953 | 0.06051 | 2 |
| C3, 2 giorni | -9.493 | -8.69 | -2.154 | [-5.70, -1.57] | -35.56 | 789 | 3.422 | -0.5509 | 0.1128 | 4 |
| C3, 3 giorni | -3.146 | -6.695 | -1.638 | [-4.15, -1.25] | -28.46 | 569 | 7.909 | -0.5804 | 0.1584 | 6 |
| C3, 7 giorni | 11.76 | -5.06 | -1.16 | [-1.71, -0.85] | -22.2 | 312 | 29.49 | -0.7882 | 0.3084 | 9 |

Positive fuori campione (tenute 1-3 giorni): **0 su 12**.

## Verdetto
Nessuna regola positiva fuori campione: **nessuna regge**.
