# Strategy Discovery Engine sulle memecoin già quotate (pool PumpSwap, jocry giugno-luglio 2026)

Pre-registrazione (testo originale):

```
(written before looking at any result):
  * data: jocry postgard_snapshots (PumpSwap pools, June 5 - July 14 2026, a snapshot about every 5 minutes; USD
    converted to SOL with Binance SOLUSDT hourly closes); days split by the snapshot's day: discovery Jun 5-24,
    validation Jun 25 - Jul 4, test Jul 5-14 (read once, only for what passed validation); the other dataset (fly,
    September) is used only if something passes the test;
  * decision moments: the first snapshot of every hour of age, from 30 minutes to 48 hours after the graduation, with
    >= 20 SOL on the pool's SOL side;
  * signals (past and present snapshots only): age, returns over 5 minutes / 1 hour / 6 hours, distance from the
    high since the graduation, return since the graduation, last hour's volume / liquidity, last 5 minutes' volume vs
    the hour (acceleration), buyers' share of the last hour's trades, trades in the last hour, liquidity change over
    the last hour, market cap / liquidity, last hour's volume vs the 6-hour average (revival);
  * named pattern families (thresholds fixed here): momentum = within 5% of the high and turnover above the discovery
    median; breakout = within 2% of the high and acceleration >= 1.5; pullback = 30-60% below the high with a positive
    5-minute return and >= 55% buyers; accumulation = 6-hour return within +-15%, >= 60% buyers and turnover above the
    discovery median; revival = age >= 6 h and last hour's volume >= 3x the 6-hour average; plus, generated
    automatically, every signal in its top / bottom 20%, pairs of the 8 best, a gradient-boosted model (top 10%) and
    every moment (reference); (correction after the synthetic check, before any real run: on the discovery days the
    model is cross-fitted by day - trained on half of the days, scored on the other half - otherwise its
    in-sample fit fills the validation slots; validation and test days use the model trained on all discovery days);
  * entries: E1 at once; E2 confirmation (+10% within 1 hour); E3 pullback (-20% from the high since the decision
    within 2 hours); E4 consolidation (a 1-hour stretch of >= 6 snapshots within a 15% range, within 3 hours);
    delay: the same snapshot (with 1% latency slippage) or the next snapshot;
  * exits (24 hours at most): X1 1 h; X2 4 h; X3 24 h; X4 stop -25% / target +50%; X5 trailing stop 30%; X6 half at
    +50%, the rest with the trailing stop; X7 momentum lost (buyers < 45% of the last hour's trades, after 1 hour);
    X8 liquidity lost (pool liquidity 30% below the entry); a token no longer observed exits at its last snapshot
    (optimistic) and, as a second reading, at -100% (pessimistic);
  * costs on 0.1 SOL: PumpSwap fee tier by market cap (1.25% at <= $100k down to 0.30% at $20M) per side, the sale
    through the constant product of the pool at that moment, own buy impact, 1% latency slippage per side, 0.0002 SOL
    network fee per transaction; stress: fee doubled and 3% more slippage;
  * selection as in discovery_launch: discovery t >= 3 with >= 100 trades; the 60 best go to validation (positive
    mean on >= 50 trades, Benjamini-Hochberg q < 0.10); verdict "edge" only with a test 95% interval above zero,
    positive under the cost stress, positive with the next-snapshot delay and positive in the pessimistic reading.
```
Istantanee: 1,002,433 di 5,067 token; momenti di decisione (uno per token e ora, 30 min - 48 h dopo il diploma, >= 20 SOL di liquidità): **61,422** (scoperta 8,122, validazione 16,682, test 36,618).

