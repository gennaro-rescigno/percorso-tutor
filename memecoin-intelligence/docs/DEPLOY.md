# Deploy

## VPS qualsiasi (consigliato): installazione automatica

`deploy/vps.sh` porta una VPS Ubuntu 22.04/24.04 appena creata al sistema completo, senza interventi:

| Cosa | Dettaglio |
|---|---|
| Avvio | `deploy/cloud-config.yaml` nel campo *cloud-init/user data* del provider, oppure `curl -fsSL .../deploy/vps.sh \| sudo bash -s install` |
| Segreti | solo in `/etc/mci/config.env` (600) → copiati in `.env` (600); mai nel repository né nei log; il token Telegram passa a `curl` via stdin |
| Sistema | Docker (get.docker.com), swap 2 GB se RAM < 3,5 GB, `ufw` (22/80/443), `fail2ban`, rotazione log Docker (5×10 MB per servizio) |
| Dati | stato paper importato dal branch `bot-state` solo se il database è vuoto; PostgreSQL su volume; `pg_dump` giornaliero (14 giorni) |
| Sicurezza trading | `MCI_TRADING_MODE=paper` e `MCI_LIVE_TRADING_ENABLED=false` riscritti a ogni installazione |
| Auto-aggiornamento | timer systemd ogni 10 min: passa all'ultimo commit di `main` con **CI verde** e successivo a quello attuale; se API o worker non risultano sani entro 8 min torna al commit precedente; notifica su Telegram |
| Dashboard | con `DOMAIN` (es. DuckDNS + `DUCKDNS_TOKEN`) attiva il profilo compose `web` (Caddy + Let's Encrypt) |
| Verifica | workflow `memecoin-vps-rehearsal`: installazione su Ubuntu 24.04 pulito, funzionamento continuo, crash del worker, riavvio di Docker, reinstallazione idempotente con HTTPS, logica di aggiornamento |

Comandi: `sudo bash /opt/mci/repo/memecoin-intelligence/deploy/vps.sh status|update|install`.

---

## Oracle Cloud Always Free, 0 € (manuale)

> La guida completa e verificata per principianti è **[GUIDA_PASSO_PASSO.md](../GUIDA_PASSO_PASSO.md)**
> (bot Telegram, account Oracle, VM, porte, DuckDNS, installazione, Dune). Qui sotto il riassunto tecnico.

## 1. Bot Telegram (2 minuti)

1. Su Telegram apri **@BotFather** → `/newbot` → scegli nome e username → copia il **token**.
2. Scrivi un messaggio al tuo nuovo bot (altrimenti non può scriverti).
3. Apri `https://api.telegram.org/bot<TOKEN>/getUpdates` nel browser → il numero dopo `"chat":{"id":` è il tuo **chat id**.

## 2. VM Oracle Cloud

1. Registrati su cloud.oracle.com (piano Free Tier; serve una carta per la verifica d'identità).
2. *Compute → Instances → Create*: immagine **Ubuntu 24.04**, shape **VM.Standard.A1.Flex** (1 OCPU, 6 GB)
   oppure **VM.Standard.E2.1.Micro** se l'A1 non è disponibile; carica la tua chiave SSH pubblica.
3. *Networking → VCN → Security List*: aggiungi regole di ingresso TCP **80** e **443** da `0.0.0.0/0`.

## 3. Installazione

```bash
ssh ubuntu@<IP_PUBBLICO>
git clone https://github.com/gennaro-rescigno/percorso-tutor.git
cd percorso-tutor/memecoin-intelligence
git checkout feature/memecoin-intelligence   # finché il branch non è unito
bash deploy/oracle-setup.sh                   # Docker, firewall, swap, .env con segreti casuali
nano .env                                     # imposta:
#   MCI_DASHBOARD_PASSWORD=<password lunga>
#   MCI_TELEGRAM_BOT_TOKEN=<token BotFather>
#   MCI_TELEGRAM_CHAT_IDS=<tuo chat id>
#   DOMAIN=<nome>.duckdns.org   (DuckDNS gratuito, puntato all'IP della VM)
sudo docker compose up -d --build
```

## 4. Verifica

```bash
sudo docker compose ps                              # tutti i servizi "running"
sudo docker compose exec worker mci check-sources   # tutte le fonti OK
sudo docker compose exec worker mci telegram-test   # ricevi il messaggio di prova
sudo docker compose logs -f worker                  # cicli dello scanner
```

Apri `https://<DOMAIN>` e accedi con `admin` / la password scelta. Su Telegram invia `/status`.

## 5. Manutenzione

| Operazione | Comando |
|---|---|
| Aggiornare il codice | `git pull && sudo docker compose up -d --build` |
| Riavviare | `sudo docker compose restart worker api` |
| Backup manuale | `sudo docker compose exec backup sh -c 'pg_dump -h db -U mci mci | gzip > /backups/manual.sql.gz'` |
| Ripristino | `gunzip -c backups/<file>.sql.gz \| sudo docker compose exec -T db psql -U mci mci` |
| Cambiare profilo di rischio | `MCI_RISK_PROFILE=` in `.env`, poi `sudo docker compose up -d` |
| Fermare i nuovi ingressi | `/pause` su Telegram o pulsante in Risk Management |

Riavvio automatico: tutti i servizi hanno `restart: unless-stopped` (ripartono dopo crash e reboot della VM);
lo stato (capitale, posizioni, kill switch) è nel database.

## Sviluppo locale

```bash
cd backend && python -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest -q
MCI_DASHBOARD_PASSWORD=dev .venv/bin/mci api &          # API su :8000 (SQLite in ./data)
.venv/bin/mci worker                                     # scanner + paper trading
cd ../frontend && npm install && npm run dev             # dashboard su :5173 (proxy verso :8000)
```
