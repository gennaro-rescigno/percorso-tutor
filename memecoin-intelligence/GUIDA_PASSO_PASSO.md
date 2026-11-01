# Guida passo-passo

Due modi per far girare il bot senza tenere acceso il PC:

| | **VPS (attiva dal 1° novembre 2026)** | GitHub Actions (gratis, ora spento: il bot gira sulla VPS) |
|---|---|---|
| Costo | ~8–10 €/mese IVA inclusa (Hetzner, novembre 2026: da 7,92 €; pagamento a ore: se cancelli la VPS smetti di pagare) | 0 € |
| Frequenza | scanner ogni 60 s, posizioni ogni 20 s, Pump.fun in tempo reale | finestre di 3 min ogni 15 min (o più: GitHub le ritarda) |
| Comandi Telegram | risposta immediata | alla finestra successiva |
| Strategie | A, B, C, D, E | B, C, D, E |
| Dashboard | privata con password (facoltativa) | pubblica in sola lettura |

## ⭐ VPS: bot attivo 24/7 (circa 20 minuti, quasi tutto automatico)

> **Stato attuale:** VPS Hetzner **CX23** (2 vCPU, 4 GB) a Falkenstein, **7,31 €/mese** IVA e IPv4 inclusi,
> creata il 1° novembre 2026 dal workflow **memecoin VPS create (Hetzner)**; portafoglio paper importato dal
> bot su GitHub (2,0021 SOL), bot su GitHub disattivato. La dashboard su GitHub Pages non si aggiorna più.

**Cosa fai tu:** crei l'account e la VPS e incolli un testo. **Cosa fa il server da solo:** installa tutto,
importa il portafoglio paper attuale da GitHub, si protegge (firewall), riparte da solo dopo crash o
riavvii, e si aggiorna da solo quando io miglioro il codice — solo con versioni che hanno superato i test,
e se una versione non parte torna automaticamente a quella precedente. Resta **sempre in paper trading**.

Prima di proportela, l'installazione è stata provata da cima a fondo su una macchina Ubuntu 24.04 pulita
(workflow **memecoin VPS rehearsal** nel tab Actions): raccolta dati continua, stato importato,
crash del bot con ripartenza automatica, riavvio con dati conservati, dashboard HTTPS.

