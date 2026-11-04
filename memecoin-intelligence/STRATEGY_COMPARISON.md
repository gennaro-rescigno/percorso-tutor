# STRATEGY_COMPARISON.md — Confronto e classifica delle strategie

Generato da `research/ranking/ranking.py` a partire da `research/ranking/registry.csv` (cifre copiate dai report degli studi nel branch `research-results`). Il punteggio premia la credibilità statistica, non il rendimento più alto: formula e pesi nel docstring di `ranking.py`.

Strategie valutate: **36** · robuste: **0** · promettenti ma non dimostrate: **7** · scartate: **28**.

## Nuovi lanci

| Pos. | Strategia | Studio | Periodo fuori campione | N | Risultato | IC 95% | Max DD | Verifiche | Stato | Punteggio |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Copia perfetta allo stesso prezzo del wallet copiato | jocry_copy2 | 2026-06-05/07-14 | 4,163 | +9.1% a operazione | – | – | 0/1 | positiva ma non eseguibile gratis | 26.8 |
| 2 | Portafoglio principale dal vivo (strategie B-E) | paper trading | 2026-11-01/11-03 | 18 | +0.5% ROI | – | -4% | 0/1 | promettente, non dimostrata | 26.7 |
| 3 | Laboratorio dal vivo (A-C senza limiti) | paper trading | 2026-11-02/11-03 | 33 | -8.2% ROI | – | -9% | 0/1 | scartata | 18.7 |
| 4 | Modello che sceglie quando entrare per 5-10 minuti | loop_model2 | 2026-08-31/10-27 | 1,260,000 | -7.0% a operazione | – | – | 0/1 | scartata | 17.5 |
| 5 | Entrate brevi sulla curva 1-5 min (6 regole x 3 tenute) | loop_short | 2026-08-31/10-27 | 330,000 | -8.0% a operazione | – | – | 0/1 | scartata | 17.5 |
| 6 | Comprare sulla curva e tenere fino al diploma (7 regole) | loop_curve | 2026-08-31/10-27 | 547,350 | -13.0% a operazione | – | – | 0/1 | scartata | 17.5 |
| 7 | Comprare dopo il diploma (36 combinazioni) | postgrad | 2026-06/10 | 32,765 | – | – | – | 0/1 | scartata | 17.5 |
| 8 | Copiare i 50 wallet migliori con 3 s di ritardo | jocry_copy | 2026-06-05/07-14 | 4,163 | -5.9% a operazione | – | – | 0/1 | scartata | 17.5 |
| 9 | Copiare i 50 wallet migliori con 10 s di ritardo | jocry_copy | 2026-06-05/07-14 | 4,163 | -6.5% a operazione | – | – | 0/1 | scartata | 17.5 |
| 10 | Esperimento x_curve (curva organica) dal vivo | paper trading | 2026-11-02/11-03 | 26 | -10.1% ROI | – | – | 0/1 | scartata | 12.2 |
| 11 | Copia dei wallet migliori con 1 s di ritardo | jocry_copy2 | 2026-06-05/07-14 | 4,163 | -5.4% a operazione | – | – | 0/1 | scartata | 8.8 |

## Memecoin esistenti

| Pos. | Strategia | Studio | Periodo fuori campione | N | Risultato | IC 95% | Max DD | Verifiche | Stato | Punteggio |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Trend sulle memecoin quotate media 50 giorni | meme_trend | 2022-01/2026-10 | 1,474 | +4.6% annuo | Sharpe [-0.78, 1.31] | -60% | 1/2 | promettente, non dimostrata | 41.8 |
| 2 | Hype con BTC sopra la media di 50 giorni (3 giorni) | crypto_daily + crypto_daily2 | 2022-01/2026-10 | 1,216 | +11.7% annuo | Sharpe [-0.43, 1.32] | -51% | 0/3 | promettente, non dimostrata | 39.7 |
| 3 | Regole sui token quotati PumpSwap (7 regole x 3 tenute) | fly_rules | 2026-09-14/09-21 | 297 | +0.0% a operazione | [-6.3, 10.8] | – | 0/1 | promettente, non dimostrata | 23.3 |
| 4 | Modello portabile per token quotati 1 e 4 ore | dex_model | 2026-06/09 | 1,006 | -2.9% a operazione | [-15.5, 17.2] | – | 0/1 | scartata | 20.0 |
| 5 | Hype senza filtro (3 giorni) | crypto_daily | 2022-01/2026-10 | 1,725 | -20.0% annuo | – | – | 0/1 | scartata | 17.5 |
| 6 | Comprare i cali in una moneta in salita (3 giorni) | crypto_daily | 2022-01/2026-10 | 2,941 | -58.0% annuo | – | – | 0/1 | scartata | 17.5 |
| 7 | Modello che impara quando entrare (1-3 giorni) | crypto_daily | 2022-01/2026-10 | 4,446 | -65.0% annuo | – | – | 0/1 | scartata | 17.5 |
| 8 | Le 5 più forti degli ultimi 3 giorni | crypto_daily | 2022-01/2026-10 | 2,550 | -44.0% annuo | – | – | 0/1 | scartata | 17.5 |
| 9 | Rottura dei massimi con volume (3 giorni) | crypto_daily | 2022-01/2026-10 | 1,919 | -13.0% annuo | – | – | 0/1 | scartata | 17.5 |
| 10 | Fornire liquidità ai pool PumpSwap (33 combinazioni) | dex_lp | 2026-06/09 | 340 | -3.7% a operazione | [-5.2, -2.1] | – | 0/1 | scartata | 15.9 |
| 11 | Trend sulle memecoin quotate candele 4 ore | meme_trend | 2022-01/2026-10 | 9,762 | -11.1% annuo | Sharpe [-0.96, 1.04] | -75% | 0/2 | scartata | 13.8 |
| 12 | Trend sulle memecoin quotate media 20 giorni | meme_trend | 2022-01/2026-10 | 2,593 | -14.3% annuo | Sharpe [-1.11, 1.05] | -75% | 0/2 | scartata | 13.8 |

