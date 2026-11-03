# Studio storico: un modello impara quando entrare per 5-10 minuti? (loopholetape, set-ott 2026)

Pre-registrazione (testo originale):

```
(written before looking at any result):
  * decision points: every sampled minute between 1 and 5 minutes of age of every classic launch;
  * features known at that moment only: age, real SOL reserve and its change since the previous minute, distance
    from the highest reserve so far, buys so far and their change, buys and reserve per minute, creator share,
    insider share, block-0 bundle wallets, creator history (launches, rug and graduation rates), the observed flags
    (creator sold, bundle dumped, curve drained, serial rugger, warm launch), creator's first buy, how many earlier
    launches used the same name, hour of the day (UTC). The API's own served probabilities are NOT used;
  * targets: net return of a 0.1 SOL trade held 5 and 10 minutes (exit at the first sampled row at least that much
    later; a graduation in between exits at the graduation price minus 30%), with the costs of loop_curve
    (3% latency, 1.25% fee per side, 1% priority fees);
  * model: gradient-boosted trees (scikit-learn HistGradientBoostingRegressor, fixed settings), target clipped to
    [-100%, +200%]; walk-forward: trained only on days before the tested ones (first 7 days only for training),
    retrained every 3 days;
  * selections, one trade per token per day (its first selected minute): P0 every token (reference),
    P1 predicted net return > 0, P2 prediction in the top 5% of the training predictions, P3 top 1%;
  * statistics: bootstrap 95% interval of the mean, Benjamini-Hochberg over all tests, verdict "positive and stable"
    only with q < 0.05 and both halves of the tested days positive.
```
Momenti di decisione (1-5 minuti di vita): 1,261,483 di 547,350 token.
- tenuta 5 min: correlazione di rango media tra previsione e risultato fuori campione = 0.614 (8 blocchi di test)
- tenuta 10 min: correlazione di rango media tra previsione e risultato fuori campione = 0.612 (8 blocchi di test)
| selezione | tenuta_min | n | media_% | IC95_basso_% | IC95_alto_% | p | mediana_% | vincenti_% | previsto_medio_% | 1a_metà_% | 2a_metà_% | q_BH | verdetto |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P0 ogni token (riferimento) | 5 | 186837 | -12.36 | -12.51 | -12.21 | 1 | -8.902 | 5.831 | -12.96 | -12.05 | -12.71 | 1 | non dimostrata |
| P1 rendimento previsto > 0 | 5 | 553 | -9.071 | -14.58 | -3.375 | 0.9995 | -23.55 | 37.97 | 4.738 | -9.074 | -9.066 | 1 | non dimostrata |
| P2 previsione nel 5% più alto | 5 | 13570 | -6.118 | -6.57 | -5.643 | 1 | -6.325 | 5.018 | -5.471 | -5.964 | -6.389 | 1 | non dimostrata |
| P3 previsione nell'1% più alto | 5 | 2971 | -8.03 | -9.662 | -6.459 | 1 | -6.576 | 17.27 | -3.293 | -8.34 | -7.641 | 1 | non dimostrata |
| P0 ogni token (riferimento) | 10 | 62295 | -10.41 | -10.79 | -10.05 | 1 | -10.2 | 7.209 | -11.66 | -9.433 | -11.42 | 1 | non dimostrata |
| P1 rendimento previsto > 0 | 10 | 4602 | 21.69 | 18.9 | 24.58 | 0.0005 | -6.325 | 45.76 | 26.05 | 26.1 | 16.3 | 0.001333 | positiva e stabile |
| P2 previsione nel 5% più alto | 10 | 4288 | 24.21 | 21.26 | 27.27 | 0.0005 | -6.325 | 47.55 | 28.27 | 31.34 | 16.44 | 0.001333 | positiva e stabile |
| P3 previsione nell'1% più alto | 10 | 757 | 91.83 | 84.05 | 99.57 | 0.0005 | 103.8 | 73.05 | 98.39 | 103 | 78.44 | 0.001333 | positiva e stabile |

`previsto_medio_%` = quanto il modello si aspettava in media sulle operazioni scelte: se è molto sopra il risultato reale, il modello si illude (sovra-adattamento).