### V1. Prepara il testo da incollare
Copia il contenuto del file
[`deploy/cloud-config.yaml`](deploy/cloud-config.yaml) (qui sotto c'è uguale) in un editor di testo e
sostituisci le due righe `INCOLLA_QUI_...` con **il token del bot** (BotFather → `/mybots` → il tuo bot →
**API Token**) e **il tuo chat id**. Non mandarmeli in chat.

```yaml
#cloud-config
write_files:
  - path: /etc/mci/config.env
    permissions: "0600"
    content: |
      MCI_TELEGRAM_BOT_TOKEN=INCOLLA_QUI_IL_TOKEN_DI_BOTFATHER
      MCI_TELEGRAM_CHAT_IDS=INCOLLA_QUI_IL_TUO_CHAT_ID
      DOMAIN=
      DUCKDNS_TOKEN=
      MCI_DASHBOARD_PASSWORD=
      MCI_JUPITER_API_KEY=
runcmd:
  - curl -fsSL https://raw.githubusercontent.com/gennaro-rescigno/percorso-tutor/main/memecoin-intelligence/deploy/vps.sh -o /root/vps.sh
  - bash /root/vps.sh install
```

*(Facoltativo, per la dashboard web con password)* su **https://www.duckdns.org** entra con GitHub,
scrivi un nome (es. `memogenn`) → **add domain**, copia il **token** in alto e compila
`DOMAIN=memogenn.duckdns.org` e `DUCKDNS_TOKEN=...`. L'indirizzo IP lo imposta il server da solo.

### V2. Crea l'account (esempio: Hetzner Cloud, Germania/Finlandia, fatturazione a ore)
1. **https://www.hetzner.com/cloud** → **Sign up** → conferma l'email → inserisci i dati e un metodo di
   pagamento (carta o PayPal). Per gli account nuovi Hetzner può chiedere una verifica d'identità.
2. Nella console crea un progetto (es. `memecoin`).

### V3. Crea la VPS
**Add Server** / **Create Server** e scegli:
* **Location**: una qualsiasi in Europa (Falkenstein, Norimberga, Helsinki).
* **Image**: **Ubuntu 24.04**.
* **Type**: la più economica disponibile con **almeno 2 GB di RAM** (il sistema ne usa circa 0,2 GB;
  funziona sia x86 sia Arm). Se compare *non disponibile*, prova un'altra location o il tipo successivo.
* **Networking**: lascia attivo **IPv4 pubblico** (serve: GitHub e alcune API non hanno IPv6).
* **SSH keys**: puoi saltare (ti arriva via email una password di emergenza). **Firewall**: nessuno (lo
  configura lo script). **Backups**: non necessari (il server fa un backup giornaliero del database).
* **Cloud config** (o *User data*): incolla il testo del punto V1.
* **Name**: `memecoin-bot` → controlla il prezzo mostrato → **Create & Buy now**.

### V4. Aspetta il messaggio su Telegram (10–15 minuti)
Il bot ti scrive **«✅ VPS pronta: il bot gira 24/7 in modalità PAPER»** (con indirizzo e password della
dashboard se hai compilato DuckDNS). Poi scrivimi «fatto»: io spengo il bot su GitHub, così non ci sono due
bot che rispondono agli stessi comandi.

**Se dopo 20 minuti non arriva nulla:** console Hetzner → server → **Console** (icona `>_`), accedi come
`root` con la password ricevuta via email e scrivi `bash /opt/mci/repo/memecoin-intelligence/deploy/vps.sh status`:
mandami la parte finale *senza* righe che contengono token o password (lo script non le stampa mai).

### Altri provider (OVH, Netcup, Contabo, IONOS...)
Funziona su qualsiasi VPS **Ubuntu 22.04/24.04** con almeno 2 GB di RAM (lo script aggiunge 2 GB di swap
sotto i 3,5 GB). Se il provider ha il campo *cloud-init / user data*, incolla lo stesso testo. Altrimenti, dalla
console web del provider:
```bash
mkdir -p /etc/mci && nano /etc/mci/config.env      # incolla le righe MCI_... / DOMAIN=... e salva
curl -fsSL https://raw.githubusercontent.com/gennaro-rescigno/percorso-tutor/main/memecoin-intelligence/deploy/vps.sh | bash -s install
```

### Gestione
* **Stato:** `bash /opt/mci/repo/memecoin-intelligence/deploy/vps.sh status` (dalla console del provider).
* **Cambiare token/chat id/dominio:** modifica `/etc/mci/config.env` e rilancia `... vps.sh install`
  (dati e password esistenti vengono mantenuti).
* **Spegnere e smettere di pagare:** console Hetzner → server → **Delete**. Spegnere (*Power off*) non basta:
  una VPS spenta si paga lo stesso. Prima di cancellarla puoi tornare al bot su GitHub (il portafoglio paper
  ripartirebbe dall'ultimo stato salvato su GitHub).

**Onestamente, cosa può ancora andare storto:** nessun sistema funziona al 100%. Le API gratuite
(DexScreener, GeckoTerminal, Jupiter, RugCheck, PumpPortal) possono rallentare o fermarsi per qualche minuto:
il bot lo segnala, salta quel dato e non lo trasforma mai in un segnale positivo. Il provider garantisce in
genere ~99,9% di disponibilità (circa 40 minuti di fermo al mese nel caso peggiore); dopo un riavvio il bot
riparte da solo. Il rischio di trading non c'entra: si resta in paper trading.

---

## Gratis: GitHub Actions (nessun server, nessun nuovo account, PC spento)

Il bot gira **gratis sui server di GitHub**, nel tuo repository, ogni ~15 minuti. È già tutto
configurato e verificato dal vivo (5 esecuzioni reali: tutte le fonti OK, 168 token analizzati, primo
trade paper eseguito con quote reale di Jupiter).

### 1. Revoca il vecchio token del bot (urgente: è stato pubblicato)
Il token era stato scritto in `.env.example`, che è **pubblico**. Su Telegram apri **@BotFather** →
`/revoke` → scegli il tuo bot → BotFather ti dà un **nuovo token**. Il vecchio smette di funzionare.

### 2. Attiva l'esecuzione automatica (1 clic)
Il codice è sul branch `feature/memecoin-intelligence`; GitHub esegue i workflow programmati solo dal
branch principale `main`. Apri
**https://github.com/gennaro-rescigno/percorso-tutor/compare/main...feature/memecoin-intelligence**
→ **Create pull request** → **Create pull request** → **Merge pull request** → **Confirm merge**.

### 3. Dai al bot il NUOVO token Telegram (in modo segreto)
1. Apri **https://github.com/gennaro-rescigno/percorso-tutor/settings/secrets/actions**
   (oppure: repository → **Settings** → **Secrets and variables** → **Actions**).
2. **New repository secret** → Name: `MCI_TELEGRAM_BOT_TOKEN` → Secret: il token di BotFather → **Add secret**.
3. **New repository secret** → Name: `MCI_TELEGRAM_CHAT_IDS` → Secret: il tuo chat id → **Add secret**.

I segreti di GitHub sono cifrati: nessuno li vede (nemmeno nei log, dove compaiono come `***`).
Dalla prossima esecuzione (entro ~15 minuti) il bot ti scrive su Telegram.

### 4. La dashboard web (già attiva)
È pubblicata automaticamente su **https://gennaro-rescigno.github.io/percorso-tutor/** (branch
`gh-pages`, aggiornato a ogni esecuzione del bot).

È in **sola lettura** e **pubblica** (contiene solo dati di paper trading e analisi di token pubblici,
nessun segreto): i comandi si danno da Telegram (`/status`, `/pause`, `/resume`, `/kill`, ...).

### Cosa cambia rispetto a un server sempre acceso (onestamente)
| | Server 24/7 (Oracle) | GitHub Actions |
|---|---|---|
| Costo / account | 0 € / account Oracle + carta | 0 € / nessun nuovo account |
| Frequenza | scansione ogni 60 s, posizioni ogni 20 s | finestre di ~3 min ogni ~15 min (GitHub può ritardarle di 10–30 min) |
| Risposta ai comandi Telegram | immediata | alla finestra successiva |
| Strategie attive | A, B, C, D, E | B, C, D, E (la A richiede reattività al minuto) |
| Stop loss | controllati ogni 20 s | controllati a ogni finestra: in un crollo il prezzo di uscita può essere molto peggiore dello stop (il paper trading lo registra fedelmente) |
| Dashboard | privata con password | pubblica in sola lettura |

**Regole di GitHub:** i termini di GitHub Actions vietano usi "non collegati" al progetto software del
repository. Qui il workflow esegue, testa e pubblica i dati del progetto stesso, con esecuzioni brevi e
programmate; è comunque un uso al limite: GitHub può sospendere i workflow se li ritiene eccessivi. In quel
caso basta passare alla soluzione con server (punti 2 sotto), senza perdere nulla: lo stato è salvato nel
branch `bot-state`.

**Spegnere il bot:** tab **Actions** → **memecoin-bot** → **⋯** → **Disable workflow**.
**Inattività:** GitHub disattiva i workflow programmati dopo 60 giorni senza attività sul repository: se
ricevi l'email, riattivalo dallo stesso menu.

**Backtest dal browser:** tab **Actions** → **memecoin-backtest** → **Run workflow** (eventualmente con l'ID
della query Dune del punto 4 e il secret `MCI_DUNE_API_KEY`). Il report compare nella pagina dell'esecuzione.

---

## Alternativa: server sempre acceso

Ordine consigliato: **1 → 2 → 4**. Il punto 3 è facoltativo.

| # | Cosa | Costo | Serve un account? | Tempo |
|---|---|---|---|---|
| 1 | Bot Telegram | 0 € | il tuo Telegram | 5 min |
| 2 | Server gratuito Oracle + installazione | 0 € (carta solo per verifica identità) | Oracle Cloud, DuckDNS | 45–60 min |
| 3 | Sbloccare la rete della sessione Claude (facoltativo) | 0 € | quello che usi già | 3 min |
| 4 | Storico per il backtest con Dune | 0 € (piano Free: 2.500 crediti/mese) | Dune | 15 min + 2–4 h di download automatico |

> **Regole d'oro**
> * Il **token del bot**, le **password** e le **chiavi API** vanno SOLO nel file `.env` sul server.
>   Mai in chat (nemmeno a me), mai su GitHub, mai in screenshot.
> * Il sistema parte in **paper trading**: non usa soldi veri e non serve nessun wallet.

---

## 1. Bot Telegram

### 1.1 Crea il bot
1. Su Telegram cerca **@BotFather** (ha la spunta blu) e premi *Avvia*.
2. Scrivi `/newbot`.
3. Ti chiede un **nome** (es. `Memecoin Intelligence`), poi uno **username** che deve finire con `bot`
   (es. `gennaro_memecoin_bot`).
4. BotFather risponde con un **token** del tipo `1234567890:AAH...` → copialo in un posto sicuro
   (es. le Note del telefono, temporaneamente).

### 1.2 Trova il tuo chat id (metodo ufficiale, senza bot di terze parti)
1. Apri il tuo nuovo bot su Telegram e premi **Avvia** (o scrivi `ciao`). È obbligatorio: un bot non
   può scriverti se non gli hai mai scritto tu.
2. Dal browser apri questo indirizzo, sostituendo `IL_TUO_TOKEN`:
   `https://api.telegram.org/botIL_TUO_TOKEN/getUpdates`
3. Nella pagina cerca `"chat":{"id":` → il numero che segue (es. `987654321`) è il tuo **chat id**.
   Se la pagina mostra `"result":[]`, scrivi di nuovo al bot e ricarica.

### 1.3 Dove si mettono (lo farai al passo 2.8)
Sul server, nel file `.env` dentro la cartella `memecoin-intelligence`:
```
MCI_TELEGRAM_BOT_TOKEN=1234567890:AAH...il tuo token...
MCI_TELEGRAM_CHAT_IDS=987654321
```
Se il token finisse per errore in un posto pubblico: BotFather → `/revoke` → scegli il bot → nuovo token.

---

## 2. Server gratuito su Oracle Cloud

### 2.1 Prepara la chiave SSH sul tuo PC (serve per collegarti al server)
*Windows 10/11*: apri **PowerShell**. *Mac*: apri **Terminale**. Scrivi:
```
ssh-keygen -t ed25519 -C "oracle-vm"
```
Premi **Invio** tre volte (percorso predefinito, nessuna passphrase o una a tua scelta). Poi mostra la
chiave **pubblica**:
* Windows: `type $env:USERPROFILE\.ssh\id_ed25519.pub`
* Mac: `cat ~/.ssh/id_ed25519.pub`

Copia tutta la riga che inizia con `ssh-ed25519`. (Il file **senza** `.pub` è la chiave privata: non
condividerlo mai.)

### 2.2 Crea l'account Oracle Cloud (gratuito)
1. Vai su **https://signup.oraclecloud.com** e scegli il piano **Free Tier**.
2. Inserisci email, nazione, nome; conferma l'email.
3. **Home Region**: scegli con attenzione, **non si può cambiare dopo** e le risorse gratuite esistono
   solo lì. Per l'Italia vanno bene *Italy Northwest (Milan)* o *Germany Central (Frankfurt)*.
4. **Carta di credito/debito**: serve solo a verificare l'identità. Può comparire una piccola
   autorizzazione temporanea che viene annullata. Le prepagate a volte vengono rifiutate.
5. Fine: per 30 giorni hai anche 300 $ di prova; dopo, l'account resta **Always Free** automaticamente.

> ⚠️ **Per restare a 0 €**
> * **NON** premere *Upgrade to Pay As You Go*: con il piano gratuito non puoi essere addebitato.
> * Crea solo risorse con l'etichetta **"Always Free-eligible"**.
> * Consigliato: *Billing & Cost Management → Budgets → Create Budget*, importo **1**, avviso al 100%
>   via email. Se mai qualcosa costasse, lo sapresti subito.

### 2.3 Crea la macchina virtuale
Menu ☰ → **Compute → Instances → Create instance**:
1. **Name**: `memecoin`.
2. **Image**: *Change image* → **Ubuntu** → **Canonical Ubuntu 24.04** (non la versione "Minimal").
3. **Shape**: *Change shape* → **Ampere** → **VM.Standard.A1.Flex** → **1 OCPU, 4 GB** di memoria.
   Deve comparire *Always Free-eligible*. (Il limite gratuito 2026 è 2 OCPU / 12 GB in totale: 1/4 basta
   e lascia margine.)
4. **Networking**: *Create new virtual cloud network* + *Create new public subnet*, e
   **Automatically assign public IPv4 address** attivo.
5. **Add SSH keys**: *Paste public keys* → incolla la riga `ssh-ed25519 ...` del passo 2.1.
6. **Boot volume**: lascia il default (rientra nei 200 GB gratuiti).
7. **Create**. Quando lo stato è **Running**, copia il **Public IP address** (es. `140.238.10.20`).

**Errore "Out of capacity"?** Succede spesso con Ampere. Riprova più tardi (anche il giorno dopo), oppure
scegli un'altra *Availability domain*, oppure usa la shape **VM.Standard.E2.1.Micro** (Always Free,
1 GB di RAM: funziona grazie allo swap creato dallo script, ma la prima installazione è più lenta).

