/* =====================================================================
   MESSAGGI.JS — la pagina privata: qui la festeggiata legge le lettere
   Il codice non è scritto da nessuna parte nel sito: viaggia solo verso
   il foglio Google, che risponde soltanto se è quello giusto.
   ===================================================================== */
(function () {
  "use strict";

  var C = window.CONFIG || {};
  var $  = function (s, d) { return (d || document).querySelector(s); };

  var serratura   = $("#serratura");
  var scrigno     = $("#scrigno");
  var modulo      = $("#moduloCodice");
  var campoCodice = $("#codice");
  var avviso      = $("#avvisoCodice");
  var tasto       = $("#apri");

  /* Su una pagina dove la cassetta non c'è (l'invito degli ospiti)
     questo file non ha niente da fare: se ne va prima di toccare
     il titolo o qualunque altra cosa che non gli appartiene. */
  if (!serratura || !scrigno || !modulo) return;

  var nome = (C.festeggiata && C.festeggiata.nome) || "";
  var eta = (C.festeggiata && C.festeggiata.eta) || 18;
  document.title = "Conferme per il tuo " + eta + "esimo";
  if (nome) $("#titoloSerratura").textContent = "Le lettere di " + nome;
  if (!Ponte.collegato()) {
    campoCodice.value = "PROVA";
    avviso.textContent = "Modo prova: il codice è PROVA e vedrai solo i messaggi scritti su questo telefono.";
    avviso.hidden = false;
  }

  function errore(testo) {
    avviso.textContent = testo;
    avviso.hidden = false;
    tasto.disabled = false;
    tasto.textContent = "Apri le lettere";
  }

  modulo.addEventListener("submit", function (ev) {
    ev.preventDefault();
    var codice = campoCodice.value.trim();
    if (!codice) { errore("Scrivi il tuo codice."); return; }
    avviso.hidden = true;
    tasto.disabled = true;
    tasto.textContent = "Apro";
    apri(codice);
  });

  var codiceUsato = "";

  function apri(codice) {
    Ponte.leggi(codice).then(function (risposta) {
      codiceUsato = codice;
      /* localStorage e non sessionStorage: così il codice resta anche
         quando chiude l'app, e non deve riscriverlo ogni volta */
      try { localStorage.setItem("invito.codice", codice); } catch (e) { /* niente */ }
      mostra(risposta);
    }).catch(function (err) {
      errore(err.message === "Failed to fetch"
        ? "Non riesco a collegarmi. Controlla la connessione."
        : "Codice sbagliato. Riprova.");
      campoCodice.select();
    });
  }

  function mostra(risposta) {
    serratura.hidden = true;
    scrigno.hidden = false;

    var messaggi = risposta.messaggi || [];
    var quanti = risposta.quanti !== undefined ? risposta.quanti : messaggi.length;

    $("#quanti").textContent = quanti === 0 ? "Nessuna ancora"
      : quanti === 1 ? "Una lettera" : quanti + " lettere";

    if (risposta.aperto === false) {
      /* le lettere restano chiuse fino alla data decisa */
      $("#ancoraChiusi").hidden = false;
      $("#testoChiusura").textContent = risposta.apreIl
        ? "Si apriranno il " + risposta.apreIl + ". Manca poco."
        : "Si apriranno la sera della festa.";
      disegnaSigilli(Math.min(quanti, 24));
    } else {
      $("#sezioneMessaggi").hidden = false;
      var pila = $("#pilaMessaggi");
      pila.innerHTML = "";
      if (!messaggi.length) {
        var vuoto = document.createElement("p");
        vuoto.className = "testo-tenue";
        vuoto.textContent = "Ancora nessun messaggio. Torna a controllare fra qualche giorno.";
        pila.appendChild(vuoto);
      }
      messaggi.forEach(function (m, i) {
        var carta = document.createElement("article");
        carta.className = "messaggio";
        carta.style.animationDelay = (i * 0.06) + "s";
        var numero = document.createElement("span");
        numero.className = "messaggio-numero";
        numero.textContent = i + 1;
        var testo = document.createElement("p");
        testo.style.margin = "0";
        testo.textContent = m.testo || "";      // textContent: niente HTML da fuori
        carta.appendChild(numero);
        carta.appendChild(testo);
        pila.appendChild(carta);
      });
    }

    var conferme = risposta.conferme || [];
    if (conferme.length) {
      $("#sezioneConferme").hidden = false;
      disegnaConferme(conferme);
    }
  }

  /* --- La lista di chi viene, con il cestino su ogni riga -------------
     Cancellare è definitivo: prima si chiede, e la riga sparisce solo
     dopo che il foglio ha davvero detto di sì.                        */
  function disegnaConferme(conferme) {
    var corpo = $("#corpoConferme");
    corpo.innerHTML = "";

    conferme.forEach(function (c) {
      var viene = String(c.presenza || "").toLowerCase().indexOf("s") === 0;
      var riga = document.createElement("tr");
      riga.dataset.id = c.id || "";

      /* L'etichetta serve al telefono: lì la tabella diventa una scheda
         e ogni dato deve dire da solo che cosa rappresenta. */
      function cella(testo, etichetta, classe) {
        var td = document.createElement("td");
        td.textContent = testo || "";
        td.dataset.eti = etichetta || "";
        if (classe) td.className = classe;
        if (!td.textContent) td.classList.add("vuota");
        riga.appendChild(td);
        return td;
      }

      cella(c.nome, "Nome", "c-nome");

      var stato = document.createElement("td");
      stato.className = "c-stato";
      var pastiglia = document.createElement("span");
      pastiglia.className = "pastiglia " + (viene ? "si" : "no");
      pastiglia.textContent = viene ? "Sì" : "No";
      stato.appendChild(pastiglia);
      riga.appendChild(stato);

      var ospiti = Number(c.accompagnatori || 0);
      cella(viene && ospiti ? "+" + ospiti : "", "Con lui/lei", "c-ospiti");
      cella(c.allergie, "Allergie", "c-allergie");
      cella(c.note, "Note", "c-note");

      var azioni = document.createElement("td");
      azioni.className = "c-azioni";
      var cestino = document.createElement("button");
      cestino.type = "button";
      cestino.className = "cestino";
      cestino.title = "Togli " + (c.nome || "questo invitato") + " dalla lista";
      cestino.setAttribute("aria-label", cestino.title);
      cestino.innerHTML = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" ' +
        'stroke="currentColor" stroke-width="1.4"><path d="M4 7h16M9 7V5h6v2M6 7l1 13h10l1-13"/></svg>';
      cestino.addEventListener("click", function () { togli(c, riga, cestino); });
      azioni.appendChild(cestino);
      riga.appendChild(azioni);

      corpo.appendChild(riga);
    });

    riassumi();
  }

  function riassumi() {
    var presenti = 0, ospiti = 0;
    Array.prototype.forEach.call($("#corpoConferme").children, function (riga) {
      var viene = riga.children[1].textContent.trim().toLowerCase().indexOf("s") === 0;
      if (!viene) return;
      presenti++;
      ospiti += Number(riga.children[2].textContent.replace("+", "")) || 0;
    });
    $("#riassuntoConferme").textContent = presenti === 0
      ? "Ancora nessuno ha detto sì."
      : presenti + (presenti === 1 ? " persona ha detto sì" : " persone hanno detto sì") +
        (ospiti ? ", più " + ospiti + (ospiti === 1 ? " accompagnatore" : " accompagnatori") : "") +
        " — " + (presenti + ospiti) + " a tavola.";
  }

  function togli(c, riga, cestino) {
    if (!window.confirm("Vuoi togliere " + (c.nome || "questo invitato") + " dalla lista?\n\nNon si torna indietro.")) return;
    cestino.disabled = true;
    cestino.classList.add("in-corso");

    Ponte.elimina(codiceUsato, c.id).then(function () {
      riga.classList.add("va-via");
      setTimeout(function () { riga.remove(); riassumi(); }, 320);
    }).catch(function (err) {
      cestino.disabled = false;
      cestino.classList.remove("in-corso");
      window.alert("Non sono riuscita a cancellarlo: " + err.message);
    });
  }

  /* le buste ancora sigillate, disegnate una per messaggio */
  function disegnaSigilli(quanti) {
    var griglia = $("#sigilli");
    griglia.innerHTML = "";
    var iniziali = (C.festeggiata && C.festeggiata.iniziali) || "";
    for (var i = 0; i < quanti; i++) {
      var s = document.createElement("span");
      s.className = "sigillo-piccolo";
      s.textContent = iniziali;
      s.style.animationDelay = (i * 0.12) + "s";
      griglia.appendChild(s);
    }
  }

  $("#chiudi").addEventListener("click", function () {
    try { localStorage.removeItem("invito.codice"); } catch (e) { /* niente */ }
    location.reload();
  });

  /* se il codice è già stato messo poco fa, riapro da sola */
  var salvato = null;
  try { salvato = localStorage.getItem("invito.codice"); } catch (e) { /* niente */ }
  if (salvato) {
    campoCodice.value = salvato;
    tasto.disabled = true;
    tasto.textContent = "Apro";
    apri(salvato);
  }
})();
