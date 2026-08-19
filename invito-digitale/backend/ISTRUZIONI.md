# Collegare il foglio Google (10 minuti, gratis)

Finché non fai questi passaggi il sito funziona lo stesso, ma in **modo prova**:
messaggi e conferme restano salvati solo sul telefono di chi li scrive.
Per riceverli davvero serve un foglio Google. Non serve pagare niente.

---

## 1. Crea il foglio

1. Apri **[sheets.new](https://sheets.new)** (devi essere dentro il tuo account Google).
2. Dagli un nome, per esempio `Diciottesimo di Marta — risposte`.

Le due schede `Messaggi` e `Conferme` si creano da sole al primo invio: non toccare niente.

## 2. Incolla lo script

1. Nel foglio, menu in alto: **Estensioni → Apps Script**.
2. Si apre una pagina con dentro qualche riga di codice: **cancella tutto**.
3. Apri il file `Codice.gs` che trovi in questa cartella, copia **tutto** il contenuto e incollalo lì.
4. In alto cambia queste righe:

   ```js
   var CODICE_SEGRETO = 'MARTA18';   // ← mettine uno tuo, è la chiave della festeggiata
   var APERTURA_MESSAGGI = '';       // ← es. '2026-08-04T20:00:00' per tenerli chiusi fino alla festa
   ```

5. Premi l'icona del **dischetto** (Salva).

## 3. Pubblica lo script

1. In alto a destra: **Distribuisci → Nuova distribuzione**.
2. Clicca l'ingranaggio accanto a "Seleziona tipo" e scegli **App web**.
3. Compila così:
   - **Esegui come**: `Io (la tua mail)`
   - **Chi ha accesso**: `Chiunque`
4. **Distribuisci**.
5. Google chiede il permesso: **Autorizza accesso** → scegli il tuo account →
   compare un avviso, clicca **Avanzate** → **Vai a Progetto senza titolo (non sicuro)** → **Consenti**.
   È normale: stai autorizzando uno script scritto da te sul tuo foglio.
6. Copia l'indirizzo che ti dà, quello che finisce con `/exec`.

> **Perché "Chiunque"?** Perché i tuoi invitati devono poter inviare senza fare il login
> con Google. Chi ha il link può solo **scrivere**. Per **leggere** i messaggi serve il
> `CODICE_SEGRETO`, che resta dentro lo script e non compare mai nel sito.

## 4. Incolla l'indirizzo nel sito

Apri `config.js` e mettilo qui:

```js
backend: {
  url: "https://script.google.com/macros/s/AKfy.../exec"
}
```

Salva. Fine: la scritta "Modo prova" sparisce da sola.

## 5. Prova che funzioni

1. Apri l'invito, scrivi un messaggio finto e invialo.
2. Torna sul foglio Google: nella scheda `Messaggi` deve essere comparsa una riga.
3. Apri `messaggi.html`, metti il tuo `CODICE_SEGRETO` e controlla che si veda.
4. Cancella la riga di prova dal foglio.

---

## Se cambi qualcosa nello script, dopo

Le modifiche **non partono da sole**. Ogni volta devi rifare:

**Distribuisci → Gestisci distribuzioni →** icona matita **→ Versione: Nuova versione → Distribuisci**

Così l'indirizzo `/exec` resta lo stesso e non devi ritoccare `config.js`.

---

## Problemi frequenti

| Cosa vedi | Cosa fare |
|---|---|
| "Il messaggio non è partito" | Controlla che l'indirizzo in `config.js` finisca con `/exec` e non con `/dev` |
| "Codice sbagliato" ma il codice è giusto | Hai modificato lo script senza ripubblicarlo: rifai il passaggio qui sopra |
| Il foglio resta vuoto | In "Chi ha accesso" deve esserci `Chiunque`, non `Solo io` |
| Le schede non compaiono | Si creano al primo invio riuscito: manda un messaggio di prova |
