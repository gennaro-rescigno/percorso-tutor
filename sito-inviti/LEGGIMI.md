# Inviti — come funziona e come si usa

Un solo sito, un invito diverso per ogni persona, e nessuno che possa
leggere l'invito di un altro.

---

## Cosa c'è dentro

```
sito-inviti/
├── pubblico/          ← SOLO QUESTA cartella finisce online
│   ├── index.html         pagina neutra: chi capita qui non trova niente
│   ├── robots.txt         dice a Google di non indicizzare nulla
│   ├── motore/            il codice, uguale per tutti gli inviti
│   ├── i/<indirizzo>/     l'invito degli ospiti  (uno per festa)
│   └── c/<indirizzo>/     le conferme della festeggiata (uno per festa)
├── backend/Codice.gs  lo script da incollare dentro il foglio Google
├── modelli/           gli stampi da cui nascono le pagine nuove
├── strumenti/
│   └── nuovo_invito.py   il comando che crea un invito nuovo
├── impostazioni.json  i due indirizzi, da riempire una volta sola
├── registro.md        l'elenco privato di tutto (NON va su GitHub)
└── netlify.toml       le istruzioni per il servizio che pubblica il sito
```

Il **motore** è uno solo per tutti. Se domani sistemo un dettaglio della
grafica, lo sistemo una volta e cambia in tutti gli inviti già mandati.
Ogni invito, da solo, pesa **4 KB**: mille inviti sono 4 MB, non 250.

---

## Perché nessuno può entrare dove non deve

1. **L'indirizzo non si indovina.** `marta-18-fg79gxy48gsu` — quelle
   dodici lettere finali sono sorteggiate fra 31 caratteri: le
   combinazioni sono più di 800 mila miliardi di miliardi. Provarle a
   caso non è una cosa che si fa.
2. **I due indirizzi non si assomigliano.** Chi ha il link degli ospiti
   non può ricavarne quello della festeggiata: la parte finale è
   sorteggiata due volte, in modo indipendente.
3. **Il sito non è cercabile.** `robots.txt` e l'intestazione
   `X-Robots-Tag: noindex` tengono tutto fuori da Google, e la pagina
   iniziale non elenca niente.
4. **La repository è privata.** Su GitHub pubblico i nomi delle cartelle
   si vedrebbero: sarebbe come pubblicare l'elenco dei link.
5. **Le lettere le apre solo lei.** Il codice a sei caratteri non è
   scritto da nessuna parte nel sito: viaggia verso il foglio Google, che
   risponde soltanto se è quello giusto. Chi arriva sulla pagina delle
   conferme senza codice vede una serratura chiusa e basta.
6. **I messaggi sono davvero anonimi.** Del messaggio parte solo il
   testo — niente nome, niente orario — e la lista arriva mescolata.
   Non c'è modo di risalire a chi ha scritto cosa: non è una promessa,
   è che il dato non esiste.

---

## PARTE 1 — Il GitHub nuovo (una volta sola)