### 2.4 Apri le porte 80 e 443 (per la dashboard in HTTPS)
Nella pagina dell'istanza → sezione *Primary VNIC* → clic sulla **Subnet** → **Security Lists** →
*Default Security List* → **Add Ingress Rules**:
* Source CIDR `0.0.0.0/0`, IP Protocol **TCP**, Destination Port Range **80** → *Add*.
* Ripeti con la porta **443**.

(La porta 22 per SSH è già aperta di default.)

### 2.5 Indirizzo web gratuito con DuckDNS
1. Vai su **https://www.duckdns.org** e accedi con GitHub o Google (gratis, nessuna carta).
2. Scrivi un nome (es. `gennaro-memecoin`) → **add domain**.
3. Nel campo **current ip** del dominio incolla l'IP pubblico della VM → **update ip**.
4. Il tuo indirizzo è `gennaro-memecoin.duckdns.org`.

### 2.6 Collegati al server
Dal PowerShell/Terminale del passo 2.1:
```
ssh ubuntu@IL_TUO_IP_PUBBLICO
```
Alla domanda *Are you sure you want to continue connecting* scrivi `yes`. Ora sei sul server.

### 2.7 Installa il sistema
Copia e incolla queste righe una alla volta:
```
sudo apt-get update && sudo apt-get install -y git
git clone https://github.com/gennaro-rescigno/percorso-tutor.git
cd percorso-tutor/memecoin-intelligence
git checkout feature/memecoin-intelligence
bash deploy/oracle-setup.sh
```
Lo script installa Docker, apre le porte nel firewall interno di Ubuntu, crea lo swap, crea il file
`.env` con una password del database e una chiave segreta **casuali** (generate sul server, nessuno le
conosce) e stampa l'IP pubblico.

