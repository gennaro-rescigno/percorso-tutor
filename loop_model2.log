# Verifica del modello a 10 minuti: sopravvissuti, ipotesi sul diploma, divisione netta (loopholetape)

```
loop_model found the 10-minute selections positive (+22% to +92% per trade). Before believing it, three checks
written BEFORE running them:
  * survivorship: in loop_model a decision without a sampled row 10 minutes later was DROPPED (about two thirds of
    the tokens at 10 minutes); here it is kept and valued at the token's final reserve (`terminal_rs`), which for
    a dead curve is close to its price at that time (conservative: never better than the truth for a dying token);
  * graduation: an exit at the graduation price minus 30% (as before) and minus 50%;
  * a single clean split: trained on the first half of the days, judged only on the second half (no retraining);
  * what the model looks at: permutation importance on the test half.
Everything else (features, model, costs, selections, statistics) as in loop_model.
```

## Cosa guarda il modello (10 minuti, importanza per permutazione sulla seconda metà)
| caratteristica | importanza |
|---|---|
| f_rs | 0.3745 |
| dd | 0.006909 |
| hour | 0.004924 |
| f_n_buys | 0.003943 |
| copy_rank | 0.003602 |
| f_insider_share | 0.00325 |
| f_rep_n | 0.003141 |
| f_rep_rug | 0.002268 |
| f_dev_share | 0.001687 |
| d_rs | 0.001302 |
| dev_buy_sol | 0.001164 |
| d_buys | 0.0009197 |

Profilo dei momenti scelti (1% più alto) rispetto a tutti (mediane):
| caratteristica | scelti | tutti |
|---|---|---|
| age_s | 189 | 181.5 |
| f_rs | 0.4348 | 0.7053 |
| d_rs | -1e-05 | 0 |
| r_rs | -0.02082 | 0 |
| dd | 0.2511 | 0.5716 |
| prior_max | 30.73 | 2.815 |
| f_n_buys | 132 | 22 |
| d_buys | 12 | 0 |
| buys_per_min | 45.21 | 8.211 |
| rs_per_min | 0.1694 | 0.2294 |
| f_dev_share | 0.01 | 0 |
| f_insider_share | 0.03 | 0 |
| f_bundle_wallets | 5 | 4 |
| f_rep_n | 0 | 24 |
| f_rep_rug | 0.7727 | 0.9407 |
| f_rep_grad | 0.1667 | 0.01023 |
| flag_creator_sold | 0 | 1 |
| flag_bundle_dumped | 1 | 1 |
| flag_curve_drained | 1 | 1 |
| flag_serial_rugger_creator | 0 | 1 |
| flag_warm_launch | 0 | 0 |
| dev_buy_sol | 0.9257 | 1.966 |
| copy_rank | 6 | 8 |
| hour | 10 | 14 |


## Risultati sulla seconda metà dei giorni (mai vista dal modello)
| tenuta_min | taglio_diploma | selezione | n | media_% | IC95_basso_% | IC95_alto_% | p | mediana_% | vincenti_% | uscite_diploma_% | uscite_valore_finale_% | q_BH | verdetto |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 5 | 0.3 | P0 ogni token | 150547 | -13.19 | -13.38 | -13 | 1 | -9.796 | 4.714 | 0.8203 | 19.39 | 1 | non dimostrata |
| 5 | 0.3 | P1 previsto > 0 | 636 | -11.39 | -17.99 | -4.191 | 0.998 | -49.66 | 33.49 | 7.547 | 36.95 | 1 | non dimostrata |
| 5 | 0.3 | P2 5% più alto | 9497 | -7.113 | -7.71 | -6.527 | 1 | -6.325 | 4.117 | 0.7265 | 13.97 | 1 | non dimostrata |
| 5 | 0.3 | P3 1% più alto | 2494 | -9.689 | -11.83 | -7.431 | 1 | -6.558 | 13.79 | 2.767 | 25.74 | 1 | non dimostrata |
| 5 | 0.5 | P0 ogni token | 150547 | -13.54 | -13.73 | -13.36 | 1 | -9.864 | 4.512 | 0.8203 | 19.39 | 1 | non dimostrata |
| 5 | 0.5 | P1 previsto > 0 | 445 | -18.71 | -25.93 | -11.47 | 1 | -49.75 | 30.79 | 5.393 | 39.33 | 1 | non dimostrata |
| 5 | 0.5 | P2 5% più alto | 8758 | -7.066 | -7.578 | -6.562 | 1 | -6.325 | 3.243 | 0.4111 | 13.93 | 1 | non dimostrata |
| 5 | 0.5 | P3 1% più alto | 2341 | -9.271 | -11.1 | -7.351 | 1 | -6.515 | 10.29 | 1.538 | 24.56 | 1 | non dimostrata |
| 10 | 0.3 | P0 ogni token | 150547 | -15.27 | -15.51 | -15.03 | 1 | -12.04 | 2.403 | 1.15 | 71.17 | 1 | non dimostrata |
| 10 | 0.3 | P1 previsto > 0 | 743 | -10.19 | -17.75 | -2.819 | 0.9965 | -75.55 | 32.84 | 12.79 | 71.2 | 1 | non dimostrata |
| 10 | 0.3 | P2 5% più alto | 7229 | -6.892 | -7.851 | -5.997 | 1 | -6.325 | 5.077 | 1.881 | 63.02 | 1 | non dimostrata |
| 10 | 0.3 | P3 1% più alto | 2141 | -8.986 | -11.99 | -5.954 | 1 | -6.646 | 15.97 | 6.119 | 70.53 | 1 | non dimostrata |
| 10 | 0.5 | P0 ogni token | 150547 | -15.85 | -16.08 | -15.61 | 1 | -12.16 | 2.153 | 1.15 | 71.17 | 1 | non dimostrata |
| 10 | 0.5 | P1 previsto > 0 | 454 | -13.47 | -22.62 | -4.28 | 0.999 | -73.93 | 33.26 | 13.66 | 70.7 | 1 | non dimostrata |
| 10 | 0.5 | P2 5% più alto | 7473 | -6.87 | -7.538 | -6.161 | 1 | -6.325 | 3.118 | 1.084 | 62.53 | 1 | non dimostrata |
| 10 | 0.5 | P3 1% più alto | 2086 | -9.111 | -11.48 | -6.741 | 1 | -6.527 | 10.02 | 3.739 | 71.09 | 1 | non dimostrata |

