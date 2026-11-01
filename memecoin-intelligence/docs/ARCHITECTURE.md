# Architettura

## Vista d'insieme

```
                       ┌─────────────────────── VM cloud (docker compose) ───────────────────────┐
  DexScreener ─┐       │                                                                          │
  GeckoTerminal┤       │  ┌──────────── worker (mci worker, asyncio, 24/7) ───────────┐            │
  Jupiter ─────┤ HTTPS │  │ Scanner ─► Scoring+Filtri ─► Strategie A–E ─► RiskManager │            │
  RugCheck ────┼──────►│  │    ▲             │                                │       │            │
  Solana RPC ──┤       │  │ PumpPortal WS    │ snapshot PIT                   ▼       │            │
  CoinGecko ───┤       │  │                  ▼                          Executor      │  Telegram  │
  PumpPortal ──┘       │  │             PostgreSQL ◄──── ordini/fill ── (paper|live) ─┼──► Bot API │
                       │  │                  ▲           posizioni      Position mon. │            │
                       │  └──────────────────┼───────────────────────────────────────┘            │
                       │                     │                                                    │
                       │  api (FastAPI) ─────┘──► dashboard React (statica) ◄── Caddy HTTPS ◄─────┼── browser
                       │  backup (pg_dump giornaliero)                                            │
                       └──────────────────────────────────────────────────────────────────────────┘
```

Due processi Python separati condividono il database:

* **worker** – scanner, motore di trading (paper di default), monitor posizioni, tracking dell'esito dei
  segnali, report giornaliero, bot Telegram. Tutto lo stato è nel DB: un riavvio riprende capitale,
  posizioni, kill switch.
* **api** – REST per la dashboard + file statici del frontend. Comandi (pausa/ripresa/kill) passano dal DB
  (`system_state`), quindi la dashboard non può bloccare il worker.

## Modalità senza server: GitHub Actions

```
 cron ~15 min ─► job "memecoin-bot" (runner GitHub, rete aperta)
                  1. ripristina data/mci.db dalla cache di Actions (se assente: state.json dal branch bot-state)
                  2. mci run-once --window 180  → scanner, strategie B–E, posizioni, comandi Telegram, report giornaliero
                  3. state-export + export-static (segreti rimossi dai file)
                  4. salva il DB nella cache, pubblica state.json + dashboard statica sul branch bot-state
                  5. (se Pages è attivo) deploy della dashboard in sola lettura su GitHub Pages
```

Compromessi rispetto al server: reattività di ~15–30 minuti invece di 20 secondi, strategia A disattivata,
dashboard pubblica senza comandi (i comandi passano da Telegram). Lo stesso codice gira in entrambe le
modalità (`MCI_RUN_MODE=server|github`).

## Struttura del codice

```
memecoin-intelligence/
├── RESEARCH_REPORT.md           ricerca (Fase 1)
├── docs/                        architettura, fonti, scoring, strategie, backtest, infra, deploy, sicurezza
├── backend/mci/
│   ├── config.py                impostazioni da env (MCI_*), cancelli del trading reale, fee per venue
│   ├── domain.py                TokenSnapshot (point-in-time), Candle, Signal, Fill, ScoreResult
│   ├── utils/http.py            client HTTP: rate limit token-bucket, retry/backoff, circuit breaker
│   ├── collectors/              dexscreener, geckoterminal, jupiter, rugcheck, pumpportal, solana_rpc, fx, social
│   ├── onchain/                 wash trading, cluster di acquirenti iniziali, vendite coordinate, concentrazione
│   ├── social_analysis/         classificazione dell'attenzione (organica / a pagamento / artificiale / ...)
│   ├── scoring/                 filtri di esclusione + punteggio 0–100 con spiegazioni
│   ├── strategies/              indicatori + strategie A–E parametrizzate
│   ├── risk_management/         profili, sizing, gestione uscite, risk manager di portafoglio
│   ├── execution/               modello di costo, executor paper (quote reali), live (bloccato), wallet
│   ├── backtesting/             dataset, motore event-driven, metriche, walk-forward, report, dati sintetici
│   ├── scanner/                 ciclo di scansione con budget di rate limit
│   ├── paper_trading/           motore segnale → rischio → ordine → posizione → uscita
│   ├── telegram/                client Bot API, messaggi, comandi
│   ├── analytics/               metriche di performance dal DB
│   ├── database/                modelli SQLAlchemy, sessioni, repository
│   ├── api/                     FastAPI + autenticazione
│   ├── worker.py                orchestrazione 24/7
│   └── cli.py                   comandi `mci ...`
├── backend/tests/               86 test (pytest, SQLite e PostgreSQL)
├── frontend/                    React + Vite + Recharts (tema dark, responsive)
├── deploy/                      Caddyfile, backup, setup VM Oracle
├── reports/                     report generati (backtest, stress test)
├── Dockerfile, docker-compose.yml, .env.example
```

## Scelte tecniche (decise autonomamente)

| Scelta | Motivo |
|---|---|
| Python 3.12, asyncio + httpx | I/O di rete concorrente con un solo processo leggero (gira su 1 GB di RAM) |
| SQLAlchemy 2 + PostgreSQL (SQLite in sviluppo/test) | persistenza transazionale; JSON per snapshot point-in-time |
| Nessun ORM async | volumi bassi; codice più semplice e testabile |
| FastAPI + React statico servito dalla stessa API | un solo servizio web, nessun hosting frontend separato |
| Caddy | HTTPS automatico gratuito (Let's Encrypt) |
| Token HMAC firmati, password da env | nessun servizio di identità esterno; rate limit sul login |
| Telegram long polling (no webhook) | non serve un endpoint pubblico per il bot |
| Nessuna dipendenza da pandas | immagine più piccola; numpy non necessario nel percorso critico |

## Separazione segnali / ordini simulati / ordini reali

* `signals` – proposta di una strategia, con **lo snapshot dei dati disponibili in quel momento**, i motivi,
  i rischi, lo stato (`generated/accepted/rejected/executed/failed`) e il motivo del rifiuto; più tardi
  vengono riempiti i prezzi a 15m/1h/4h/24h (esito, Fase 14).
* `orders` – ordini con `mode = paper | live` e `client_order_id` univoco (idempotenza).
* `fills` – esecuzioni (simulate con quote reali per paper, on-chain per live), con fee DEX, fee di rete,
  affitto ATA, slippage, impatto, fonte del prezzo.
* `positions` – posizioni aperte/chiuse con lo stato del motore di uscita.

## Estensione a Ethereum / Base

Il dominio (`TokenSnapshot.chain`), DexScreener e GeckoTerminal sono già multi-chain. Per aggiungere una
chain servono: un collector di sicurezza per contratti EVM (honeypot/tax, es. simulazione di vendita), un
aggregatore di quote (es. 0x/1inch/ParaSwap) che implementi la stessa interfaccia di `JupiterCollector`
(`buy_quote/sell_quote`), fee/gas nel `CostModel` e un executor live EVM. Scoring, strategie, risk
management, backtest e dashboard non cambiano.
