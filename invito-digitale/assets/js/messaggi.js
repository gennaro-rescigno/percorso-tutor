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

  var nome = (C.festeggiata && C.festeggiata.nome) || "";
  if (nome) {
    $("#titoloSerratura").textContent = "Le lettere di " + nome;
    document.title = "Le lettere di " + nome;
  }
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

  function apri(codice) {
    Ponte.leggi(codice).then(function (risposta) {
      try { sessionStorage.setItem("invito.codice", codice); } catch (e) { /* niente */ }
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
      var presenti = 0, ospiti = 0;
      var corpo = $("#corpoConferme");
      corpo.innerHTML = "";
      conferme.forEach(function (c) {
        var viene = String(c.presenza || "").toLowerCase().indexOf("s") === 0;
        if (viene) { presenti++; ospiti += Number(c.accompagnatori || 0) || 0; }
        var riga = document.createElement("tr");
        [
          c.nome || "",
          null,
          viene ? String(c.accompagnatori || 0) : "",
          c.allergie || "",
          c.note || ""
        ].forEach(function (v, i) {
          var cella = document.createElement("td");
          if (i === 1) {
            var p = document.createElement("span");
            p.className = "pastiglia " + (viene ? "si" : "no");
            p.textContent = viene ? "Sì" : "No";
            cella.appendChild(p);
          } else {
            cella.textContent = v;
          }
          riga.appendChild(cella);
        });
        corpo.appendChild(riga);
      });
      $("#riassuntoConferme").textContent =
        presenti + (presenti === 1 ? " persona ha detto sì" : " persone hanno detto sì") +
        (ospiti ? ", più " + ospiti + " accompagnatori" : "") +
        " — " + (presenti + ospiti) + " a tavola.";
    }
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
    try { sessionStorage.removeItem("invito.codice"); } catch (e) { /* niente */ }
    location.reload();
  });

  /* se il codice è già stato messo poco fa, riapro da sola */
  var salvato = null;
  try { salvato = sessionStorage.getItem("invito.codice"); } catch (e) { /* niente */ }
  if (salvato) {
    campoCodice.value = salvato;
    tasto.disabled = true;
    tasto.textContent = "Apro";
    apri(salvato);
  }
})();
