# Invito digitale per un diciottesimo

Un invito che si apre come una busta, con conto alla rovescia, conferma di
presenza e — la parte che conta — una **cassetta di messaggi anonimi** per
la festeggiata: gli invitati le scrivono qualcosa prima che diventi
maggiorenne, e solo lei potrà leggerli.

Arriva in tre versioni, si sceglie con una riga:

| | `"cipria"` | `"discoteca"` | `"neve"` |
|---|---|---|---|
| **colori** | rosa e oro rosa | nero, magenta e ciano | azzurro e bianco |
| **carattere** | corsivo elegante (Parisienne) | insegna al neon (Monoton) | serif d'inverno (Fraunces) |
| **sfondo** | pioggia di brillantini e giardino di rose | palla specchiata, fasci di luce e pista | fiocchi di neve e cumuli |
| **in più** | ceralacca con le iniziali | il nome al neon che tremola | neve posata su scritte, pulsanti, campi e riquadri |

Cambia solo l'aspetto: testi, messaggi anonimi e conferme funzionano identici.

Tutto è già pronto: **devi cambiare solo `config.js`**.

---

## Cosa c'è dentro

| File | A cosa serve | Lo devi toccare? |
|---|---|---|
| **`config.js`** | nome, data, ora, luogo, frasi, programma | **sì, solo questo** |
| `index.html` | l'invito che vedono gli ospiti | no |
| `messaggi.html` | la pagina privata dove la festeggiata legge le lettere | no |
| `assets/css/stile.css` | la struttura e il tema cipria | solo se vuoi cambiare stile |
| `assets/css/discoteca.css` | il tema discoteca | solo se vuoi cambiare stile |
| `assets/css/neve.css` | il tema neve | solo se vuoi cambiare stile |
| `assets/js/*.js` | il funzionamento | no |
| `backend/Codice.gs` | lo script che salva le risposte nel foglio Google | lo incolli su Google |
| `backend/ISTRUZIONI.md` | la guida passo passo per collegare il foglio | leggila |

---

## 1. Scegli il tema

Prima riga di `config.js`:

```js
tema: "cipria",      // oppure "discoteca", oppure "neve"
```

Non serve toccare altro: cambiano colori, caratteri e sfondo di tutte e due
le pagine, invito e cassetta dei messaggi.

## 2. Personalizza (5 minuti)

Apri `config.js` e cambia solo il testo fra le virgolette:

```js
festeggiata: {
  nome: "Marta",          // il nome grande in corsivo
  iniziali: "MP",         // le lettere sulla ceralacca della busta
  eta: 18,
},
evento: {
  quando: "2026-08-04T20:00:00",   // serve al conto alla rovescia
  dataTesto: "4 Agosto 2026",
  oraTesto: "20:00",
  luogo: "Villa dei Fiori",
  ...
}
```

Due regole sole: **non togliere le virgolette** e **non togliere le virgole**
a fine riga. Se qualcosa smette di funzionare, quasi sempre è una di queste due.

Nel file puoi anche:

- riscrivere le frasi dell'invito (sezione `testi`)
- aggiungere o togliere righe del programma della serata
- spegnere una sezione intera mettendo `attivo: false`
  (per esempio se non vuoi le conferme di presenza)

## 3. Metti la musica (facoltativo)

Copia il tuo file dentro `assets/audio/` e scrivi il nome in `config.js`:

```js
musica: { attiva: true, file: "assets/audio/musica.mp3", volume: 0.35 }
```

La musica parte quando l'ospite tocca la busta — prima non può, i telefoni
non lo permettono. Se il file non c'è, il tasto della musica sparisce da solo
e non si rompe niente.

## 4. Collega il foglio Google

Segui **[`backend/ISTRUZIONI.md`](backend/ISTRUZIONI.md)**: dieci minuti, gratis,
e da lì in poi messaggi e conferme arrivano su un foglio che vedi solo tu.

Finché non lo fai il sito gira in **modo prova**: puoi provare tutto, ma le
risposte restano sul telefono di chi le scrive.

## 5. Mettilo online

Il sito è fatto di soli file: va bene qualsiasi hosting gratuito.

**GitHub Pages** (il più semplice, il codice è già qui):
`Settings → Pages → Source: Deploy from a branch → main → /root` → Salva.
Dopo un minuto l'invito è su
`https://<tuo-utente>.github.io/percorso-tutor/invito-digitale/`

**Netlify Drop**: vai su [app.netlify.com/drop](https://app.netlify.com/drop)
e trascina la cartella `invito-digitale`. Ti dà subito un link.

Poi mandi il link su WhatsApp e basta.

> **Anteprima su WhatsApp:** l'immagine e il titolino che compaiono sotto il link
> si prendono dalle righe `og:title` e `og:description` in cima a `index.html`.
> Quelle vanno cambiate a mano, perché WhatsApp legge la pagina prima che si riempia.

## 6. Leggere i messaggi

La festeggiata apre `.../invito-digitale/messaggi.html`, scrive il codice
segreto e legge le lettere.

**Non mandare questo link insieme all'invito.** Non è segreto di per sé: la
protezione vera è il codice, senza il quale il foglio Google non risponde.

---

## Come funziona l'anonimato

Non è una promessa scritta in una frase: è come è fatto il codice.

- Il modulo del messaggio ha **un solo campo**: il testo. Niente nome, niente mail.
- Il sito manda al foglio **solo quel testo**. Non registra chi sei, da dove scrivi,
  che telefono usi.
- In modo collegato il messaggio **non viene salvato sul telefono di chi scrive**
  (succede solo in modo prova, dove non c'è un foglio dove mandarlo).
- Nel foglio si salva **solo la data**, non l'ora: sapere che un messaggio è
  arrivato alle 22:47 può bastare a capire chi l'ha scritto. Se vuoi anche l'ora,
  in `Codice.gs` metti `SALVA_ORARIO = true`.
- Quando la festeggiata li legge, i messaggi le arrivano **in ordine mescolato**,
  così nemmeno l'ordine di arrivo dice qualcosa.

L'unica cosa che resta è quello che scrivono le persone. Che è il punto.

---

## Se vuoi tenerli chiusi fino alla festa

In `backend/Codice.gs`:

```js
var APERTURA_MESSAGGI = '2026-08-04T20:00:00';
```

Da quel momento in poi, se la festeggiata apre la pagina prima della data
vede **quante lettere l'aspettano** ma non può leggerle: compare una fila di
buste ancora sigillate. Il controllo lo fa Google, non il browser: non si
aggira guardando il codice della pagina.
