# PROJECT_AUDIT.md — Audit del progetto Memecoin Intelligence (4 novembre 2026)

Audit eseguito prima di qualsiasi modifica all'architettura, come richiesto dalla missione "Memecoin Profitability
Research Lab". Ogni affermazione è verificata sul codice, sui test o sui dati del server (file `vps_status.md` del
branch `research-results`, aggiornato dal workflow `memecoin-vps-status`). Dove qualcosa non è verificato, è
scritto.

## 1. Sintesi in dieci punti

1. **Il sistema funziona come piattaforma di ricerca e paper trading**: gira su un VPS Hetzner, raccoglie dati
   on-chain gratuiti in tempo reale, simula operazioni, registra tutto in PostgreSQL e lo mostra nella dashboard.
2. **Nessuna operazione reale è mai stata eseguita.** L'esecutore reale esiste ma è bloccato da più cancelli
   (`trading_mode`, `live_trading_enabled`, frase di conferma, wallet dedicato): resta in modalità paper.
3. **Nessuna strategia sulle memecoin ha dimostrato un vantaggio** in 18 studi storici (oltre 150 combinazioni) su
   dataset gratuiti (milioni di token e operazioni, quattro periodi diversi). L'unica strategia robusta trovata non
   riguarda le memecoin: il filtro di trend a 50 giorni su BTC·ETH·SOL (+31,2% annuo fuori campione).
4. **L'unico vantaggio misurato sulle memecoin è la velocità**: copiare i wallet migliori allo stesso prezzo
   renderebbe +9,1%, con 1 secondo di ritardo −5,4%. Non è raggiungibile con l'infrastruttura gratuita.
5. **Il ritardo reale dei dati è alto**: lo stream gratuito (WebSocket pubblico di Solana) consegna le operazioni con
   un ritardo mediano misurato di **28,7 s** (p01 2,8 s, p90 55,7 s). Ogni strategia "nei primi 10-30 secondi" non è
   eseguibile dal vivo con questi dati.
