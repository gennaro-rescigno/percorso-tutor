/* =====================================================================
   CONFIG DI QUESTO INVITO — Marta
   Creato da strumenti/nuovo_invito.py. Puoi ritoccare i testi a mano:
   cambia solo quello che sta fra le virgolette.
   ===================================================================== */

window.CONFIG = {

  /* Il nome in codice di questa festa. NON cambiarlo: è quello che lo
     script Google usa per non mischiare questa festa con le altre. */
  invito: { id: "marta-18-vm5cyy" },

  tema: "calcio",

  festeggiata: {
    nome: "Marta",
    iniziali: "M",
    eta: 18,
    articolo: "la",
    festeggiataDi: "festeggiata"
  },

  evento: {
    quando: "2027-08-04T20:00:00",
    dataTesto: "4 Agosto 2027",
    oraTesto: "20:00",
    luogo: "Villa Ferrara",
    indirizzo: "Via delle Rose 12, Salerno",
    mappa: "",
    dressCode: "Elegante",
    notaDressCode: ""
  },

  testi: {
    istruzioneBusta: "",
    soprannome: "Ti aspetto il",
    apertura: "18 anni si compiono una volta sola.",
    invitoBreve: "Ho scelto le persone giuste per festeggiarli: ci sei anche tu.",
    firma: "Con affetto, Marta"
  },

  programma: [
    { ora: "20:00", cosa: "Arrivo degli ospiti", dettaglio: "Aperitivo di benvenuto" },
    { ora: "21:00", cosa: "Cena",               dettaglio: "Servita ai tavoli" },
    { ora: "23:00", cosa: "Taglio della torta", dettaglio: "Il momento del brindisi" },
    { ora: "23:30", cosa: "Si balla",           dettaglio: "Fino a quando reggiamo" }
  ],

  rsvp: {
    attivo: true,
    scadenzaTesto: "1 agosto",
    chiediAccompagnatori: true,
    chiediAllergie: true
  },

  /* --- IL GRUPPO WHATSAPP ---------------------------------------------
     Apri il gruppo, Info gruppo, "Invita tramite link", copia e incolla
     qui. Se lasci vuoto, la sezione sparisce da sola dall'invito.      */
  whatsapp: {
    attivo: true,
    link: "https://chat.whatsapp.com/ESEMPIO",
    titolo: "Il gruppo della festa",
    invito: "Qui ci mettiamo d'accordo su tutto: passaggi, regali, sorprese.",
    bottone: "Entra nel gruppo WhatsApp"
  },

  messaggi: {
    attivo: true,
    titolo: "Un messaggio per Marta",
    invito: "Scrivile qualcosa prima che diventi maggiorenne: un ricordo, un augurio, una cosa che non le hai mai detto.",
    promessa: "Nessuno saprà mai chi l'ha scritto. Nemmeno Marta.",
    massimoCaratteri: 900,
    ringraziamento: "Il tuo messaggio è partito.",
    ringraziamentoDettaglio: "Resterà chiuso nella busta fino alla sera della festa."
  },

  musica: { attiva: true, file: "../../motore/audio/musica.mp3", volume: 0.35 },

  backend: { url: "" }
};
