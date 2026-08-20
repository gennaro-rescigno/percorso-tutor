/* =====================================================================
   INVITO.JS — riempie l'invito con i dati di config.js e lo fa vivere
   ===================================================================== */
(function () {
  "use strict";

  var C = window.CONFIG || {};
  var fermoImmagine = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var tema = C.tema || "cipria";

  /* La frase sulla busta, quando in config.js è lasciata vuota */
  var FRASI_BUSTA = {
    cipria:    "Tocca la busta per aprire l'invito",
    discoteca: "Tocca la busta per aprire l'invito",
    neve:      "Tocca la busta per aprire l'invito",
    spazio:    "Sali a bordo",
    casino:    "Tira la leva",
    calcio:    "Scegli dove tirare"
  };

  /* Quanto aspettare prima di mostrare l'invito: lo decide il tema, in CSS */
  function attesaApertura() {
    var v = parseFloat(getComputedStyle(document.documentElement)
      .getPropertyValue("--attesa-apertura"));
    return isNaN(v) ? 1500 : v;
  }
  var $  = function (s, d) { return (d || document).querySelector(s); };
  var $$ = function (s, d) { return Array.prototype.slice.call((d || document).querySelectorAll(s)); };

  /* --- La brutta copia --------------------------------------------------
     Quello che uno sta scrivendo resta sul suo telefono anche se chiude
     l'app a metà. Si cancella appena il messaggio parte: dopo non deve
     restare traccia di niente da nessuna parte.                          */
  var BRUTTA = "invito.brutta.";
  function ricorda(chiave, testo) {
    try { localStorage.setItem(BRUTTA + chiave, testo); } catch (e) { /* memoria piena */ }
  }
  function ricordato(chiave) {
    try { return localStorage.getItem(BRUTTA + chiave) || ""; } catch (e) { return ""; }
  }
  function dimentica(chiave) {
    try { localStorage.removeItem(BRUTTA + chiave); } catch (e) { /* niente */ }
  }

  /* --- Legge un valore annidato: valore("evento.dataTesto") ------------ */
  function valore(percorso) {
    return percorso.split(".").reduce(function (o, k) {
      return (o && o[k] !== undefined && o[k] !== null) ? o[k] : "";
    }, C);
  }

  /* --- 1. Riempie tutti i testi segnati con data-c --------------------- */
  function applicaTesti() {
    $$("[data-c]").forEach(function (el) { el.textContent = valore(el.dataset.c); });

    /* se la frase sulla busta è vuota, si usa quella che sta bene al tema */
    var frase = $(".busta-istruzione");
    if (frase && !String(valore("testi.istruzioneBusta")).trim()) {
      frase.textContent = FRASI_BUSTA[tema] || FRASI_BUSTA.cipria;
    }
    $$("[data-c-href]").forEach(function (el) { el.href = valore(el.dataset.cHref); });
    $$("[data-c-segnaposto]").forEach(function (el) { el.placeholder = valore(el.dataset.cSegnaposto); });

    document.title = "Invito " + valore("festeggiata.eta") + "esimo " + valore("festeggiata.nome");
    var descr = $('meta[name="description"]');
    if (descr) {
      descr.content = "Invito per i " + valore("festeggiata.eta") + " anni di " +
        valore("festeggiata.nome") + " — " + valore("evento.dataTesto") + ", ore " + valore("evento.oraTesto");
    }

    /* sezioni che si possono spegnere da config.js */
    /* il gruppo WhatsApp: se in config.js non c'è il link, sparisce tutto */
    var linkGruppo = $("#linkGruppo");
    if (linkGruppo) {
      var indirizzoGruppo = String(valore("whatsapp.link")).trim();
      if (!valore("whatsapp.attivo") || !indirizzoGruppo) nascondi("gruppo");
      else linkGruppo.href = indirizzoGruppo;
    }

    if (!valore("rsvp.attivo")) nascondi("conferma");
    if (!valore("messaggi.attivo")) nascondi("messaggio");
    if (!valore("rsvp.chiediAccompagnatori")) rimuovi("#campoAccompagnatori");
    if (!valore("rsvp.chiediAllergie")) rimuovi("#campoAllergie");
  }

  function nascondi(id) {
    var s = document.getElementById(id);
    if (s) s.remove();
    var b = $('.bollo[href="#' + id + '"]');
    if (b) b.remove();
  }
  function rimuovi(sel) { var e = $(sel); if (e) e.remove(); }

  /* --- 2. Il programma della serata ------------------------------------ */
  function costruisciProgramma() {
    var contenitore = $("#programmaElenco");
    if (!contenitore) return;
    var righe = valore("programma") || [];
    if (!righe.length) { nascondi("programma"); return; }

    contenitore.innerHTML = "";
    righe.forEach(function (r) {
      var voce = document.createElement("li");
      voce.className = "programma-voce";
      voce.innerHTML =
        '<span class="programma-ora"></span>' +
        '<span class="programma-filo" aria-hidden="true"></span>' +
        '<span><span class="programma-cosa"></span><br><span class="programma-dettaglio"></span></span>';
      $(".programma-ora", voce).textContent = r.ora || "";
      $(".programma-cosa", voce).textContent = r.cosa || "";
      $(".programma-dettaglio", voce).textContent = r.dettaglio || "";
      contenitore.appendChild(voce);
    });
  }

  /* --- 3. Conto alla rovescia ------------------------------------------ */
  function contoAllaRovescia() {
    var scatola = $("#conto");
    if (!scatola) return;
    var meta = new Date(valore("evento.quando")).getTime();
    if (isNaN(meta)) { scatola.remove(); return; }

    var campi = {
      giorni: $("#contoGiorni"), ore: $("#contoOre"),
      minuti: $("#contoMinuti"), secondi: $("#contoSecondi")
    };

    function passo() {
      var resta = meta - Date.now();
      if (resta <= 0) {
        scatola.innerHTML = '<p class="titolo-sezione">È arrivato il giorno</p>';
        if (orologio) clearInterval(orologio);
        return;
      }
      var s = Math.floor(resta / 1000);
      campi.giorni.textContent  = Math.floor(s / 86400);
      campi.ore.textContent     = String(Math.floor(s / 3600) % 24).padStart(2, "0");
      campi.minuti.textContent  = String(Math.floor(s / 60) % 60).padStart(2, "0");
      campi.secondi.textContent = String(s % 60).padStart(2, "0");
    }
    passo();
    var orologio = setInterval(passo, 1000);
  }

  /* --- 4. Apparizione allo scorrimento --------------------------------- */
  function rivelaScorrendo() {
    var pezzi = $$(".rivela");
    if (!("IntersectionObserver" in window) || fermoImmagine) {
      pezzi.forEach(function (p) { p.classList.add("visibile"); });
      return;
    }
    var occhio = new IntersectionObserver(function (voci) {
      voci.forEach(function (v) {
        if (v.isIntersecting) { v.target.classList.add("visibile"); occhio.unobserve(v.target); }
      });
    }, { threshold: 0.12, rootMargin: "0px 0px -8% 0px" });
    pezzi.forEach(function (p) { occhio.observe(p); });
  }

  /* --- 5. La musica ----------------------------------------------------- */
  var suono = null;
  function preparaMusica() {
    var tasto = $("#musica");
    if (!tasto) return;
    if (!valore("musica.attiva")) { tasto.remove(); return; }

    suono = new Audio(valore("musica.file"));
    suono.loop = true;
    suono.volume = Number(valore("musica.volume")) || 0.35;

    /* se il file non c'è, il tasto sparisce senza far danni */
    suono.addEventListener("error", function () { tasto.remove(); suono = null; });

    tasto.addEventListener("click", function () {
      if (!suono) return;
      if (suono.paused) { suono.play().catch(function () {}); tasto.classList.remove("in-pausa"); }
      else { suono.pause(); tasto.classList.add("in-pausa"); }
      tasto.setAttribute("aria-pressed", String(!suono.paused));
    });
  }

  function avviaMusica() {
    var tasto = $("#musica");
    if (!suono || !tasto) return;
    suono.play().then(function () {
      tasto.classList.add("mostrata");
      tasto.setAttribute("aria-pressed", "true");
    }).catch(function () {
      tasto.classList.add("mostrata", "in-pausa");   // il telefono ha detto no: resta il tasto
      tasto.setAttribute("aria-pressed", "false");
    });
  }

  /* --- 6. L'apertura della busta ---------------------------------------- */
  function preparaBusta() {
    var scena = $("#scenaBusta");
    var busta = $("#busta");
    var invito = $("#invito");
    if (!scena || !busta || !invito) return;

    document.body.classList.add("sigillato");

    var giaAperta = false;

    function apriInvito() {
      if (giaAperta) return;
      giaAperta = true;

      scena.classList.add("aperta");
      avviaMusica();

      setTimeout(function () {
        scena.classList.add("andata");
        document.body.classList.remove("sigillato");
        invito.classList.add("mostrato");
        invito.removeAttribute("aria-hidden");
        rivelaScorrendo();
        window.scrollTo(0, 0);
      }, fermoImmagine ? 100 : attesaApertura());
    }

    /* Un tema può mettere una prova davanti all'invito — nel tema calcio
       bisogna segnare un rigore. In quel caso decide lei quando si apre. */
    if (window.SFIDA && window.SFIDA.attiva(tema)) {
      window.SFIDA.prepara(scena, busta, apriInvito, fermoImmagine);
      return;
    }

    busta.addEventListener("click", apriInvito);
  }

  /* --- 7. Il messaggio anonimo ------------------------------------------ */
  function preparaMessaggio() {
    var lettera = $("#letteraMessaggio");     // il foglio è anche il modulo
    if (!lettera) return;

    var foglio = $("#testoMessaggio");
    var contatore = $("#contatoreMessaggio");
    var avviso = $("#avvisoMessaggio");
    var tasto = $("#inviaMessaggio");
    var esito = $("#esitoMessaggio");
    var massimo = Number(valore("messaggi.massimoCaratteri")) || 900;

    foglio.maxLength = massimo;
    function aggiornaContatore() {
      var usati = foglio.value.length;
      contatore.textContent = usati + " / " + massimo;
      contatore.classList.toggle("pieno", usati >= massimo);
    }
    foglio.value = ricordato("messaggio");
    foglio.addEventListener("input", function () {
      aggiornaContatore();
      ricorda("messaggio", foglio.value);
    });
    aggiornaContatore();

    lettera.addEventListener("submit", function (ev) {
      ev.preventDefault();
      avviso.hidden = true;

      var testo = foglio.value.trim();
      if (testo.length < 2) {
        avviso.textContent = "Scrivi qualcosa prima di inviare.";
        avviso.hidden = false;
        foglio.focus();
        return;
      }

      tasto.disabled = true;
      tasto.textContent = "Sto inviando";
      if (!fermoImmagine) lettera.classList.add("parte");

      var partenza = Date.now();
      /* mando solo il testo: nessun nome, nessuna mail, nessun indirizzo */
      Ponte.invia("messaggio", { testo: testo })
        .then(function () {
          dimentica("messaggio");        /* è partito: niente più copie in giro */
          var attesa = Math.max(0, (fermoImmagine ? 0 : 1500) - (Date.now() - partenza));
          setTimeout(function () {
            lettera.hidden = true;
            esito.classList.add("visibile");
          }, attesa);
        })
        .catch(function (err) {
          lettera.classList.remove("parte");
          tasto.disabled = false;
          tasto.textContent = "Invia il messaggio";
          avviso.textContent = "Il messaggio non è partito: " + err.message +
            ". Controlla la connessione e riprova.";
          avviso.hidden = false;
        });
    });
  }

  /* --- 8. La conferma di presenza --------------------------------------- */
  function preparaConferma() {
    var modulo = $("#moduloConferma");
    if (!modulo) return;

    var avviso = $("#avvisoConferma");
    var tasto = $("#inviaConferma");
    var esito = $("#esitoConferma");
    var seViene = $("#seViene");

    /* le domande in più compaiono solo a chi risponde "sì" */
    function aggiornaVisibilita() {
      var scelto = modulo.querySelector('input[name="presenza"]:checked');
      var viene = scelto && scelto.value === "si";
      if (seViene) seViene.hidden = !viene;
    }
    /* ogni campo si ricorda da solo quello che ci hai messo */
    var CAMPI = ["nome", "accompagnatori", "allergie", "note"];
    CAMPI.forEach(function (c) {
      var campo = modulo.querySelector('[name="' + c + '"]');
      if (!campo) return;
      var salvato = ricordato("conferma." + c);
      if (salvato) campo.value = salvato;
      campo.addEventListener("input", function () { ricorda("conferma." + c, campo.value); });
    });

    var presenzaSalvata = ricordato("conferma.presenza");
    $$('input[name="presenza"]', modulo).forEach(function (r) {
      if (presenzaSalvata && r.value === presenzaSalvata) r.checked = true;
      r.addEventListener("change", function () {
        ricorda("conferma.presenza", r.value);
        aggiornaVisibilita();
      });
    });
    aggiornaVisibilita();

    function erroreConferma(testo) {
      avviso.textContent = testo;
      avviso.hidden = false;
      avviso.scrollIntoView({ block: "center", behavior: "smooth" });
    }

    var doppione = $("#doppioneConferma");
    var doppioneTesto = $("#doppioneTesto");
    var tastoCambio = $("#cambioNome");
    var tastoAltro = $("#sonoAltro");

    function raccogli() {
      var dati = new FormData(modulo);
      var scelto = modulo.querySelector('input[name="presenza"]:checked');
      var viene = scelto && scelto.value === "si";
      return {
        nome: String(dati.get("nome") || "").trim(),
        presenza: viene ? "Sì" : "No",
        accompagnatori: viene ? String(dati.get("accompagnatori") || "0") : "0",
        allergie: viene ? String(dati.get("allergie") || "").trim() : "",
        note: String(dati.get("note") || "").trim()
      };
    }

    function mandaConferma(forza) {
      var d = raccogli();
      d.forza = forza ? 1 : 0;

      tasto.disabled = true;
      tasto.textContent = "Sto inviando";
      if (doppione) doppione.hidden = true;

      Ponte.invia("conferma", d).then(function (r) {
        /* Il nome c'è già: non è un errore, è una domanda. Decide chi
           sta scrivendo se cambiare nome o dire "sono un altro". */
        if (r && r.esito === "doppione") {
          tasto.disabled = false;
          tasto.textContent = "Invia la conferma";
          var altro = (r.simili && r.simili[0] && r.simili[0].nome) || d.nome;
          if (doppioneTesto) {
            doppioneTesto.textContent = "In lista c'è già " + altro + ". Se sei tu, sei a posto: " +
              "non serve confermare due volte. Se invece sei un'altra persona con lo stesso nome, " +
              "aggiungi qualcosa per farvi distinguere — il cognome per esteso, il paese, il soprannome.";
          }
          if (doppione) doppione.hidden = false;
          if (doppione && doppione.scrollIntoView) doppione.scrollIntoView({ block: "center", behavior: "smooth" });
          return;
        }

        CAMPI.forEach(function (c) { dimentica("conferma." + c); });
        dimentica("conferma.presenza");
        modulo.hidden = true;
        esito.classList.add("visibile");
        $("#esitoConfermaTesto").textContent = d.presenza === "Sì"
          ? "Ci vediamo il " + valore("evento.dataTesto") + "."
          : "Ci dispiace non vederti. Grazie per avercelo detto.";
      }).catch(function (err) {
        tasto.disabled = false;
        tasto.textContent = "Invia la conferma";
        erroreConferma("La conferma non è partita: " + err.message + ". Riprova fra poco.");
      });
    }

    if (tastoCambio) tastoCambio.addEventListener("click", function () {
      doppione.hidden = true;
      var campoNome = $("#nomeConferma");
      if (campoNome) { campoNome.focus(); campoNome.select(); }
    });
    if (tastoAltro) tastoAltro.addEventListener("click", function () { mandaConferma(true); });

    modulo.addEventListener("submit", function (ev) {
      ev.preventDefault();
      avviso.hidden = true;
      if (doppione) doppione.hidden = true;

      var d = raccogli();
      if (!d.nome) { erroreConferma("Scrivi il tuo nome e cognome."); return; }
      if (!modulo.querySelector('input[name="presenza"]:checked')) { erroreConferma("Dicci se ci sarai."); return; }
      mandaConferma(false);
    });
  }

  /* --- 9. Avviso "modo prova" -------------------------------------------- */
  function avvisoModoProva() {
    /* La nota serve solo finché non c'è il foglio Google collegato. */
    if (Ponte.collegato()) {
      $$(".nota-prova").forEach(function (n) { n.remove(); });
    }
  }

  /* --- Partenza ---------------------------------------------------------- */
  applicaTesti();
  costruisciProgramma();
  contoAllaRovescia();
  preparaMusica();
  preparaMessaggio();
  preparaConferma();
  avvisoModoProva();
  preparaBusta();
})();
