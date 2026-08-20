/* =====================================================================
   CONFIG DI QUESTO INVITO — {{NOME}}
   Creato da strumenti/nuovo_invito.py. Puoi ritoccare i testi a mano:
   cambia solo quello che sta fra le virgolette.
   ===================================================================== */

window.CONFIG = {

  /* Il nome in codice di questa festa. NON cambiarlo: è quello che lo
     script Google usa per non mischiare questa festa con le altre. */
  invito: { id: "{{ID}}" },

  tema: "{{TEMA}}",

  festeggiata: {
    nome: "{{NOME}}",
    iniziali: "{{INIZIALI}}",
    eta: {{ETA}},
    articolo: "la",
    festeggiataDi: "festeggiata"
  },

  evento: {
    quando: "{{QUANDO}}",
    dataTesto: "{{DATA}}",
    oraTesto: "{{ORA}}",
    luogo: "{{LUOGO}}",
    indirizzo: "{{INDIRIZZO}}",
    mappa: "{{MAPPA}}",
    dressCode: "{{DRESSCODE}}",
    notaDressCode: ""
  },

  testi: {
    istruzioneBusta: "",
    soprannome: "Ti aspetto il",
    apertura: "{{ETA}} anni si compiono una volta sola.",
    invitoBreve: "Ho scelto le persone giuste per festeggiarli: ci sei anche tu.",
    firma: "Con affetto, {{NOME}}"
  },

  programma: [
    { ora: "{{ORA}}", cosa: "Arrivo degli ospiti", dettaglio: "Aperitivo di benvenuto" },
    { ora: "21:00", cosa: "Cena",               dettaglio: "Servita ai tavoli" },
    { ora: "23:00", cosa: "Taglio della torta", dettaglio: "Il momento del brindisi" },
    { ora: "23:30", cosa: "Si balla",           dettaglio: "Fino a quando reggiamo" }
  ],

  rsvp: {
    attivo: true,
    scadenzaTesto: "{{SCADENZA}}",
    chiediAccompagnatori: true,
    chiediAllergie: true
  },

  /* --- IL GRUPPO WHATSAPP ---------------------------------------------
     Apri il gruppo, Info gruppo, "Invita tramite link", copia e incolla
     qui. Se lasci vuoto, la sezione sparisce da sola dall'invito.      */
  whatsapp: {
    attivo: true,
    link: "{{WHATSAPP}}",
    titolo: "Il gruppo della festa",
    invito: "Qui ci mettiamo d'accordo su tutto: passaggi, regali, sorprese.",
    bottone: "Entra nel gruppo WhatsApp"
  },

  messaggi: {
    attivo: true,
    titolo: "Un messaggio per {{NOME}}",
    invito: "Scrivile qualcosa prima che diventi maggiorenne: un ricordo, un augurio, una cosa che non le hai mai detto.",
    promessa: "Nessuno saprà mai chi l'ha scritto. Nemmeno {{NOME}}.",
    massimoCaratteri: 900,
    ringraziamento: "Il tuo messaggio è partito.",
    ringraziamentoDettaglio: "Resterà chiuso nella busta fino alla sera della festa."
  },

  musica: { attiva: true, file: "../../motore/audio/musica.mp3", volume: 0.35 },

  backend: { url: "{{BACKEND}}" }
};
