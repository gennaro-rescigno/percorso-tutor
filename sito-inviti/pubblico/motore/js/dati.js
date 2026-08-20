/* =====================================================================
   DATI.JS — il ponte fra la pagina e il foglio Google.
   Ogni invito manda sempre il suo identificativo, così lo script sa a
   quale festa appartengono i dati e non li mischia mai con un'altra.
   Se in config.js manca l'indirizzo, il sito passa da solo in "modo
   prova": tutto resta sul telefono di chi scrive.
   ===================================================================== */
window.Ponte = (function () {
  "use strict";

  var CHIAVI = { messaggio: "invito.prova.messaggi", conferma: "invito.prova.conferme" };

  function C() { return window.CONFIG || {}; }
  function invito() { return ((C().invito && C().invito.id) || "prova").trim(); }
  function indirizzo() { return (((C().backend || {}).url) || "").trim(); }
  function collegato() { return indirizzo() !== ""; }

  /* --- Modo prova: niente server, tutto qui sul telefono ------------- */
  function leggiLocale(tipo) {
    try { return JSON.parse(localStorage.getItem(CHIAVI[tipo] + "." + invito()) || "[]"); }
    catch (e) { return []; }
  }
  function scriviLocale(tipo, elenco) {
    try { localStorage.setItem(CHIAVI[tipo] + "." + invito(), JSON.stringify(elenco)); }
    catch (e) { /* memoria piena */ }
  }
  function idFinto() { return Math.random().toString(36).slice(2, 14); }

  /* --- Le chiamate vere --------------------------------------------- */
  function parla(corpo) {
    /* "text/plain" evita la richiesta di controllo CORS, che Apps Script
       rifiuterebbe. Il contenuto resta comunque JSON. */
    return fetch(indirizzo(), {
      method: "POST",
      headers: { "Content-Type": "text/plain;charset=utf-8" },
      body: JSON.stringify(corpo),
      redirect: "follow"
    }).then(function (r) { return r.json(); });
  }

  function ascolta(parametri) {
    var q = Object.keys(parametri).map(function (k) {
      return k + "=" + encodeURIComponent(parametri[k]);
    }).join("&");
    return fetch(indirizzo() + "?" + q, { redirect: "follow" }).then(function (r) { return r.json(); });
  }

  /* --- "questo nome è già in lista?" --------------------------------- */
  function normalizza(nome) {
    return String(nome || "").toLowerCase()
      .normalize("NFD").replace(/[̀-ͯ]/g, "")
      .replace(/[^a-z0-9 ]/g, " ").replace(/\s+/g, " ").trim();
  }

  function controlla(nome) {
    if (!collegato()) {
      var cerca = normalizza(nome);
      var simili = leggiLocale("conferma")
        .filter(function (v) { return normalizza(v.dati.nome) === cerca; })
        .map(function (v) { return { nome: v.dati.nome, quando: v.quando }; });
      return Promise.resolve({ esito: "ok", simili: simili });
    }
    return parla({ azione: "controlla", invito: invito(), nome: nome });
  }

  /* --- Invia un messaggio o una conferma ------------------------------
     Se torna esito "doppione" NON è un errore: vuol dire che quel nome
     c'è già, e la pagina deve chiedere conferma prima di insistere.    */
  function invia(tipo, dati) {
    if (!collegato()) {
      if (tipo === "conferma" && !dati.forza) {
        var cerca = normalizza(dati.nome);
        var simili = leggiLocale("conferma")
          .filter(function (v) { return normalizza(v.dati.nome) === cerca; })
          .map(function (v) { return { nome: v.dati.nome, quando: v.quando }; });
        if (simili.length) return Promise.resolve({ esito: "doppione", simili: simili });
      }
      var elenco = leggiLocale(tipo);
      elenco.push({ id: idFinto(), quando: new Date().toISOString().slice(0, 10), dati: dati });
      scriviLocale(tipo, elenco);
      return new Promise(function (ok) { setTimeout(function () { ok({ esito: "prova" }); }, 700); });
    }

    return parla({ azione: "salva", tipo: tipo, invito: invito(), dati: dati })
      .then(function (r) {
        if (!r) throw new Error("risposta vuota");
        if (r.esito === "ok" || r.esito === "doppione") return r;
        throw new Error(r.motivo || "risposta non valida");
      });
  }

  /* --- La festeggiata legge ------------------------------------------ */
  function leggi(codice) {
    if (!collegato()) {
      return new Promise(function (ok, no) {
        setTimeout(function () {
          if (String(codice).trim().toUpperCase() !== "PROVA") {
            no(new Error("In modo prova il codice è PROVA"));
            return;
          }
          ok({
            esito: "ok", prova: true, aperto: true,
            messaggi: leggiLocale("messaggio").map(function (v) {
              return { quando: v.quando, testo: v.dati.testo };
            }),
            conferme: leggiLocale("conferma").map(function (v) {
              var c = {}; Object.keys(v.dati).forEach(function (k) { c[k] = v.dati[k]; });
              c.id = v.id; c.quando = v.quando; return c;
            })
          });
        }, 600);
      });
    }

    return ascolta({ azione: "leggi", invito: invito(), codice: codice })
      .then(function (r) {
        if (!r || r.esito !== "ok") throw new Error((r && r.motivo) || "Codice non valido");
        return r;
      });
  }

  /* --- La festeggiata cancella un invitato ---------------------------- */
  function elimina(codice, id) {
    if (!collegato()) {
      var elenco = leggiLocale("conferma").filter(function (v) { return v.id !== id; });
      scriviLocale("conferma", elenco);
      return new Promise(function (ok) { setTimeout(function () { ok({ esito: "ok" }); }, 350); });
    }
    return parla({ azione: "elimina", invito: invito(), codice: codice, id: id })
      .then(function (r) {
        if (!r || r.esito !== "ok") throw new Error((r && r.motivo) || "non riesco a cancellare");
        return r;
      });
  }

  return {
    collegato: collegato, invito: invito,
    invia: invia, controlla: controlla, leggi: leggi, elimina: elimina
  };
})();
