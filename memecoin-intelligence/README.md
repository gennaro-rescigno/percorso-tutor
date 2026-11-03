# Memecoin Intelligence & Trading System

Sistema di intelligence per memecoin su Solana: scopre i nuovi token, li analizza (mercato, liquidità,
on-chain, wallet, manipolazione del volume, sicurezza del contratto, social), assegna uno score 0–100
spiegato, genera segnali con 5 strategie, gestisce il rischio su un capitale di **2 SOL** (controvalore in
EUR aggiornato dinamicamente), simula le operazioni in **paper trading con quote reali**, invia notifiche
Telegram e mostra tutto in una dashboard web. Architettura pronta per il trading reale, **disattivato**.

> ⚠️ **Stato onesto del progetto**
> * Nessun backtest su dati reali è ancora stato eseguito: l'ambiente di sviluppo non poteva raggiungere le
>   API di mercato. Il motore è completo e testato; il dataset senza survivorship bias si costruisce dal
>   primo avvio sul server (vedi [docs/BACKTEST_PLAN.md](docs/BACKTEST_PLAN.md)).
> * Le API sono implementate dalla documentazione e testate con risposte simulate: vanno verificate dal
>   server con `mci check-sources`.
> * La modalità predefinita è **paper trading**. Il trading reale richiede il tuo consenso esplicito e
>   una procedura sul server ([docs/SECURITY.md](docs/SECURITY.md)).
> * Le memecoin sono estremamente rischiose: la ricerca indica che ~98% dei token Pump.fun mostra segni di
>   frode e che la maggior parte dei trader perde denaro.

## Documenti

| Documento | Contenuto |
|---|---|
| **[GUIDA_PASSO_PASSO.md](GUIDA_PASSO_PASSO.md)** | **come mettere tutto online gratis: Telegram, Oracle, DuckDNS, Dune** |
| [RESEARCH_REPORT.md](RESEARCH_REPORT.md) | ricerca: tassi base, casi studio, pattern testabili, fonti con affidabilità e limiti |
| [docs/RICERCA_MERCATO_MEMECOIN.md](docs/RICERCA_MERCATO_MEMECOIN.md) | **ricerca sul mercato**: ciclo di vita dei lanci, tattiche, bot, segnali con evidenza, dataset gratuiti, ipotesi da testare |
| [docs/EVOLUZIONE_IMPLEMENTATA.md](docs/EVOLUZIONE_IMPLEMENTATA.md) | **cosa fa ora il bot**: stream blockchain gratuito, sicurezza propria, wallet, feature store, esperimenti, ricerca |
| [docs/EVOLUZIONE_FASE1_FASE2.md](docs/EVOLUZIONE_FASE1_FASE2.md) | audit, ricerca e roadmap dell'evoluzione |
| [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) | API utilizzate, limiti, cosa succede quando non rispondono |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | architettura, struttura del codice, scelte tecniche |
| [docs/SCORING.md](docs/SCORING.md) | filtri di esclusione, pesi dello score, spiegazioni |
| [docs/STRATEGIES.md](docs/STRATEGIES.md) | strategie A–E, uscite, sizing e profili di rischio |
| [docs/BACKTEST_PLAN.md](docs/BACKTEST_PLAN.md) | limiti dei dati storici, piano di backtest, criteri di robustezza, stress test |
| [docs/INFRASTRUCTURE.md](docs/INFRASTRUCTURE.md) | confronto dei piani gratuiti, costi, compromessi |
| [docs/DEPLOY.md](docs/DEPLOY.md) | deploy passo-passo su Oracle Cloud Always Free (0 €) |
| [docs/SECURITY.md](docs/SECURITY.md) | segreti, wallet dedicato, cancelli del trading reale |
| [reports/STRESS_TEST_SYNTHETIC.md](reports/STRESS_TEST_SYNTHETIC.md) | stress test del risk management su scenari sintetici di rug |

## Avvio rapido senza server (GitHub Actions)

Il workflow `.github/workflows/memecoin-bot.yml` esegue il bot ogni ~15 minuti sui server gratuiti di
GitHub: basta aggiungere i secret `MCI_TELEGRAM_BOT_TOKEN` e `MCI_TELEGRAM_CHAT_IDS` (vedi
[GUIDA_PASSO_PASSO.md](GUIDA_PASSO_PASSO.md)). Stato nel cache di Actions + backup nel branch `bot-state`,
dashboard in sola lettura su GitHub Pages.

## Avvio rapido con server

```bash
# server (guida completa: GUIDA_PASSO_PASSO.md)
cp .env.example .env    # imposta password dashboard e Telegram
sudo docker compose up -d --build
sudo docker compose exec worker mci check-sources

# sviluppo locale
cd backend && python -m venv .venv && .venv/bin/pip install -e ".[dev]" && .venv/bin/pytest -q
```

## Comandi

| Comando | Cosa fa |
|---|---|
| `mci worker` | scanner + paper trading + monitor posizioni + report giornaliero + bot Telegram (24/7) |
| `mci api` | API e dashboard |
| `mci check-sources` | verifica che ogni fonte dati gratuita risponda |
| `mci telegram-test` | invia un messaggio di prova |
| `mci fetch-history` | scarica le candele di tutti i token registrati (inclusi quelli morti) |
| `mci backtest` / `compare-profiles` / `walkforward` | backtest su dati registrati o file di dataset |
| `mci stress-test` | stress test del risk management su rug sintetici |
| `mci import-universe` | storico senza survivorship bias: campione casuale di lanci da Dune + prezzi GeckoTerminal |

## Telegram

Notifiche: memecoin interessante, superamento soglia di score, segnale (accettato o rifiutato con motivo),
acquisto, take profit/vendita parziale, stop loss, posizione chiusa (lordo, commissioni, slippage, netto),
rischio rug, anomalie, variazioni di capitale ≥ 3%, report giornaliero. Ogni messaggio indica
🧪 PAPER TRADING o 💰 TRADING REALE.

Comandi: `/start /status /balance /positions /signals /history /performance /daily /risk /pause /resume /kill /paper /help`.

## Dashboard

Overview · Live Market Scanner (ordinabile per score, volume, momentum, market cap, crescita, liquidità,
rischio) · Scheda token (grafici, distribuzione holder, wallet, community, score dettagliato, rischi, motivo
del segnale) · Posizioni · Performance (equity, drawdown, P/L giornaliero/settimanale/mensile,
distribuzione dei rendimenti, per strategia e categoria, qualità dei segnali) · Backtest Lab (parametri,
capitale, periodo, stake, stop/TP, confronto tra due run) · Risk Management (kill switch, limiti,
esposizione) · Log e attività. Tema dark, responsive, aggiornamento automatico, accesso protetto.

## Test

86 test automatici (`backend/tests`), eseguiti sia su SQLite sia su PostgreSQL
(`MCI_TEST_DATABASE_URL=postgresql+psycopg://... pytest`): costi e AMM, sizing anti-martingala e limite di perdita in caso di rug,
filtri (honeypot, authority, token illiquidi, slippage, concentrazione, wash trading, prezzi anomali),
uscite (gap, ordine pessimistico stop/TP, trailing, break-even), risk manager (limiti, cooldown, perdite
consecutive, kill switch), backtest (costi, determinismo, assenza di look-ahead, token morti, rug durante
la posizione), collector (parsing, API non disponibili, rate limit 429, circuit breaker), executor paper e
live (cancelli, limiti di spesa, duplicati, wallet), flusso completo di paper trading con riavvio del
server, API (autenticazione, rate limit del login, endpoint, backtest lab) e comandi Telegram.