## 1. Le famiglie di pattern su tutti i giorni (entrata subito, stessa istantanea)
| pattern | uscita | n | media_% | mediana_% | vincenti_% | pessimistica_% | durata_media_min |
|---|---|---|---|---|---|---|---|
| tutti i momenti | X1 1 h | 61422 | -5.242 | -5.718 | 11.91 | -7.672 | 38.83 |
| tutti i momenti | X2 4 h | 61422 | -6.874 | -6.814 | 15.53 | -16.36 | 210.9 |
| tutti i momenti | X3 24 h | 61422 | -11.12 | -11.76 | 13.64 | -63.38 | 999.3 |
| tutti i momenti | X4 stop -25% / +50% | 61422 | -5.796 | -10.79 | 17.3 | -45.31 | 616.8 |
| tutti i momenti | X5 trailing 30% | 61422 | -9.817 | -10.85 | 14.68 | -51.4 | 641.4 |
| tutti i momenti | X6 metà a +50% + trailing | 61422 | -7.449 | -10.59 | 16.48 | -48.98 | 641.4 |
| tutti i momenti | X7 slancio perso | 61422 | -6.734 | -6.696 | 12.03 | -16.38 | 192 |
| tutti i momenti | X8 liquidità persa | 61422 | -10.2 | -12.07 | 13.2 | -60.49 | 857.4 |
| slancio: vicino al massimo, volume alto | X1 1 h | 953 | -5.668 | -9.445 | 29.49 | -6.405 | 45.1 |
| slancio: vicino al massimo, volume alto | X2 4 h | 953 | -10.57 | -21.71 | 27.7 | -13.14 | 222.9 |
| slancio: vicino al massimo, volume alto | X3 24 h | 953 | -22.78 | -60.73 | 17.84 | -47.01 | 1261 |
| slancio: vicino al massimo, volume alto | X4 stop -25% / +50% | 953 | -8.21 | -30 | 30.43 | -15.61 | 219.7 |
| slancio: vicino al massimo, volume alto | X5 trailing 30% | 953 | -13.69 | -26.73 | 21.2 | -21.31 | 257.1 |
| slancio: vicino al massimo, volume alto | X6 metà a +50% + trailing | 953 | -10.24 | -25.78 | 26.55 | -17.79 | 257.1 |
| slancio: vicino al massimo, volume alto | X7 slancio perso | 953 | -13.27 | -31.66 | 21.51 | -17.25 | 450.3 |
| slancio: vicino al massimo, volume alto | X8 liquidità persa | 953 | -21.44 | -56.28 | 15.01 | -40.58 | 682.2 |
| rottura: nuovo massimo con accelerazione | X1 1 h | 368 | -3.271 | -7.13 | 20.65 | -5.517 | 41.54 |
| rottura: nuovo massimo con accelerazione | X2 4 h | 368 | -5.803 | -11.66 | 21.2 | -10.16 | 217.9 |
| rottura: nuovo massimo con accelerazione | X3 24 h | 368 | 3.824 | -27.21 | 20.11 | -38.08 | 1185 |
| rottura: nuovo massimo con accelerazione | X4 stop -25% / +50% | 368 | -5.341 | -27.82 | 26.36 | -30.63 | 361.2 |
| rottura: nuovo massimo con accelerazione | X5 trailing 30% | 368 | -12.19 | -21.41 | 19.29 | -38.65 | 385.1 |
| rottura: nuovo massimo con accelerazione | X6 metà a +50% + trailing | 368 | -6.38 | -18.99 | 24.18 | -32.77 | 385.1 |
| rottura: nuovo massimo con accelerazione | X7 slancio perso | 368 | 6.588 | -12.61 | 19.84 | 0.1371 | 344.9 |
| rottura: nuovo massimo con accelerazione | X8 liquidità persa | 368 | 1.303 | -40.01 | 16.85 | -36.82 | 710.7 |
| ritracciamento con ripresa | X1 1 h | 964 | -8.741 | -7.737 | 26.76 | -10.4 | 44.13 |
| ritracciamento con ripresa | X2 4 h | 964 | -15.37 | -16.51 | 25.41 | -20.51 | 219.2 |
| ritracciamento con ripresa | X3 24 h | 964 | -26.82 | -47.68 | 19.71 | -58.79 | 1135 |
| ritracciamento con ripresa | X4 stop -25% / +50% | 964 | -11.69 | -30.38 | 26.66 | -24.22 | 251.1 |
| ritracciamento con ripresa | X5 trailing 30% | 964 | -15.78 | -27.38 | 20.64 | -29.87 | 271 |
| ritracciamento con ripresa | X6 metà a +50% + trailing | 964 | -13.69 | -26.41 | 23.55 | -27.75 | 271 |
| ritracciamento con ripresa | X7 slancio perso | 964 | -19.24 | -20.67 | 20.75 | -27.27 | 362.8 |
| ritracciamento con ripresa | X8 liquidità persa | 964 | -23.77 | -54.72 | 17.84 | -51.99 | 662.6 |
| accumulazione | X1 1 h | 988 | -5.051 | -6.373 | 20.85 | -7.109 | 39.23 |
| accumulazione | X2 4 h | 988 | -13.81 | -13.26 | 20.65 | -20.98 | 214 |
| accumulazione | X3 24 h | 988 | -25.25 | -23.1 | 15.49 | -67.44 | 1071 |
| accumulazione | X4 stop -25% / +50% | 988 | -10.64 | -24.46 | 20.75 | -34.96 | 445.8 |
| accumulazione | X5 trailing 30% | 988 | -17.26 | -19.75 | 16.3 | -44.57 | 482.9 |
| accumulazione | X6 metà a +50% + trailing | 988 | -12.18 | -19.35 | 19.03 | -39.6 | 482.9 |
| accumulazione | X7 slancio perso | 988 | -18.52 | -11.47 | 15.08 | -26.51 | 254.5 |
| accumulazione | X8 liquidità persa | 988 | -25.44 | -24.84 | 13.87 | -64.39 | 765.3 |
| revival: volume 3x la media di 6 ore | X1 1 h | 3828 | -6.414 | -5.712 | 7.184 | -9.98 | 34.96 |
| revival: volume 3x la media di 6 ore | X2 4 h | 3828 | -8.46 | -6.702 | 9.718 | -21.19 | 204.4 |
| revival: volume 3x la media di 6 ore | X3 24 h | 3828 | -10.72 | -8.875 | 10.84 | -76.52 | 879.8 |
| revival: volume 3x la media di 6 ore | X4 stop -25% / +50% | 3828 | -8.437 | -8.719 | 12.57 | -64.59 | 685.8 |
| revival: volume 3x la media di 6 ore | X5 trailing 30% | 3828 | -9.784 | -8.818 | 11.36 | -67.73 | 712.1 |
| revival: volume 3x la media di 6 ore | X6 metà a +50% + trailing | 3828 | -8.681 | -8.677 | 12.51 | -66.59 | 712.1 |
| revival: volume 3x la media di 6 ore | X7 slancio perso | 3828 | -7.779 | -6.607 | 8.281 | -19.81 | 174.9 |
| revival: volume 3x la media di 6 ore | X8 liquidità persa | 3828 | -10.81 | -8.923 | 10.66 | -75.38 | 819.1 |