## Short

| Pos. | Strategia | Studio | Periodo fuori campione | N | Risultato | IC 95% | Max DD | Verifiche | Stato | Punteggio |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Vendere i nuovi listing al secondo giorno (3 giorni) | crypto_short | 2022-01/2026-10 | 526 | +3.7% annuo | Sharpe [-0.66, 1.09] | -43% | 0/2 | promettente, non dimostrata | 33.0 |
| 2 | Vendere dopo l'hype con BTC debole | crypto_short | 2022-01/2026-10 | 755 | -5.3% annuo | Sharpe [-0.85, 0.56] | -57% | 0/2 | scartata | 16.1 |
| 3 | Vendere quando il funding è alto | crypto_short | 2022-01/2026-10 | 1,562 | -26.0% annuo | – | -80% | 0/2 | scartata | 13.0 |
| 4 | Seguire la debolezza con BTC in calo | crypto_short | 2022-01/2026-10 | 2,221 | -23.2% annuo | – | -86% | 0/2 | scartata | 12.1 |
| 5 | Vendere dopo l'hype | crypto_short | 2022-01/2026-10 | 2,078 | -43.3% annuo | – | -96% | 0/2 | scartata | 10.5 |
| 6 | Vendere le più salite | crypto_short | 2022-01/2026-10 | 5,164 | -44.7% annuo | – | -98% | 0/2 | scartata | 10.3 |

## Funding

| Pos. | Strategia | Studio | Periodo fuori campione | N | Risultato | IC 95% | Max DD | Verifiche | Stato | Punteggio |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Incassare il funding su BTC ed ETH (3 giorni) | crypto_carry | 2022-01/2026-10 | 379 | -1.5% annuo | – | -7% | 0/2 | scartata | 20.0 |
| 2 | Incassare il funding nell'euforia >= 0.10% (3 giorni) | crypto_carry | 2022-01/2026-10 | 526 | -2.7% annuo | – | -21% | 0/2 | scartata | 20.0 |
| 3 | Incassare il funding persistente (3 giorni) | crypto_carry | 2022-01/2026-10 | 569 | -6.7% annuo | – | -28% | 0/2 | scartata | 19.9 |
| 4 | Incassare il funding >= 0.03% (3 giorni) | crypto_carry | 2022-01/2026-10 | 5,154 | -39.6% annuo | – | -91% | 0/2 | scartata | 11.3 |

## Crypto affermate

| Pos. | Strategia | Studio | Periodo fuori campione | N | Risultato | IC 95% | Max DD | Verifiche | Stato | Punteggio |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Trend BTC + ETH + SOL sopra la media di 50 giorni | crypto_trend + crypto_trend2 + crypto_trend_trades | 2022-01/2026-10 | 141 | +31.2% annuo | Sharpe [-0.09, 1.83] | -42% | 3/3 | promettente, non dimostrata | 70.3 |
| 2 | BTC sopra la media di 50 giorni | crypto_trend | 2022-01/2026-10 | 51 | +20.0% annuo | – | -51% | 2/3 | promettente, non dimostrata | 52.9 |
| 3 | Momentum tra monete (le 5 migliori ogni settimana) | crypto_trend | 2022-01/2026-10 | – | -29.0% annuo | – | -100% | 0/2 | scartata | 0.0 |

## Come leggere

- **robusta**: intervallo di confidenza fuori campione sopra zero, almeno 2 verifiche su 3 superate, risultato positivo in almeno il 60% dei periodi, eseguibile con strumenti gratuiti.
- **promettente, non dimostrata**: media positiva fuori campione ma senza significatività o robustezza: non va in produzione, si può solo osservare in paper trading.
- **positiva ma non eseguibile gratis**: il vantaggio esiste solo con infrastruttura a pagamento (velocità).
- **scartata**: media fuori campione negativa o non misurabile.
- Le note di ogni riga (nel CSV) spiegano il limite principale.
