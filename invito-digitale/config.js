/* =====================================================================
   CONFIG.JS  —  L'UNICO FILE CHE DEVI MODIFICARE
   ---------------------------------------------------------------------
   Cambia solo il testo tra le virgolette "cosi".
   Non togliere le virgolette e non togliere le virgole a fine riga.
   Tutto il resto del sito si aggiorna da solo.
   ===================================================================== */

window.CONFIG = {

  /* --- 0. IL TEMA ------------------------------------------------------
     "cipria"    = rosa, glitter e rose (elegante)
     "discoteca" = nero, neon e luci che girano (serata)
     "neve"      = azzurro, fiocchi che scendono e neve posata sopra
     "spazio"    = notte, sistema solare che gira e navicella che parte
     "casino"    = verde e oro, torcia al buio e slot che paga
     "calcio"    = stadio di notte, con un rigore da segnare per entrare  */
  tema: "cipria",

  /* --- 1. CHI FESTEGGIA ---------------------------------------------- */
  festeggiata: {
    nome: "Marta",              // il nome che si legge grande, in corsivo
    iniziali: "MP",             // le lettere stampate sulla ceralacca della busta
    eta: 18,                    // il numero grande in cima all'invito
    articolo: "la",             // "la" per una ragazza, "il" per un ragazzo
    festeggiataDi: "festeggiata" // "festeggiata" oppure "festeggiato"
  },

  /* --- 2. LA FESTA ---------------------------------------------------- */
  evento: {
    // Data e ora in formato ANNO-MESE-GIORNO T ORA:MINUTI:00 (serve al conto alla rovescia)
    quando: "2027-08-04T20:00:00",

    dataTesto: "4 Agosto 2027",   // come vuoi che si legga la data
    oraTesto: "20:00",            // come vuoi che si legga l'ora

    luogo: "Villa dei Fiori",
    indirizzo: "Via Roma 12 — Salerno",
    // Link di Google Maps: cerca il posto su Maps, premi "Condividi" e incolla qui
    mappa: "https://www.google.com/maps/search/?api=1&query=Villa+dei+Fiori+Salerno",

    dressCode: "Elegante",
    notaDressCode: "Niente bianco, per favore"
  },

  /* --- 3. LE FRASI DELL'INVITO ---------------------------------------- */
  testi: {
    // Lascia vuoto "" e ci pensa il tema ("Sali a bordo", "Tira la leva"...)
    istruzioneBusta: "",
    soprannome: "Ti aspetto il",              // frase sopra la data
    apertura: "Diciotto anni si compiono una volta sola.",
    invitoBreve: "Ho scelto le persone giuste per festeggiarli: ci sei anche tu.",
    firma: "Con affetto, Marta"
  },

  /* --- 4. IL PROGRAMMA DELLA SERATA ----------------------------------- */
  // Aggiungi o togli righe copiando il blocco { ora: "...", cosa: "..." },
  programma: [
    { ora: "20:00", cosa: "Arrivo degli ospiti",  dettaglio: "Aperitivo di benvenuto in giardino" },
    { ora: "21:00", cosa: "Cena",                 dettaglio: "Servita ai tavoli" },
    { ora: "23:00", cosa: "Taglio della torta",   dettaglio: "Il momento del brindisi" },
    { ora: "23:30", cosa: "Si balla",             dettaglio: "Fino a quando reggiamo" }
  ],

  /* --- 5. CONFERMA DI PRESENZA (RSVP) --------------------------------- */
  rsvp: {
    attivo: true,                       // metti false se non vuoi le conferme
    scadenzaTesto: "20 luglio 2027",
    chiediAccompagnatori: true,
    chiediAllergie: true
  },

  /* --- 6. I MESSAGGI ANONIMI PER LA FESTEGGIATA ----------------------- */
  messaggi: {
    attivo: true,
    titolo: "Un messaggio per Marta",
    invito: "Scrivile qualcosa prima che diventi maggiorenne: un ricordo, un augurio, una cosa che non le hai mai detto.",
    promessa: "Nessuno saprà mai chi l'ha scritto. Nemmeno Marta.",
    massimoCaratteri: 900,
    ringraziamento: "Il tuo messaggio è partito.",
    ringraziamentoDettaglio: "Resterà chiuso nella busta fino alla sera della festa."
  },

  /* --- 7. LA MUSICA ---------------------------------------------------- */
  musica: {
    attiva: true,
    // Metti il tuo file dentro la cartella assets/audio/ e scrivi qui il nome
    file: "assets/audio/musica.mp3",
    volume: 0.35
  },

  /* --- 8. IL COLLEGAMENTO AL FOGLIO GOOGLE ---------------------------- */
  // Qui va l'indirizzo che ottieni seguendo backend/ISTRUZIONI.md
  // Finché resta vuoto il sito funziona lo stesso, ma le risposte
  // restano salvate solo sul telefono di chi le scrive (modo prova).
  backend: {
    url: ""
  }
};
