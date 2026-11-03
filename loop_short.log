# Studio storico: entrate a breve termine sulla curva (loopholetape, 27 set - 27 ott 2026)

Pre-registrazione (testo originale):

```
(written before looking at any result):
  * universe and price as in loop_curve (classic launches, settled, decoder complete, lag <= 10 s, rows before the
    migration; price from the real SOL reserve with 30 SOL virtual);
  * entry: the first row between 1 and 5 minutes of age that meets the rule (one trade per token);
  * rules: M0 any row (reference); M1 momentum: reserve up >= 30% since the previous row and >= 3 SOL;
    M2 pullback: reserve <= 60% of the earlier maximum, which was >= 5 SOL; M3 deep pullback: <= 40% of an
    earlier maximum >= 10 SOL; M4 flow: >= 20 more buys than at the previous row; M5 pullback + flow: M2 and
    >= 10 more buys;
  * exits at a fixed time after the entry: the first row at least 60 s, 180 s or 600 s later; a token that
    graduated before that moment exits at the graduation price minus 30% (pool haircut); a token with no later
    row and no graduation is dropped and counted (the sampling stops at 15 minutes of age);
  * costs as in loop_curve (3% latency, 1.25% fee per side, 1% priority fees);
  * statistics: bootstrap 95% interval, Benjamini-Hochberg over all tests, verdict needs both halves positive.
```
Righe candidate (1-5 min): 1,261,483 di 329,829 token.
| regola | uscita_s | n | scartati | media_% | IC95_basso_% | IC95_alto_% | p | mediana_% | vincenti_% | 1a_metà_% | 2a_metà_% | q_BH | verdetto |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| M0 qualsiasi riga 1-5 min | 60 | 328494 | 1335 | -7.767 | -7.828 | -7.707 | 1 | -6.325 | 8.471 | -7.618 | -7.946 | 1 | non dimostrata |
| M0 qualsiasi riga 1-5 min | 180 | 322104 | 7725 | -9.982 | -10.08 | -9.885 | 1 | -6.776 | 7.451 | -9.58 | -10.46 | 1 | non dimostrata |
| M0 qualsiasi riga 1-5 min | 600 | 90375 | 239454 | -10.68 | -10.97 | -10.38 | 1 | -9.665 | 6.726 | -9.43 | -12.04 | 1 | non dimostrata |
| M1 slancio: riserva +30% dalla riga prima e >= 3 SOL | 60 | 53738 | 541 | -9.725 | -9.996 | -9.447 | 1 | -9.816 | 28.91 | -9.308 | -10.22 | 1 | non dimostrata |
| M1 slancio: riserva +30% dalla riga prima e >= 3 SOL | 180 | 50660 | 3619 | -16.09 | -16.54 | -15.64 | 1 | -25.16 | 23.5 | -15.4 | -16.9 | 1 | non dimostrata |
| M1 slancio: riserva +30% dalla riga prima e >= 3 SOL | 600 | 15274 | 39005 | -11.75 | -12.92 | -10.54 | 1 | -31.2 | 23.08 | -9.229 | -14.52 | 1 | non dimostrata |
| M2 ritracciamento: <= 60% di un massimo >= 5 SOL | 60 | 87682 | 983 | -8.02 | -8.134 | -7.897 | 1 | -6.643 | 8.027 | -8.049 | -7.991 | 1 | non dimostrata |
| M2 ritracciamento: <= 60% di un massimo >= 5 SOL | 180 | 82105 | 6560 | -10.89 | -11.07 | -10.71 | 1 | -9.438 | 5.784 | -10.56 | -11.23 | 1 | non dimostrata |
| M2 ritracciamento: <= 60% di un massimo >= 5 SOL | 600 | 19436 | 69229 | -10.67 | -11.35 | -9.978 | 1 | -13.86 | 3.998 | -9.33 | -11.88 | 1 | non dimostrata |
| M3 ritracciamento forte: <= 40% di un massimo >= 10 SOL | 60 | 45832 | 605 | -8.137 | -8.297 | -7.982 | 1 | -6.843 | 7.259 | -8.291 | -7.975 | 1 | non dimostrata |
| M3 ritracciamento forte: <= 40% di un massimo >= 10 SOL | 180 | 42444 | 3993 | -11.14 | -11.39 | -10.89 | 1 | -9.815 | 4.936 | -10.76 | -11.53 | 1 | non dimostrata |
| M3 ritracciamento forte: <= 40% di un massimo >= 10 SOL | 600 | 9003 | 37434 | -10.92 | -12 | -9.829 | 1 | -14.42 | 3.288 | -10.19 | -11.57 | 1 | non dimostrata |
| M4 flusso: >= 20 acquisti in più dalla riga prima | 60 | 75195 | 341 | -9.728 | -9.953 | -9.509 | 1 | -8.357 | 24.26 | -9.378 | -10.13 | 1 | non dimostrata |
| M4 flusso: >= 20 acquisti in più dalla riga prima | 180 | 73456 | 2080 | -15.02 | -15.36 | -14.66 | 1 | -18.27 | 18.9 | -14.62 | -15.49 | 1 | non dimostrata |
| M4 flusso: >= 20 acquisti in più dalla riga prima | 600 | 23767 | 51769 | -12.53 | -13.47 | -11.59 | 1 | -25.62 | 18.31 | -9.76 | -15.41 | 1 | non dimostrata |
| M5 ritracciamento + flusso (M2 e >= 10 acquisti in più) | 60 | 50964 | 500 | -8.423 | -8.624 | -8.231 | 1 | -7.375 | 11 | -8.463 | -8.381 | 1 | non dimostrata |
| M5 ritracciamento + flusso (M2 e >= 10 acquisti in più) | 180 | 48073 | 3391 | -11.96 | -12.25 | -11.66 | 1 | -12.25 | 7.603 | -11.59 | -12.35 | 1 | non dimostrata |
| M5 ritracciamento + flusso (M2 e >= 10 acquisti in più) | 600 | 11910 | 39554 | -11.37 | -12.31 | -10.36 | 1 | -16.4 | 5.231 | -10.32 | -12.32 | 1 | non dimostrata |