### 2.8 Inserisci le tue impostazioni nel file `.env`
```
nano .env
```
Modifica solo queste righe (frecce per muoverti):
```
DOMAIN=gennaro-memecoin.duckdns.org
MCI_DASHBOARD_PASSWORD=una-password-lunga-che-scegli-tu
MCI_TELEGRAM_BOT_TOKEN=1234567890:AAH...
MCI_TELEGRAM_CHAT_IDS=987654321
```
Salva con **Ctrl+O**, **Invio**, esci con **Ctrl+X**. Non toccare `MCI_TRADING_MODE=paper`.

### 2.9 Avvia
```
sudo docker compose up -d --build
```
La prima volta impiega 10–20 minuti (scarica e compila tutto). Poi controlla:
```
sudo docker compose ps                              # 5 servizi "running"/"Up"
sudo docker compose exec worker mci check-sources   # le fonti devono essere OK
sudo docker compose exec worker mci telegram-test   # ti arriva un messaggio su Telegram
```
Apri **https://gennaro-memecoin.duckdns.org** → utente `admin`, password = `MCI_DASHBOARD_PASSWORD`.
Su Telegram scrivi `/status` al bot.

Da qui il sistema gira 24/7 anche a PC spento, riparte da solo dopo errori o riavvii del server e
registra ogni token scoperto (costruendo lo storico per il backtest).

