# Stress test del risk management (scenari sintetici di rug pull)

> ⚠️ **DATI SINTETICI** — questo report verifica il funzionamento del motore e del risk
> management. NON è una misura della redditività di alcuna strategia.

## Dati
- Fonte: `synthetic` — universo: scenari generati
- Token: 12 — periodo: 2026-01-01T00:00:00+00:00 → 2026-01-01T17:28:00+00:00
- Privo di survivorship bias: sì
- Feature point-in-time: **NO (solo OHLCV)**
- Nota: DATI SINTETICI: solo test del motore e del risk management

## Risultati

| Metrica | conservative | moderate | aggressive |
|---|---|---|---|
| Capitale iniziale (SOL) | 2.0000 | 2.0000 | 2.0000 |
| Capitale finale (SOL) | 1.8793 | 1.6179 | 1.4310 |
| Profitto netto (SOL) | -0.1207 | -0.3821 | -0.5690 |
| Rendimento | -6.04% | -19.10% | -28.45% |
| Operazioni | 3 | 6 | 6 |
| Win rate | 0.00% | 0.00% | 0.00% |
| Loss rate | 100.00% | 100.00% | 100.00% |
| Profit factor | 0.00 | 0.00 | 0.00 |
| Expectancy / trade (SOL) | -0.0402 | -0.0637 | -0.0948 |
| Expectancy / trade (%) | -77.50% | -78.57% | -79.16% |
| IC 95% expectancy | n/d | n/d | n/d |
| Average win (SOL) | n/d | n/d | n/d |
| Average loss (SOL) | -0.0402 | -0.0637 | -0.0948 |
| Max drawdown | 7.19% | 22.11% | 32.47% |
| Max DD Monte Carlo p50 / p95 | n/d / n/d | n/d / n/d | n/d / n/d |
| Sharpe | n/d | n/d | n/d |
| Sortino | n/d | n/d | n/d |
| Serie massima di perdite | 3 | 6 | 6 |
| Durata media (min) | 68 | 55 | 55 |
| Commissioni totali (SOL) | 0.0013 | 0.0029 | 0.0036 |
| Slippage totale (SOL) | 0.0009 | 0.0029 | 0.0045 |
| Capitale massimo investito (SOL) | 0.1023 | 0.3249 | 0.4840 |
| Ordini falliti | 1 | 0 | 0 |
| Uscite su token morti | 0 | 0 | 0 |
| Robusto? | NO | NO | NO |

### conservative
- Segnali generati: 218
- Sharpe/Sortino: non significativi: solo 0 giorni di storico (minimo 30)
- Robustezza: campione troppo piccolo: 3 trade (minimo 100); trade generati con soli dati OHLCV (feature on-chain/social non disponibili)
- Motivi di uscita: STOP_GAP=1, STOP_LOSS=1, TAKE_PROFIT_1=1, TRAILING_STOP=1
- Segnali/ordini scartati: rifiutato dal risk manager: numero massimo di posizioni (199); rifiutato dal risk manager: trading in pausa fino alle 06:57 UTC (9); rifiutato dal risk manager: limite di perdita giornaliero raggiunto (7)
- ⚠️ feature point-in-time non disponibili: modalità ridotta (solo OHLCV)

### moderate
- Segnali generati: 194
- Sharpe/Sortino: non significativi: solo 0 giorni di storico (minimo 30)
- Robustezza: campione troppo piccolo: 6 trade (minimo 100); trade generati con soli dati OHLCV (feature on-chain/social non disponibili)
- Motivi di uscita: STOP_LOSS=4, TAKE_PROFIT_1=2, TRAILING_STOP=2
- Segnali/ordini scartati: rifiutato dal risk manager: numero massimo di posizioni (181); rifiutato dal risk manager: trading in pausa fino alle 04:51 UTC (7)
- ⚠️ feature point-in-time non disponibili: modalità ridotta (solo OHLCV)

### aggressive
- Segnali generati: 194
- Sharpe/Sortino: non significativi: solo 0 giorni di storico (minimo 30)
- Robustezza: campione troppo piccolo: 6 trade (minimo 100); trade generati con soli dati OHLCV (feature on-chain/social non disponibili)
- Motivi di uscita: STOP_LOSS=4, TAKE_PROFIT_1=2, TRAILING_STOP=2
- Segnali/ordini scartati: rifiutato dal risk manager: numero massimo di posizioni (181); rifiutato dal risk manager: trading in pausa fino alle 03:56 UTC (6); rifiutato dal risk manager: limite di perdita giornaliero raggiunto (1)
- ⚠️ feature point-in-time non disponibili: modalità ridotta (solo OHLCV)

## Avvertenze
- Le metriche sono calcolate con commissioni, slippage, impatto AMM, latenza e transazioni fallite simulate.
- Un risultato è considerato robusto solo con ≥100 trade e intervallo di confidenza dell'expectancy > 0.
- Risultati passati non garantiscono risultati futuri; il regime del mercato memecoin cambia rapidamente.