Lordo = senza costi: per capire se il problema sono i costi o la direzione, la stessa tabella senza costi:
| regola | uscita_s | n | media_lorda_% | mediana_lorda_% |
|---|---|---|---|---|
| M0 qualsiasi riga 1-5 min | 60 | 328494 | -1.524 | 0 |
| M0 qualsiasi riga 1-5 min | 180 | 322104 | -3.863 | -0.4767 |
| M0 qualsiasi riga 1-5 min | 600 | 90375 | -4.605 | -3.528 |
| M1 slancio: riserva +30% dalla riga prima e >= 3 SOL | 60 | 53738 | -3.591 | -3.687 |
| M1 slancio: riserva +30% dalla riga prima e >= 3 SOL | 180 | 50660 | -10.32 | -19.89 |
| M1 slancio: riserva +30% dalla riga prima e >= 3 SOL | 600 | 15274 | -5.729 | -26.28 |
| M2 ritracciamento: <= 60% di un massimo >= 5 SOL | 60 | 87682 | -1.791 | -0.3359 |
| M2 ritracciamento: <= 60% di un massimo >= 5 SOL | 180 | 82105 | -4.817 | -3.289 |
| M2 ritracciamento: <= 60% di un massimo >= 5 SOL | 600 | 19436 | -4.59 | -7.961 |
| M3 ritracciamento forte: <= 40% di un massimo >= 10 SOL | 60 | 45832 | -1.914 | -0.547 |
| M3 ritracciamento forte: <= 40% di un massimo >= 10 SOL | 180 | 42444 | -5.082 | -3.687 |
| M3 ritracciamento forte: <= 40% di un massimo >= 10 SOL | 600 | 9003 | -4.853 | -8.553 |
| M4 flusso: >= 20 acquisti in più dalla riga prima | 60 | 75195 | -3.595 | -2.147 |
| M4 flusso: >= 20 acquisti in più dalla riga prima | 180 | 73456 | -9.189 | -12.62 |
| M4 flusso: >= 20 acquisti in più dalla riga prima | 600 | 23767 | -6.55 | -20.38 |
| M5 ritracciamento + flusso (M2 e >= 10 acquisti in più) | 60 | 50964 | -2.216 | -1.109 |
| M5 ritracciamento + flusso (M2 e >= 10 acquisti in più) | 180 | 48073 | -5.953 | -6.256 |
| M5 ritracciamento + flusso (M2 e >= 10 acquisti in più) | 600 | 11910 | -5.329 | -10.64 |

