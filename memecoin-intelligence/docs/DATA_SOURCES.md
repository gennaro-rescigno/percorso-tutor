# Fonti dati e API

> **Stato di verifica (1 nov 2026).** Il container in cui è stato sviluppato il progetto ha una policy di rete
> che blocca tutti gli host delle API crypto (proxy: `connect_rejected`). Gli endpoint sono implementati dalla
> documentazione pubblica (vedi RESEARCH_REPORT §9 e registro fonti) con parsing difensivo, e testati con
> risposte simulate (`backend/tests/test_collectors.py`). **La verifica live va fatta sul server** con:
>
> ```bash
> docker compose exec worker mci check-sources
> ```
>
> Esito atteso: tutte le righe `OK`. Una riga `KO` indica una fonte cambiata o bloccata: il sistema continua a
> funzionare senza (il dato diventa "non disponibile" e, se critico, il token non è negoziabile).

## API effettivamente utilizzate

| Fonte | Endpoint | Chiave | Budget usato dal sistema | Dato | Se non disponibile |
|---|---|---|---|---|---|
| DexScreener | `/token-profiles/latest/v1`, `/token-boosts/latest/v1`, `/tokens/v1/solana/{≤30 indirizzi}` | no | ~15–20 req/min (limite 300/min sui pair) | prezzo, MC/FDV, liquidità, volume e tx 5m/1h/6h/24h, età, link social, boost | nuovi ingressi bloccati (anomalia "fonti dati principali non disponibili"); posizioni gestite con l'ultimo prezzo noto |
| GeckoTerminal | `new_pools`, `trending_pools`, `pools/{pool}`, `pools/{pool}/trades`, `pools/{pool}/ohlcv/{tf}?currency=token` | no | ≤25 req/min (limite 30/min) | compratori/venditori **unici**, finestra 15m, trade per wash score, candele OHLCV (storico per il backtest) | strategie basate su candele non generano segnali; compratori unici "n/d" |
| Jupiter | `/swap/v1/quote`, `/price/v3`, `/swap/v1/swap` | opzionale | 0,5 RPS keyless | quote eseguibili (impatto reale), prezzi, transazioni di swap | paper: ripiego sul modello AMM con etichetta `amm_model`; test di vendibilità "n/d" → token non negoziabile |
| RugCheck | `/v1/tokens/{mint}/report` | no | ~2 req/min (cache 15 min) | mint/freeze authority, estensioni Token-2022, top holder, LP bloccata, rischi, insider | sicurezza "n/d" → token non negoziabile |
| PumpPortal | WebSocket `subscribeNewToken`, `subscribeMigration`, `subscribeTokenTrade` | no | 1 connessione | nuovi token e migrazioni in tempo reale, trade dei token in bonding curve | scoperta solo tramite DexScreener/Gecko (con ritardo) |
| Solana RPC | `getAccountInfo`, `getTokenLargestAccounts`, `getBalance`, `sendTransaction`, `getSignatureStatuses` | no (Helius free consigliato) | basso | decimali, saldo, conferme | paper: decimali di default 6 per token pump.fun |
| CoinGecko / Kraken | `simple/price`, `0/public/Ticker` | no | 1 req/2 min | SOL in EUR/USD (dinamico) | importi in EUR "n/d" |
| Telegram Bot API | `sendMessage`, `getUpdates` | token BotFather | — | notifiche e comandi | solo log |
| Reddit (opzionale) | OAuth app-only `search` | app gratuita | 1 req/30 min per token | menzioni e autori unici | categoria social "n/d" |
| Dune (opzionale) | `GET /api/v1/query/{id}/results` (header `X-Dune-API-Key`) | account Free | 1 lettura per import | elenco casuale di tutti i lanci Pump.fun di un periodo (universo storico senza survivorship bias) | si usa solo il dataset registrato in avanti |
| GeckoTerminal (import storico) | `/networks/solana/tokens/{mint}/pools`, OHLCV a finestra | no | ≤25 req/min | pool e candele delle prime 24 h dei token estratti | token conteggiato come "senza dati" nella copertura |

## Non usate (e perché)

| Fonte | Motivo |
|---|---|
| X / Twitter API | dal 6 feb 2026 solo pay-per-use (~0,005 $ per post letto): contraddice il requisito "gratuito" |
| Birdeye | free tier di 30.000 CU/mese a 1 RPS: insufficiente per uno scanner continuo; utile in futuro per OHLCV |
| Pump.fun frontend API | non documentata, protetta da Cloudflare; PumpPortal offre gli stessi eventi in modo stabile |
| Bitquery | non necessario: Dune copre l'universo storico |

## Dati raccolti per ogni token e copertura

| Gruppo richiesto | Campo | Fonte | Note |
|---|---|---|---|
| Token | nome, simbolo, mint, creazione | DexScreener / Gecko / PumpPortal | |
| Mercato | prezzo, MC, FDV, liquidità | DexScreener (+Gecko) | |
| Volume 5m/15m/1h/24h | DexScreener (5m/1h/6h/24h) + Gecko (15m) | 15m solo per i candidati arricchiti |
| Transazioni, compratori/venditori | DexScreener (conteggi) + Gecko (**unici**) | |
| Holder, distribuzione | RugCheck (top holder, totale) | pool/bonding curve esclusi |
| Concentrazione top 10 | RugCheck (fallback RPC approssimato) | |
| Wallet collegati / insider | RugCheck `insider`, cluster acquisti iniziali (PumpPortal) | il collegamento per finanziamento richiede storico transazioni (Helius) – non implementato nel free tier |
| Deployer | RugCheck `creator`, PumpPortal `create` | conteggio token per deployer: dal nostro DB nel tempo |
| Permessi del token | RugCheck / RPC | ricontrollati ogni 15 min per le posizioni aperte |
| Slippage stimato | quote Jupiter per 0,1 SOL in vendita | |
| Nuovi compratori / wallet ricorrenti | trade Gecko/PumpPortal | metriche wash: trade per trader, wallet su entrambi i lati |
| Social | link dichiarati, boost (a pagamento), Reddit opzionale, membri Telegram opzionali | X non disponibile |

Ogni campo non fornito resta `None` e viene mostrato come **"n/d"**; non viene mai stimato o inventato.