Combinazioni positive (lettura ottimistica): 3 su 48.

## 2. Il motore di scoperta
Strategie generate e valutate sui giorni di scoperta: **3,456** (54 ipotesi x 2 ritardi x 4 entrate x 8 uscite). Con t >= 3, media positiva e >= 100 operazioni: **2**.
Selezionate per la validazione: 2; passano: **0**.
| ipotesi | ritardo | entrata | uscita | n_scoperta | media_scoperta_% | t_scoperta | n_validazione | media_validazione_% | q_val | passa_validazione |
|---|---|---|---|---|---|---|---|---|---|---|
| distanza dal massimo alto (>= -0.441) | istantanea dopo | E4 consolidamento | X2 4 h | 101 | 11.69 | 3.114 | 231 | -4.765 | 0.9385 | False |
| distanza dal massimo alto (>= -0.441) E età (ore) basso (<= 9.05) | istantanea dopo | E4 consolidamento | X2 4 h | 101 | 11.69 | 3.114 | 231 | -4.765 | 0.9385 | False |


## 3. Giorni di test (letti una sola volta): nessuna ha passato la validazione; per trasparenza, le 10 migliori della scoperta
| momento_s | ipotesi | ritardo_s | entrata | uscita | test_n | test_media_% | test_IC95_basso_% | test_IC95_alto_% | test_p | test_mediana_% | test_vincenti_% | test_vincita_media_% | test_perdita_media_% | test_profit_factor | test_serie_perdite_max | test_durata_media_min | test_profitto_SOL_su_0,1 | test_ROI_su_2_SOL_% | test_maxDD_% | test_Sharpe_giorni | test_Sortino_giorni | test_commissioni_SOL | test_pessimistica_% | test_stress_media_% | test_ritardo30_media_% | media_scoperta_% | verdetto |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1-48 h | distanza dal massimo alto (>= -0.441) | 300 | E4 consolidamento | X2 4 h | 360 | -10.68 | -15.49 | -4.741 | 0.9995 | -7.98 | 25.56 | 29.15 | -24.36 | 0.4109 | 18 | 257.3 | -3.845 | -192.3 | -214.9 | -16.16 | -23.06 | 1.044 | -11.82 | -15.51 | -10.68 | 11.69 | no |
| 1-48 h | distanza dal massimo alto (>= -0.441) E età (ore) basso (<= 9.05) | 300 | E4 consolidamento | X2 4 h | 360 | -10.68 | -15.26 | -4.607 | 0.9995 | -7.98 | 25.56 | 29.15 | -24.36 | 0.4109 | 18 | 257.3 | -3.845 | -192.3 | -214.9 | -16.16 | -23.06 | 1.044 | -11.82 | -15.51 | -10.68 | 11.69 | no |


**Strategie con un vantaggio dimostrato fuori campione: 0.**
