/* =====================================================================
   DATI.JS — il ponte fra la pagina e il foglio Google
   Se in config.js non c'è ancora l'indirizzo del foglio, il sito passa
   da solo in "modo prova": le risposte restano sul telefono di chi scrive.
   ===================================================================== */
window.Ponte = (function () {
  "use strict";

  var CHIAVI = { messaggio: "invito.prova.messaggi", conferma: "invito.prova.conferme" };

  function indirizzo() {
    var c = window.CONFIG || {};
    return ((c.backend && c.backend.url) || "").trim();
  }

  function collegato() {
    return indirizzo() !== "";
  }

  function leggiLocale(tipo) {
    try { return JSON.parse(localStorage.getItem(CHIAVI[tipo]) || "[]"); }
    catch (e) { return []; }
  }

  function scriviLocale(tipo, elenco) {
    try { localStorage.setItem(CHIAVI[tipo], JSON.stringify(elenco)); } catch (e) { /* memoria piena */ }
  }

  /* Invia una risposta. tipo = "messaggio" oppure "conferma" */
  function invia(tipo, dati) {
    if (!collegato()) {
      // Modo prova: nessun server, salvo qui per far vedere come funziona.
      var elenco = leggiLocale(tipo);
      elenco.push({ quando: new Date().toISOString(), dati: dati });
      scriviLocale(tipo, elenco);
      return new Promise(function (ok) { setTimeout(function () { ok({ esito: "prova" }); }, 900); });
    }

    // "text/plain" evita la richiesta di controllo CORS: Apps Script la rifiuterebbe.
    return fetch(indirizzo(), {
      method: "POST",
      headers: { "Content-Type": "text/plain;charset=utf-8" },
      body: JSON.stringify({ azione: "salva", tipo: tipo, dati: dati }),
      redirect: "follow"
    }).then(function (r) {
      return r.json();
    }).then(function (risposta) {
      if (!risposta || risposta.esito !== "ok") {
        throw new Error((risposta && risposta.motivo) || "risposta non valida");
      }
      return risposta;
    });
  }

  /* Legge messaggi e conferme: serve il codice segreto della festeggiata */
  function leggi(codice) {
    if (!collegato()) {
      return new Promise(function (ok, no) {
        setTimeout(function () {
          if (String(codice).trim().toUpperCase() !== "PROVA") {
            no(new Error("In modo prova il codice è PROVA"));
            return;
          }
          ok({
            esito: "ok",
            prova: true,
            aperto: true,
            messaggi: leggiLocale("messaggio").map(function (v) {
              return { quando: v.quando, testo: v.dati.testo };
            }),
            conferme: leggiLocale("conferma").map(function (v) { return v.dati; })
          });
        }, 700);
      });
    }

    var url = indirizzo() + "?azione=leggi&codice=" + encodeURIComponent(codice);
    return fetch(url, { redirect: "follow" }).then(function (r) {
      return r.json();
    }).then(function (risposta) {
      if (!risposta || risposta.esito !== "ok") {
        throw new Error((risposta && risposta.motivo) || "Codice non valido");
      }
      return risposta;
    });
  }

  return { collegato: collegato, invia: invia, leggi: leggi };
})();
