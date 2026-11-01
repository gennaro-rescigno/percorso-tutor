# Strategie, gestione delle posizioni e del capitale

Implementazione: `strategies/library.py`, `risk_management/{profiles,sizing,exits,manager}.py`.
Tutte le soglie sono parametri modificabili dal Backtest Lab o da CLI.

## Strategie di ingresso

| | Timeframe | Condizioni principali (default) | Stop strutturale |
|---|---|---|---|
| **A – Early Entry** | 1m | età 15 min–6 h; score ≥ 68; liquidità ≥ 20k $; accelerazione volume (5m×12/1h) ≥ 1,3; prezzo 1h tra +5% e +300%; buy ratio 0,52–0,80; ≥ 50 compratori unici/h in crescita; wash ≤ 0,5 | minimo 15 candele −3% |
| **B – Momentum** | 5m | età ≥ 3 h; breakout sopra il massimo di 48 candele; volume ≥ 2× media; EMA20 > EMA50; prezzo ≤ 30% sopra EMA20 (no inseguimento); variazione 1h ≤ 150% | max(livello di breakout −8%, close − 2,5 ATR) |
| **C – Pullback** | 5m | impulso ≥ +80% nelle ultime 12 h; ritracciamento 30–62%; volume della correzione ≤ 0,7× impulso; ripresa: close > EMA9 e > massimo precedente con volume | minimo del pullback −3% |
| **D – Accumulazione** | 15m | età ≥ 6 h; range ≤ 30% su 8 h; volume crescente a prezzo stabile (≥ 1,3×); holder e liquidità in crescita (storico point-in-time); prevalenza acquisti 6h; uscita dal range con volume | minimo del range −3% |
| **E – Revival** | 1h | età ≥ 7 giorni; volume 24h ≥ 3× fase dormiente (6 giorni prima); ≥ 70% sotto i massimi storici; rottura del massimo di 72 h; liquidità ≥ 20k $ | minimo 24 h −5% |

Ogni strategia restituisce o un segnale con i motivi, o l'elenco delle condizioni non soddisfatte.
Una sola posizione per token; tra più strategie vince la prima che segnala (ordine A→E).

## Gestione dell'uscita (politiche confrontabili nel backtest)

| Politica | Stop iniziale | Take profit | Trailing | Break-even |
|---|---|---|---|---|
| `fixed_simple` | fisso 20% | 100% a +60% | no | mai |
| `ladder_trailing` (default) | 2,5 ATR (10–35%) | 33% a +50%, 33% a +100% | 25% dal massimo dopo +40% | dopo il 1° TP, a ingresso +4% (copre i costi) |
| `trailing_only` | 2,5 ATR | — | 22% dopo +25% | dopo +1,5R |
| `momentum_exit` | 2,5 ATR | 50% a +30% | 18% dopo +30% | dopo il 1° TP |
| `ladder_no_be` | come default | come default | come default | **mai** |
| `ladder_be_1r` | come default | come default | come default | dopo +1R |

Uscite indipendenti dal prezzo, comuni a tutte: durata massima (6 h), nessun progresso (60 min senza +5%),
volume crollato sotto il 20% del livello d'ingresso, liquidità −35% rispetto all'ingresso, deterioramento
on-chain (authority riattivate, rotta di vendita scomparsa, nuovi rischi critici, vendite coordinate).

**Break-even:** non viene spostato automaticamente appena il prezzo sale. Le due varianti `ladder_no_be` e
`ladder_be_1r` esistono proprio per misurare sui dati se e quando conviene, tenendo conto di commissioni,
slippage e pullback normali (il livello BE include i costi di andata e ritorno).

**Prudenza nel backtest:** stop controllato prima dei take profit nella stessa candela; apertura sotto lo
stop → esecuzione all'apertura (gap); trailing/BE aggiornati solo dalla candela successiva; nelle candele di
rug lo stop viene eseguito al minimo della candela, non al livello dello stop.

## Dimensionamento (2 SOL, capitale aggiornato)

```
dimensione = min(
  rischio per trade × equity / (distanza stop + costi andata/ritorno + cuscinetto gap),
  max per posizione × equity,
  esposizione massima − esposizione aperta,
  cassa − riserva minima − fee,
  dimensione con impatto di prezzo ≤ limite,
  quota massima della riserva del pool,
  perdita massima in caso di rug × equity / 100%      ← aggiunto dopo lo stress test
)
```

| Profilo | Rischio/trade | Pos. max | Esposizione max | Riserva cassa | Perdita max se rug | Stop giornaliero | Riduzione / pausa per drawdown | Score min |
|---|---|---|---|---|---|---|---|---|
| Conservativo | 0,75% | 2 | 20% | 50% | 2,5% | −3% | 10% / 20% | 75 |
| **Moderato (default)** | 1,25% | 3 | 35% | 40% | 4% | −5% | 15% / 30% | 70 |
| Aggressivo | 2% | 3 | 50% | 30% | 6% | −8% | 20% / 35% | 65 |

Con 2 SOL e profilo moderato una posizione tipica è **0,05–0,08 SOL**. Il rischio si calcola sempre
sull'equity corrente: dopo le perdite la dimensione scende (anti-martingala) e in drawdown il rischio viene
dimezzato. Il sistema non raddoppia mai dopo una perdita.

**Anti-overtrading:** massimo operazioni giornaliere, pausa dopo N perdite consecutive, cooldown sullo stesso
token (più lungo dopo una perdita), nessun nuovo ingresso con anomalie di mercato (SOL −8% in 1 ora o fonti
dati principali non disponibili), kill switch automatico oltre il drawdown massimo (ripresa solo manuale).
