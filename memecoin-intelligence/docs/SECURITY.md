# Sicurezza, segreti e attivazione (futura) del trading reale

## Regole

* Nessun segreto nel codice, nei log o su GitHub. Tutti i segreti stanno in `.env` sul server
  (`chmod 600`, escluso da git tramite `.gitignore`), tipizzati come `SecretStr` (non stampabili).
* Il bot Telegram risponde solo alle chat in `MCI_TELEGRAM_CHAT_IDS`; il trading reale **non** si può
  attivare da Telegram né dalla dashboard.
* La dashboard richiede login (password da `.env`, token firmati HMAC con scadenza, blocco dopo 5 tentativi
  falliti in 15 minuti), è servita solo in HTTPS tramite Caddy.
* Il database non è esposto su internet (solo rete interna di docker compose).

## Il trading reale è disattivato

Il worker usa l'executor reale **solo se tutte** queste condizioni sono vere; altrimenti resta in paper e lo
scrive nel log:

1. `MCI_TRADING_MODE=live`
2. `MCI_LIVE_TRADING_ENABLED=true`
3. `MCI_LIVE_TRADING_CONFIRMATION` uguale alla frase esatta
   `I UNDERSTAND I CAN LOSE ALL FUNDS IN THE DEDICATED WALLET`
4. `MCI_LIVE_WALLET_KEYFILE` punta a un file esistente, **fuori dalla cartella del progetto**, con permessi
   `600` (il codice rifiuta file dentro il repository o con permessi aperti)
5. dipendenza opzionale installata: `pip install '.[live]'` (`solders`)

Protezioni aggiuntive in modalità reale (`execution/live.py`):

| Protezione | Default |
|---|---|
| Limite per operazione | 0,1 SOL |
| Limite giornaliero di spesa | 0,5 SOL |
| Limite per singolo token | 0,2 SOL |
| Riserva minima di SOL nel wallet per fee/affitti | 0,05 SOL |
| Ordini duplicati | `client_order_id` univoco + blocco di ordini ripetuti sullo stesso token entro 60 s |
| Controllo saldo | prima di ogni operazione |
| Impatto massimo accettato | 5% |
| Conferma on-chain | polling fino a `confirmed`; senza conferma l'ordine è "fallito/sconosciuto", mai "eseguito" |
| Blocco automatico | dopo 3 errori consecutivi |
| Kill switch | da Telegram (`/kill`), dashboard o automatico per drawdown |

Nota: in modalità reale gli importi del fill derivano oggi dalla quote confermata; prima di usare capitale
reale va aggiunta la lettura dei saldi pre/post dalla transazione confermata (attività di hardening prevista).

## Procedura per un wallet dedicato (quando e se deciderai di attivare il reale)

1. **Non usare mai il wallet principale.** Crea un wallet nuovo sul server:
   `solana-keygen new --outfile /home/ubuntu/secrets/trading-wallet.json` (poi `chmod 600`).
2. Annota la seed phrase **offline** (carta), mai in file, chat, email o cloud.
3. Trasferisci **solo** il capitale che accetti di perdere (es. 2 SOL + 0,05 per le fee).
4. Monta il file nel container in sola lettura (vedi commento in `docker-compose.yml`) e imposta
   `MCI_LIVE_WALLET_KEYFILE=/run/secrets/wallet.json`.
5. Imposta i cancelli 1–3 in `.env`, riavvia il worker, verifica nel log e su Telegram che i messaggi
   mostrino **💰 TRADING REALE**.
6. Per tornare in paper: `MCI_TRADING_MODE=paper` e riavvio. Per fermare subito i nuovi ingressi: `/kill`.

Prerequisiti richiesti dal progetto prima di questo passo: backtest robusto su dati reali + almeno 30
giorni di paper trading (docs/BACKTEST_PLAN.md) + **tuo consenso esplicito**.