### 1.1 Fai l'account
[github.com](https://github.com) → **Sign up**. Usa un'altra email
(anche un alias, tipo `tuonome+inviti@gmail.com`).

### 1.2 Crea la repository, **privata**
**New repository** → nome `inviti` → spunta **Private** → **Create**.

> Deve essere privata. Su una pubblica, i nomi delle cartelle dentro
> `pubblico/i/` si leggono da chiunque, e i link segreti smettono di
> essere segreti.

### 1.3 Porta dentro questa cartella
Sul computer, dentro la cartella `sito-inviti`:

```bash
git init
git add .
git commit -m "primo caricamento"
git branch -M main
git remote add origin https://github.com/TUONOME/inviti.git
git push -u origin main
```

Il lavoro fatto finora non si perde: resta anche nella repository
vecchia, che puoi lasciare dov'è.

---

## PARTE 2 — Il foglio Google (una volta sola)

### 2.1 Il foglio
[sheets.new](https://sheets.new) → chiamalo **Inviti**. Crea tre schede
(le linguette in basso), **con questi nomi esatti**:

| scheda | prima riga (le intestazioni) |
|---|---|
| `Registro` | invito · festeggiata · codice · apertura · creato |
| `Messaggi` | invito · quando · testo |
| `Conferme` | invito · id · quando · nome · presente · ospiti · allergie · note |

### 2.2 Lo script
Dentro il foglio: **Estensioni → Apps Script**. Cancella tutto quello che
c'è e incolla il contenuto di `backend/Codice.gs`. Salva.

### 2.3 Pubblica lo script
**Distribuisci → Nuova distribuzione** → tipo **App web** →
*Esegui come:* **me** → *Chi ha accesso:* **Chiunque** → **Distribuisci**.
Autorizza (Google avvisa che lo script è tuo: è normale, va bene).

Copia l'indirizzo che finisce con `/exec`.

> "Chiunque" vuol dire che chiunque può *mandare* un messaggio — ed è
> quello che serve, gli invitati non hanno un account. Ma per *leggere*
> serve il codice, e il codice ce l'ha solo lei.

---

## PARTE 3 — Mettere il sito online (una volta sola)

Va bene **Netlify**, che pubblica anche da repository private, gratis.

1. [netlify.com](https://netlify.com) → entra con GitHub
2. **Add new site → Import an existing project** → scegli `inviti`
3. *Publish directory:* **`pubblico`** ← l'unica cosa da cambiare
4. **Deploy**

Ti dà un indirizzo tipo `https://inviti-gennaro.netlify.app`.
Con `netlify.toml` già dentro, pubblica solo `pubblico/` e mette da sola
il `noindex`: `registro.md` e `impostazioni.json` restano fuori.

### Ultimo passo: `impostazioni.json`

```json
{
  "backend": "https://script.google.com/macros/s/AKfy.../exec",
  "sito": "https://inviti-gennaro.netlify.app"
}
```

Da qui in poi ogni invito nuovo se li prende da solo.

---

## PARTE 4 — Un invito nuovo (ogni volta)

```bash
python3 strumenti/nuovo_invito.py
```

Ti fa le domande una per una. Oppure tutto in una riga:

```bash
python3 strumenti/nuovo_invito.py \
  --nome "Giulia Ferrara" --eta 18 \
  --quando 2027-09-12T21:00 \
  --luogo "Villa Aurora" --indirizzo "Via Roma 4, Salerno" \
  --tema discoteca \
  --whatsapp "https://chat.whatsapp.com/ABC123" \
  --dresscode "Elegante" --scadenza 2027-09-01
```

I temi: `cipria` · `discoteca` · `neve` · `spazio` · `casino` · `calcio`.

Alla fine stampa tre cose:

1. **la riga da incollare** nella scheda `Registro` del foglio Google
   → senza questa riga l'invito non è riconosciuto e non salva niente;
2. **il link degli ospiti** → `.../i/giulia-18-.../`
3. **il link della festeggiata** + il suo **codice** → `.../c/giulia-.../`

Poi si pubblica:

```bash
git add pubblico/
git commit -m "invito di Giulia"
git push
```

Netlify se ne accorge da sola: in un minuto è online.

> La colonna `apertura` del Registro, se la lasci vuota, fa vedere i
> messaggi subito. Se ci metti `2027-09-12T21:00`, le lettere restano
> chiuse fino a quel momento — si vedono le buste sigillate e il conto,
> ma non il contenuto.

---

## PARTE 5 — Cosa mandare, e a chi

**Agli invitati** (gruppo, uno per uno, come preferisci):

> Ci sei anche tu 💌
> https://inviti-gennaro.netlify.app/i/giulia-18-9ytcvqhcrzw6/

**Solo a lei**, in privato:

> Questa pagina è tua. Il codice è **5K88B9**, non darlo a nessuno.
> https://inviti-gennaro.netlify.app/c/giulia-3cbfsunrbtuw/

Due messaggi separati, e il link di lei mai nel gruppo.

---

## Le cose che sa fare

- **Non ci si prenota due volte.** Se scrivi un nome che c'è già, la
  pagina avvisa: *«In lista c'è già Mario Rossi»*, e offre due strade —
  cambiare nome, oppure confermare che sei un'altra persona (e allora
  conviene aggiungere qualcosa: *Mario Rossi (cugino)*). Il controllo
  non guarda maiuscole, accenti e spazi doppi.
- **Lei può togliere qualcuno.** Sulla pagina delle conferme, il cestino
  accanto a ogni riga. Chiede conferma, e il totale si aggiorna.
- **Il gruppo WhatsApp.** C'è in tutti e sei i temi. Il link si mette in
  `--whatsapp`, anche dopo: basta cambiarlo nel `config.js` di
  quell'invito e ripubblicare.
- **Quello che scrivi non si perde.** Se chiudi l'app a metà di un
  messaggio, quando torni lo ritrovi lì.

---

## Se qualcosa non va

| cosa vedi | cos'è |
|---|---|
| *"Modo prova: non c'è ancora il foglio Google"* | `impostazioni.json` è vuoto, oppure l'invito è stato creato prima di riempirlo |
| *"Codice sbagliato"* anche col codice giusto | manca la riga nel `Registro`, o il codice là dentro è diverso |
| la pagina non si apre affatto | l'indirizzo va copiato **tutto**, barra finale compresa |
| ho cambiato il motore e non si vede | serve `git push`: Netlify pubblica quello che c'è su GitHub |

---

## Le due cose da non fare

1. **Non rendere pubblica la repository.**
2. **Non mettere `registro.md` su GitHub** (il `.gitignore` lo tiene già
   fuori). Se lo perdi non è un dramma: i codici sono anche nel foglio
   Google, e i link sono i nomi delle cartelle dentro `pubblico/`.