6. **Telegram non consegna messaggi**: 0 inviati; l'ultimo test (1 novembre) ha risposto `HTTP 400 chat not found`.
   Serve un'azione dell'utente (aprire il bot e premere /start, o correggere l'ID della chat).
7. **I risultati dal vivo sono coerenti con la ricerca**: portafoglio principale +0,47% su 18 operazioni (2,0093 SOL),
   Laboratorio −8,2% su 33, esperimenti x_safe −5,0% e x_curve −10,1%. Campioni piccoli, nessuna conclusione
   statistica possibile.
8. **190 test automatici passano** (SQLite, 25 s); CI su GitHub; i dati sintetici sono usati solo per test del motore
   e stress test, sempre etichettati `synthetic`.
9. **Esperimento di copia fermo**: 992 wallet misurati, 0 idonei con i criteri attuali: non genera segnali.
10. **Cinque dataset gratuiti già individuati non erano mai stati esaminati**: il probe è stato avviato in questo
    audit (`research/historical/probe2.py`).

## 2. Architettura e moduli (backend Python, 15.788 righe)

| Pacchetto | Righe | Cosa fa | Stato reale |
|---|---|---|---|
| `chain` | 1.242 | decodifica pump.fun (IDL), PDA, stream WebSocket con connessioni ridondanti, pool RPC | **in produzione**, dati reali |
| `collectors` | 1.160 | DexScreener, GeckoTerminal, Jupiter, RugCheck, Solana RPC, PumpPortal, cambio SOL/EUR | **in produzione**, tutte le fonti "ok" |
| `onchain` | 1.673 | lanci, caratteristiche della curva, holder, wallet, wash trading, diario dei token, registro dei wallet | **in produzione** |
| `scanner` | 654 | scoperta e arricchimento dei token (DexScreener, GeckoTerminal) | **in produzione** |
| `scoring` | 666 | filtri di sicurezza, punteggio, indici di rischio e opportunità | in produzione, indici **non dimostrati fuori campione** |
| `strategies` | 739 | strategie A-E (EarlyEntry, Momentum, Pullback, Accumulation, Revival), curva organica | in paper; A spenta nel principale dal 3 novembre |
| `risk_management` | 647 | profili conservativo / moderato / aggressivo, sizing, uscite, limiti | in produzione (paper) |
| `execution` | 712 | costi, simulazione di vendita (`simulateTransaction`), esecutore paper, esecutore reale | paper attivo; **reale mai eseguito** |
| `paper_trading` | 1.123 | motore principale, Laboratorio, esperimenti shadow, simulazione di copia | in produzione |
| `research` | 1.258 | feature store, etichette, valutazione, promozione, studio degli eventi, laboratorio delle regole, modello 5-10 min | in produzione (sola misura) |
| `backtesting` | 1.452 | motore, metriche, walk-forward, universo, dataset registrati/importati/sintetici | funzionante; usato poco sui dati reali |
| `trend` | 276 | portafoglio virtuale trend BTC·ETH·SOL | in produzione dal 2 novembre, in liquidità |
| `database` | 729 | 19 tabelle SQLAlchemy (PostgreSQL in produzione, SQLite nei test) | in produzione, 505 MB |
| `telegram` | 564 | bot, formattazione, invio solo acquisti/vendite del principale | **non consegna** (chat not found) |
| `api` | 692 | FastAPI con autenticazione | in produzione |
| `analytics`, `social_analysis`, `utils` | 447 | metriche di performance, analisi social minima, client HTTP con limiti di frequenza | analisi social quasi vuota |

Frontend React (15 pagine: Panoramica, Scanner, Lanci, Token, Posizioni, Performance, Rischio, Esperimenti,
Laboratorio, BacktestLab, Ricerca, Trend, Log, Sistema, Login). Deploy: Docker Compose sul VPS, 11 workflow GitHub
(CI, deploy automatico del bot, backup dello stato, stato del VPS, studi storici, controlli di contratto).

## 3. Fonti dati e API (verificate dal vivo sul server)

| Fonte | Uso | Stato sul server | Limiti noti |
|---|---|---|---|
| WebSocket pubblico Solana (`logsSubscribe` sul programma pump.fun) | operazioni e lanci in tempo reale | connesso; 150.238 messaggi, 14.819 operazioni, 17 riconnessioni | chiude le connessioni ogni 15-25 s; **ritardo mediano 28,7 s** |
| RPC pubblico Solana | conti, holder, `simulateTransaction` | 57 chiamate, 0 errori | 100 richieste / 10 s per IP |
| PumpPortal (WebSocket gratuito) | nuovi token se lo stream cade | attivo | solo creazione dei token |
| DexScreener | scoperta, coppie, boost, profili | ok | 60-300 richieste/min secondo l'endpoint |
| GeckoTerminal | pool nuovi e di tendenza, candele | ok | 30 richieste/min |
| Jupiter | prezzi e quotazioni | ok, chiave gratuita attiva (1 richiesta/s) | |
| RugCheck | controllo di sicurezza esterno | ok | |
| CoinGecko / Kraken | cambio SOL/EUR e SOL/USD | ok | |
| Binance / Kraken | chiusure giornaliere per il trend | ok | |
| Telegram Bot API | notifiche | **non consegna** | serve /start dell'utente |
| Hugging Face (jocry, loopholetape, fly-trader-seed) e data.binance.vision | studi storici | letti dai runner GitHub | il sandbox di sviluppo non li raggiunge |

Birdeye, Helius e altri fornitori a pagamento non sono integrati (vincolo: nessun servizio a pagamento).

## 4. Strategie implementate e risultati dal vivo

| Strategia | Dove gira | Risultato dal vivo (2-3 novembre) | Evidenza storica |
|---|---|---|---|
| A EarlyEntry | Laboratorio (spenta nel principale) | Laboratorio: 13 chiuse, 2 vinte, −0,150 SOL | perdente (sezioni 9.2-9.4 della ricerca) |
| B Momentum | principale + Laboratorio | Laboratorio: 18 chiuse, 3 vinte, −0,054 SOL | perdente |
| C Pullback | principale + Laboratorio | Laboratorio: 2 chiuse, +0,039 SOL | perdente |
| D Accumulation, E Revival | principale | nessun segnale significativo | non testate su dati storici specifici |
| x_curve (curva organica) | esperimento shadow | 26 chiuse, ROI −10,1% | perdente |
| x_safe (Laboratorio + regole di sicurezza) | esperimento shadow | 18 chiuse, ROI −5,0% | |
| x_copy (copia con ritardo reale) | esperimento shadow | 0 leader idonei, nessun segnale | storico: −5,9% con 3 s di ritardo |
| Trend BTC·ETH·SOL | portafoglio virtuale | avviato il 2 novembre, in liquidità | **robusta**: +31,2% annuo 2022-2026 |

Portafoglio principale (paper): 18 operazioni chiuse, win rate 33%, ROI +0,47%, drawdown 4,5%, capitale 2,0093 SOL.
Il valore in euro è calcolato dal prezzo corrente di SOL (≈ 167 € il 3 novembre), mai fisso.

Osservazioni sulle uscite dal vivo: la maggior parte delle chiusure perdenti è "stop superato in gap: eseguito
all'apertura" (il prezzo salta oltre lo stop tra due osservazioni): sulle memecoin uno stop fisso non protegge
quanto promette. È un dato utile per la ricerca sulle uscite.

## 5. Motore di scoring

Indice di rischio (`rug_60m`) e di opportunità (`hit_2x_first`) calcolati sul feature store del bot (4.849
osservazioni usabili, 69-70 casi positivi). AUC dentro il campione 0,84 e 0,44, ma nel **walk-forward**: opportunità
"batte il tasso base 0/3", rischio "2/3": **non dimostrati fuori campione**. Le caratteristiche più informative
(n_trades, drawdown dal massimo, acquirenti unici, concentrazione) hanno intervalli che non includono 0,5, ma il
campione è troppo piccolo per una strategia.

## 6. Backtesting e studi storici

- Motore di backtest (`mci/backtesting`): candele, costi, walk-forward, metriche; dataset `recorded` (candele dello
  stream: 32.668), `imported`, `synthetic`.
- **Dati sintetici**: `mci/backtesting/synthetic.py` genera scenari (rug, pump & dump, token morto...) **solo** per
  test del motore e stress test; ogni report li etichetta; l'unico report sintetico è
  `reports/STRESS_TEST_SYNTHETIC.md`. Nessun risultato di profitto è basato su dati sintetici.
- **Studi storici reali** (`research/historical`, eseguiti sui runner GitHub, risultati nel branch
  `research-results`): 18 studi di analisi (più 4 probe dei dataset), tutti con regole scritte prima, divisione in campione / fuori campione, intervalli
  bootstrap, correzione per test multipli, costi realistici. Elenco e verdetti in `docs/RICERCA_MERCATO_MEMECOIN.md`
  sezioni 9-10 e nella sezione 9 di questo audit.

## 7. Paper trading, rischio, database

- Paper trading: principale (profilo moderato, massimo 6 operazioni al giorno, punteggio minimo 70), Laboratorio
  senza limiti, esperimenti shadow, simulazione di copia, portafoglio trend. Le vendite sono verificate con
  `simulateTransaction` (7 simulazioni, 6 riuscite, 1 non verificabile).
- Risk management: profili conservativo / moderato / aggressivo, sizing per rischio, perdita massima per operazione
  4%, ipotesi di perdita totale in caso di rug, kill switch, pausa, limite giornaliero.
- Database: 19 tabelle (token, snapshot, candele, segnali, posizioni, ordini, eseguiti, equity, eventi, stato,
  backtest, alert, lanci pump, operazioni pump, profili wallet, eventi token, giornate wallet, copie, feature
  snapshot). In produzione: 15.429 lanci, 565.231 operazioni iniziali, 42.206 feature snapshot, 21.251 etichettati,
  19.041 eventi token. Backup dello stato su branch dedicato.

## 8. Test, branch, commit

- `pytest`: **190 test passano** (SQLite). L'ultima esecuzione completa su PostgreSQL era verde prima dei moduli
  trend; il CI li esegue a ogni push.
- Branch: `feature/memecoin-intelligence` (lavoro) e `main` (deploy) allineati; `research-results` (risultati degli
  studi e stato del VPS); `bot-state` (backup); `live-fixtures` (campioni reali per i test). Altri branch del
  repository (`feature/live-football-scanner`, `claude/birthday-...`, `gh-pages`) non riguardano questo progetto.

## 9. Esperimenti già eseguiti (verificati)

| Area | Studi | Verdetto |
|---|---|---|
| Lanci sulla curva | loop_curve, loop_short, loop_model, loop_model2 | perdenti, anche il modello (−7/−10%) |
| Dopo il diploma | postgrad | nessuna regola positiva e stabile |
| Wallet e copia | jocry_copy, jocry_copy2 | abilità persistente ma non copiabile: +9,1% solo allo stesso istante |
| Token quotati su PumpSwap | fly_rules, dex_model | 21/21 negative; modello portabile negativo |
| Liquidità (fare il banco) | dex_lp | 33/33 negative |
| Crypto affermate | crypto_trend, crypto_trend2, crypto_trend_trades | **trend BTC·ETH·SOL robusto** |
| Operazioni 1-3 giorni su 100 monete | crypto_daily, crypto_daily2 | H2 positiva ma non robusta (6/17) |
| Short sui perpetui | crypto_short | nessuna regge |
| Funding (carry) | crypto_carry | 12/12 negative |
| Trend sulle memecoin quotate | meme_trend | perde meno che tenerle (+4,6% contro −23%), non regge |

## 10. Cosa funziona, cosa è simulato, cosa manca

**Funziona davvero (verificato):** raccolta dati in tempo reale, decodifica on-chain, controlli di sicurezza,
simulazione di vendita, paper trading con costi, registro dei wallet, diario degli eventi, dashboard, backup,
deploy automatico, studi storici riproducibili.

**È soltanto simulazione:** tutte le operazioni (paper); il portafoglio trend; la copia dei wallet.

**Non testato:** esecuzione reale (mai fatta, per scelta); consegna Telegram (rotta); strategie D ed E su dati
storici dedicati; fonti social (modulo quasi vuoto, nessuna fonte gratuita affidabile collegata); launchpad diversi
da pump.fun (Raydium LaunchLab, Bonk.fun, Moonshot: nessun dato storico gratuito verificato finora).

**Dati sintetici:** solo `synthetic.py` e lo stress test etichettato.

**Da migliorare (in ordine di priorità):**
1. Telegram: azione dell'utente (/start sul bot o ID chat corretto).
2. Ritardo dei dati: 28,7 s mediani. Ogni ricerca sulle entrate deve assumere almeno questo ritardo (o dimostrare
   un vantaggio che giustifichi un'infrastruttura più veloce, che è una decisione con costi).
3. Esperimento di copia: 0 leader idonei; i criteri vanno rivisti sui dati del registro, senza abbassarli a caso.
4. Uscite: gli stop "in gap" dominano le perdite dal vivo; la ricerca deve confrontare uscite diverse (fisse,
   trailing, parziali, per perdita di slancio) sui percorsi reali, non solo tenute a tempo fisso.
5. Ricerca: mancano uno studio sistematico dei tempi di ingresso (10 s → 1 h) con ritardo realistico, un confronto
   entrate × uscite, la distinzione pump organico / artificiale con i wallet, e l'analisi di sopravvivenza dei token.
   Sono i primi esperimenti del laboratorio (vedi `STRATEGY_RESEARCH.md`).
6. Dataset: esaminare i cinque dataset gratuiti mai aperti (probe in corso).

## 11. Decisioni prese dopo l'audit

- Nessun codice funzionante viene eliminato. Strategie e esperimenti esistenti restano attivi in paper.
- Il nuovo lavoro va in moduli separati: `research/historical/discovery_*.py` (motore di scoperta sui dati storici) e
  `research/ranking.py` (classifica delle strategie da tutti i risultati), con i documenti `STRATEGY_RESEARCH.md`,
  `STRATEGY_RANKING.csv`, `STRATEGY_COMPARISON.md`, `PROFITABILITY_RESEARCH_REPORT.md`.
- Una strategia entra nel sistema principale solo se supera il cancello statistico fuori campione **e** con il tuo
  consenso; il trading reale resta disattivato.
