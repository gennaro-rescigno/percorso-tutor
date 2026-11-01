# Piano di backtest e stato attuale

## Stato attuale: NESSUN backtest su dati reali è stato eseguito

Motivo: la rete dell'ambiente di sviluppo blocca tutte le API di dati crypto (vedi DATA_SOURCES.md).
Non sono stati simulati risultati al posto dei dati mancanti. Il motore di backtest è completo e testato
(86 test, eseguiti sia su SQLite sia su PostgreSQL, inclusi rug, token morti, assenza di look-ahead, costi), ma **nessuna strategia è oggi validata**
e il trading reale resta bloccato.

## Limiti dei dati storici (dichiarati)

1. **Survivorship bias:** le liste "top/trending" contengono solo i sopravvissuti. Un universo corretto
   richiede tutti i token lanciati nel periodo. Gratis senza account: non disponibile.
2. **Feature point-in-time:** holder, distribuzione, rischi, compratori unici, social *al momento del
   segnale* non sono recuperabili a posteriori gratuitamente.
3. **Liquidità storica:** non è nell'OHLCV. Stimata con la legge del prodotto costante
   (x_t = x_0·√(p_t/p_0)) dalla prima liquidità osservata; i ritiri di LP non sono osservabili → modellati
   come crolli con haircut della riserva e esecuzione al minimo della candela.
4. **Profondità storica gratuita:** 6 mesi per richiesta su GeckoTerminal.
5. **Risoluzione:** candele da 1 minuto; non si può simulare la competizione con i bot a livello di blocco →
   nessuna strategia entra nei primi minuti di vita di un token.
6. **Regime:** fee e meccaniche dei launchpad cambiano (fee dinamiche set-2025, BOOST lug-2026).

## Soluzione adottata: dataset senza survivorship bias costruito in avanti

Dal primo avvio il worker registra **ogni** token scoperto (inclusi esclusi e morti) con snapshot
point-in-time ogni 5 min (candidati) / 30 min (altri), candele a 1 minuto dei candidati, e l'esito di ogni
segnale. Dopo alcune settimane:

```bash
# scarica/completa le candele di tutti i token registrati (anche quelli morti)
sudo docker compose exec worker mci fetch-history --start 2026-11-01 --timeframe 1m
# backtest su dati registrati (point-in-time, universo completo)
sudo docker compose exec worker mci backtest --strategies B --profile moderate --exit ladder_trailing --out /app/reports/b.md
# confronto dei tre profili
sudo docker compose exec worker mci compare-profiles --strategies A,B,C,D,E
# walk-forward con selezione robusta dei parametri
sudo docker compose exec worker mci walkforward --strategy B --grid '{"vol_mult":[1.5,2.0,2.5],"max_extension":[0.2,0.3]}'
```

Opzione più rapida, gratuita con un account Dune (piano Free): `mci import-universe` legge da Dune un
**campione casuale di tutti i lanci Pump.fun** di un periodo (tabella `pumpdotfun_solana.pump_call_create`,
SQL nella GUIDA_PASSO_PASSO §4), scarica da GeckoTerminal le candele a 1 minuto delle prime 24 ore di ogni
token e misura la **copertura**: il dataset è dichiarato privo di survivorship bias solo se almeno il 90%
dei token estratti ha dati (se GeckoTerminal non avesse i token rimasti in bonding curve, il report lo
segnala). La liquidità dei token Pump.fun è ricostruita dalla bonding curve (k = 30 SOL × 1,073e9 token).
Questo storico contiene solo prezzi/volumi: misura la parte prezzo/volume delle strategie.

## Esecuzione simulata (in ogni backtest)

| Elemento | Modello |
|---|---|
| Ritardo di rilevazione | decisione sulla chiusura della candela *i*, esecuzione all'apertura di *i+1*; token negoziabile solo dopo `first_seen_at` + 20 s |
| Slippage di latenza | 0,5% sfavorevole in entrata e in uscita |
| Impatto | AMM a prodotto costante sulla riserva stimata point-in-time |
| Commissioni DEX | per venue (Pump.fun 1,25%, PumpSwap 1,25%→0,30% per MC, Raydium 0,25%, …) |
| Commissioni di rete | 0,000005 SOL + priority fee (default 0,0001) + Jito tip opzionale, anche sulle tx fallite |
| Affitto ATA | ~0,00204 SOL pagato all'ingresso, rimborsato solo a uscita completa |
| Transazioni fallite | 5% ingressi (segnale perso), 3% uscite (ritentate alla candela dopo) |
| Gap / rug | stop in gap all'apertura; nelle candele di crollo esecuzione al minimo; riserva ridotta dopo il rug |
| Token morti | se i dati si interrompono mentre si è in posizione: perdita totale (recupero 0%, configurabile) |

## Test previsti (Fase 6) e come si eseguono

| # | Test | Come |
|---|---|---|
| 1–2 | memecoin esplosive e fallite | universo registrato completo (contiene entrambe per costruzione) |
| 3–4 | token appena lanciati vs consolidati | strategie A (età 15 min–6 h) vs B/C/E (età ≥ 3 h / 7 giorni) |
| 5 | condizioni di mercato diverse | finestre walk-forward + segmentazione per andamento di SOL |
| 6 | strategie di ingresso | `mci backtest --strategies X` per X in A..E |
| 7 | sistemi di uscita | `--exit` tra le 6 politiche (incluso il confronto break-even sì/no) |
| 8–9 | stake e livelli di rischio | `compare-profiles` + override `risk_per_trade_pct`, `max_position_pct` |

Suddivisione: 60% training / 20% validation / 20% out-of-sample (`split_times`), più walk-forward a 4
finestre con selezione dei parametri per **mediana dei vicini nella griglia** (evita i picchi fortunati) e
obiettivo rendimento/drawdown, non profitto grezzo.

## Criteri per dichiarare un risultato "robusto"

* ≥ 100 trade out-of-sample per strategia;
* intervallo di confidenza al 95% (bootstrap) dell'expectancy per trade interamente sopra zero;
* profit factor OOS > 1,2 con costi;
* max drawdown Monte Carlo (p95) entro il limite del profilo;
* risultati coerenti in almeno 3 delle 4 finestre walk-forward.

Sharpe e Sortino vengono mostrati solo con ≥ 30 giorni di rendimenti giornalieri.

## Cancelli prima del trading reale

1. backtest robusto secondo i criteri sopra, su dati registrati point-in-time;
2. almeno 30 giorni e 50 operazioni di paper trading coerenti con il backtest;
3. tuo consenso esplicito + configurazione sul server (docs/SECURITY.md).

## Stress test del risk management (dati SINTETICI)

`reports/STRESS_TEST_SYNTHETIC.md` – 8 scenari di rug + pump&dump + token morto + rumore, strategia A senza
filtri on-chain (caso peggiore). Serve a verificare i controlli di rischio, **non** la redditività.

| Profilo | Perdita prima della correzione | Dopo il limite "perdita massima se rug" |
|---|---|---|
| Conservativo | −8,5% | −6,0% |
| Moderato | −33,0% | −19,1% |
| Aggressivo | −47,0% | −28,5% |

Conclusione: il "rischio 1–2% per trade" calcolato sullo stop sottostima il rischio reale delle memecoin,
perché un rug salta lo stop. Il sizing ora limita anche la perdita totale della posizione (2,5% / 4% / 6%
del capitale). Anche così, una serie di rug consecutivi può costare circa il 20% con il profilo moderato:
per questo i filtri di sicurezza on-chain (assenti nello stress test) sono la prima linea di difesa.
