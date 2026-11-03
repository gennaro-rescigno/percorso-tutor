# Studio storico: regole semplici sui token già quotati su PumpSwap (aprile-settembre 2026)

Pre-registrazione (testo originale):

```
(written before looking at any result):
  * checkpoints at the end of every hour after the graduation in which the token traded; one trade per token and
    rule: the first checkpoint that meets the rule;
  * rules (pool SOL reserve >= 20 SOL in all of them):
      L0 any traded hour from the 1st hour (reference);
      L1 momentum: close >= 1.5x the previous hour's close;
      L2 strong momentum: close >= 2x the close 3 hours before;
      L3 pullback: age >= 6 h, close <= 50% of the highest price since the graduation, >= 5 SOL traded in the hour;
      L4 survivor: age >= 24 h, reserve >= 50 SOL, >= 20 traders in the hour;
      L5 survivor without insider selling: L4 and no insider or top-holder selling in the last 6 hours;
      L6 accumulation: age >= 2 h, buys >= 2x sells (SOL) in the hour, >= 5 SOL bought;
  * exits after 1, 4 and 24 hours at the last price at or before that moment (no trade = unchanged price);
  * costs for a 0.1 SOL position: the pool's own fee rate on each side (1% when missing), price impact
    0.1 / reserve on entry and position value / reserve on exit, 1% priority fees;
  * statistics: mean with bootstrap 95% interval, Benjamini-Hochberg over all tests, verdict "positive and stable"
    only with q < 0.05 and a positive mean in at least 4 of the months covered; a gross (no cost) mean is shown too.
```
Candele estratte: 1,033,011 di 28,721 token, dal 2026-09-14 al 2026-09-21.
Checkpoint orari: 152,656 di 28,721 token.
Vita (ultima ora con scambi dopo il diploma): mediana 2 h; ancora scambiato dopo 24 h: 32.0%.
| regola | tenuta_h | n | media_% | IC95_basso_% | IC95_alto_% | p | mediana_% | vincenti_% | lorda_media_% | lorda_mediana_% | mesi_positivi | q_BH | verdetto |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| L0 qualsiasi ora | 1 | 9073 | -5.699 | -6.125 | -5.228 | 1 | -3.823 | 3.836 | -2.022 | 0 | 0/1 | 1 | non dimostrata |
| L0 qualsiasi ora | 4 | 9073 | -6.973 | -7.434 | -6.534 | 1 | -3.871 | 5.423 | -3.333 | 0 | 0/1 | 1 | non dimostrata |
| L0 qualsiasi ora | 24 | 9073 | -8.584 | -9.141 | -8.018 | 1 | -3.959 | 6.723 | -4.975 | 0 | 0/1 | 1 | non dimostrata |
| L1 slancio: x1,5 in un'ora | 1 | 172 | -12.82 | -25.01 | 3.977 | 0.934 | -17.56 | 22.67 | -9.511 | -14.52 | 0/1 | 1 | non dimostrata |
| L1 slancio: x1,5 in un'ora | 4 | 172 | -25.29 | -32.72 | -17.39 | 1 | -26.54 | 20.93 | -22.38 | -23.21 | 0/1 | 1 | non dimostrata |
| L1 slancio: x1,5 in un'ora | 24 | 172 | -42.53 | -49.7 | -35.67 | 1 | -44.51 | 13.95 | -40.05 | -42.18 | 0/1 | 1 | non dimostrata |
| L2 slancio forte: x2 in 3 ore | 1 | 133 | -0.3408 | -13.74 | 21.93 | 0.5855 | -4.785 | 23.31 | 3.34 | -0.9573 | 0/1 | 1 | non dimostrata |
| L2 slancio forte: x2 in 3 ore | 4 | 133 | -17.04 | -23.13 | -11.39 | 1 | -12.81 | 25.56 | -13.9 | -8.811 | 0/1 | 1 | non dimostrata |
| L2 slancio forte: x2 in 3 ore | 24 | 133 | -28.77 | -36.5 | -21.04 | 1 | -25.2 | 18.05 | -25.88 | -22.22 | 0/1 | 1 | non dimostrata |
| L3 ritracciamento: <= 50% del massimo, età >= 6 h | 1 | 297 | 0.01919 | -6.309 | 10.78 | 0.555 | -3.858 | 27.95 | 3.726 | -0.01012 | 1/1 | 1 | non dimostrata |
| L3 ritracciamento: <= 50% del massimo, età >= 6 h | 4 | 297 | -7.938 | -11.81 | -3.61 | 1 | -4.961 | 33 | -4.47 | -1.183 | 0/1 | 1 | non dimostrata |
| L3 ritracciamento: <= 50% del massimo, età >= 6 h | 24 | 297 | -14.7 | -19.8 | -8.893 | 1 | -9.951 | 30.3 | -11.4 | -6.359 | 0/1 | 1 | non dimostrata |
| L4 sopravvissuto: età >= 24 h, riserva >= 50, >= 20 trader | 1 | 448 | -4.493 | -5.43 | -3.635 | 1 | -3.228 | 14.29 | -1.456 | 0 | 0/1 | 1 | non dimostrata |
| L4 sopravvissuto: età >= 24 h, riserva >= 50, >= 20 trader | 4 | 448 | -8.078 | -10.28 | -5.903 | 1 | -3.231 | 25.89 | -4.884 | 0 | 0/1 | 1 | non dimostrata |
| L4 sopravvissuto: età >= 24 h, riserva >= 50, >= 20 trader | 24 | 448 | -8.996 | -11.8 | -6.218 | 1 | -3.647 | 30.58 | -5.823 | -0.2718 | 0/1 | 1 | non dimostrata |
| L5 L4 senza vendite di insider/top holder in 6 h | 1 | 205 | -5.173 | -7.084 | -3.625 | 1 | -3.227 | 11.71 | -2.107 | 0 | 0/1 | 1 | non dimostrata |
| L5 L4 senza vendite di insider/top holder in 6 h | 4 | 205 | -6.4 | -8.986 | -4.043 | 1 | -3.012 | 24.39 | -2.922 | 0.02041 | 0/1 | 1 | non dimostrata |
| L5 L4 senza vendite di insider/top holder in 6 h | 24 | 205 | -4.367 | -8.72 | 0.2254 | 0.969 | -3.282 | 32.68 | -0.8318 | 0 | 0/1 | 1 | non dimostrata |
| L6 accumulo: acquisti >= 2x vendite, età >= 2 h | 1 | 807 | -4.364 | -5.842 | -2.781 | 1 | -3.191 | 25.28 | -1.114 | 0 | 0/1 | 1 | non dimostrata |
| L6 accumulo: acquisti >= 2x vendite, età >= 2 h | 4 | 807 | -7.446 | -10.02 | -4.986 | 1 | -3.818 | 25.77 | -4.347 | -0.5027 | 0/1 | 1 | non dimostrata |
| L6 accumulo: acquisti >= 2x vendite, età >= 2 h | 24 | 807 | -17.34 | -20.45 | -14.11 | 1 | -8.974 | 21.56 | -14.44 | -5.674 | 0/1 | 1 | non dimostrata |