### 2.10 Comandi utili (sempre dalla cartella `~/percorso-tutor/memecoin-intelligence`)
| Cosa | Comando |
|---|---|
| Vedere cosa fa il worker | `sudo docker compose logs -f worker` (esci con Ctrl+C) |
| Aggiornare il codice | `git pull && sudo docker compose up -d --build` |
| Applicare modifiche al `.env` | `sudo docker compose up -d` |
| Fermare tutto | `sudo docker compose down` (i dati restano) |

### 2.11 Problemi noti
* **La dashboard non si apre in HTTPS**: controlla porte 80/443 (2.4), che DuckDNS abbia l'IP giusto (2.5)
  e `sudo docker compose logs caddy`. Il certificato viene creato al primo accesso (1–2 minuti).
* **Il bot non risponde**: hai premuto *Avvia* sul bot? Il chat id è giusto? `sudo docker compose logs worker`.
* **Email di Oracle sull'istanza inattiva**: il bot usa poca CPU e Oracle può *fermare* le VM gratuite
  poco usate. Non si perde nulla: *Compute → Instances → memecoin → Start* e tutto riparte da solo.
  L'unico modo per evitarlo del tutto è passare a Pay As You Go, che però espone ad addebiti: sconsigliato
  se vuoi restare a 0 €.

---

## 3. (Facoltativo) Sbloccare la rete della sessione Claude Code

Serve solo per permettermi di verificare le API e scaricare dati **da qui**. Il server del punto 2 non
ne ha bisogno.

1. Nell'app Claude, in alto nella barra del titolo di questa sessione apri il menu dell'**ambiente cloud**
   → **Edit**.
2. **Network access** → livello **Limited** (in alcune versioni dell'app si chiama **Custom**) →
   **Allowed domains**, lasciando spuntato **Allow package managers**.
3. Aggiungi questi domini, uno per riga:
   ```
   api.dexscreener.com
   api.geckoterminal.com
   lite-api.jup.ag
   api.jup.ag
   api.rugcheck.xyz
   pumpportal.fun
   api.mainnet-beta.solana.com
   api.coingecko.com
   api.kraken.com
   api.dune.com
   ```
4. Salva e scrivimi "fatto". Se in questa sessione non funziona ancora, apri una nuova sessione: le
   impostazioni di rete valgono per i nuovi container.

Guida ufficiale: https://code.claude.com/docs/en/cloud-environments#network-access

---

## 4. Storico per il backtest con Dune (gratis)

Perché: per un backtest onesto servono **tutti** i token lanciati in un periodo, anche quelli falliti.
Dune contiene ogni lancio Pump.fun; il sistema ne prende un **campione casuale** (scelto senza guardare
come è andato) e scarica i prezzi da GeckoTerminal.

### 4.1 Account e chiave API
1. Vai su **https://dune.com** → **Sign up** (gratis, piano *Free*: 2.500 crediti al mese, nessuna carta).
2. In alto a destra: icona del profilo → **Settings** → **API** → **Create new API key** → copiala.

### 4.2 Crea la query
1. **Create → New query**.
2. Incolla:
   ```sql
   SELECT
     account_mint    AS mint,
     call_block_time AS created_at,
     symbol
   FROM pumpdotfun_solana.pump_call_create
   WHERE call_block_time >= NOW() - INTERVAL '90' DAY
     AND call_block_time <  NOW() - INTERVAL '3' DAY
   ORDER BY rand()
   LIMIT 3000
   ```
   (90 giorni perché lo storico prezzi gratuito di GeckoTerminal arriva a 6 mesi; `ORDER BY rand()` =
   campione casuale; esclusi gli ultimi 3 giorni perché i token devono avere un "dopo" da osservare.)
3. **Run**. Dovresti vedere 3.000 righe con `mint`, `created_at`, `symbol`.
   Se compare un errore su una colonna, apri `https://dune.com/data/pumpdotfun_solana.pump_call_create`
   per vedere i nomi esatti e scrivimeli.
4. **Save** (nome: `mci universe`). L'indirizzo della pagina diventa `https://dune.com/queries/1234567`:
   il numero finale è l'**ID della query**.

Consumo: lettura di 3.000 righe × 3 colonne ≈ pochi crediti (il piano Free ne dà 2.500 al mese; Dune
addebita circa 20 crediti per MB esportato e questo risultato è ben sotto 1 MB). Puoi controllare nella
pagina *Usage* di Dune.

### 4.3 Metti la chiave sul server e lancia l'import
Sul server (`ssh ubuntu@IP`, poi `cd percorso-tutor/memecoin-intelligence`):
```
nano .env          # imposta: MCI_DUNE_API_KEY=la-tua-chiave   (Ctrl+O, Invio, Ctrl+X)
sudo docker compose up -d
sudo docker compose exec -d worker sh -c "mci import-universe --dune-query-id 1234567 --sample 500 > /app/reports/import.log 2>&1"
tail -f reports/import.log     # avanzamento (Ctrl+C per uscire: l'import continua)
```
Dura **2–4 ore** perché rispetta il limite gratuito di GeckoTerminal (30 richieste/minuto); puoi
chiudere il PC. Alla fine il log mostra:
* il file creato (`data/universe_AAAAMMGG_HHMM.json`);
* la **copertura** (quanti token hanno dati di prezzo);
* se il dataset è **privo di survivorship bias**: è "sì" solo se almeno il 90% dei token estratti ha
  dati. Se è "NO" vuol dire che GeckoTerminal non ha i prezzi dei token rimasti in bonding curve: in quel
  caso il sistema lo dichiara e i risultati vanno considerati ottimistici.

### 4.4 Lancia i backtest
```
sudo docker compose exec worker mci compare-profiles --dataset data/universe_AAAAMMGG_HHMM.json --strategies A,B,C --out /app/reports/confronto_profili.md
cat reports/confronto_profili.md
```
Oppure dalla dashboard: **Backtest Lab → Dati: "storico importato da Dune"**.

Nota onesta: questo storico contiene solo prezzi e volumi. Holder, sicurezza e social *al momento del
segnale* non esistono nel passato, quindi questi backtest misurano solo la parte prezzo/volume delle
strategie (il report lo indica). Il backtest completo arriva dai dati che il server registra da solo
(dopo alcune settimane: `mci backtest` senza `--dataset`).

---

## Riepilogo costi

| Voce | Costo |
|---|---|
| VPS (solo se scegli questa opzione, es. Hetzner con IPv4) | ~8–10 €/mese IVA inclusa, a ore |
| Telegram bot | 0 € |
| Oracle VM Always Free (1 OCPU Ampere, 4 GB, disco incluso) | 0 € |
| DuckDNS + certificato HTTPS Let's Encrypt | 0 € |
| API di mercato usate dal sistema | 0 € |
| Dune piano Free | 0 € |
| Rete della sessione Claude | 0 € |
| **Totale** | **0 €/mese** con GitHub Actions o Oracle · **~8–10 €/mese** con una VPS |
