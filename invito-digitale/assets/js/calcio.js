/* =====================================================================
   CALCIO.JS — il rigore da segnare prima di entrare.
   Vale solo con  tema: "calcio"  in config.js. Con gli altri temi questo
   file non fa niente: la busta si apre al tocco come sempre.

   Il campo non sta nell'HTML perché serve solo qui: se lo costruisce
   questo file, e le altre pagine restano pulite.
   ===================================================================== */
window.SFIDA = (function () {
  "use strict";

  /* Le cinque mire, in percentuale dentro allo specchio della porta.
     L'ordine conta: è lo stesso che usa il portiere per tuffarsi. */
  var ZONE = [
    { x: 15, y: 26, nome: "Sette alla tua sinistra" },
    { x: 15, y: 76, nome: "Rasoterra a sinistra" },
    { x: 50, y: 50, nome: "In mezzo" },
    { x: 85, y: 26, nome: "Sette alla tua destra" },
    { x: 85, y: 76, nome: "Rasoterra a destra" }
  ];

  var SFOTTO = [
    "Non sei degno di aprire l'invito",
    "Parata. Non sei degno di aprire l'invito",
    "Ancora lui. Non sei degno di aprire l'invito"
  ];

  function attiva(tema) { return tema === "calcio"; }

  function el(tag, classe, dentro) {
    var e = document.createElement(tag);
    if (classe) e.className = classe;
    if (dentro) dentro.appendChild(e);
    return e;
  }

  function prepara(scena, busta, vinto, fermoImmagine) {
    var C = window.CONFIG || {};
    var nome = ((C.festeggiata && C.festeggiata.nome) || "10").toUpperCase();
    var numero = (C.festeggiata && C.festeggiata.eta) || 10;

    /* la busta non serve: al suo posto va il campo */
    busta.setAttribute("hidden", "");

    var campo = el("div", "campo-rigore");
    campo.id = "campoRigore";

    /* --- lo stadio ------------------------------------------------- */
    var stadio = el("div", "stadio", campo);
    el("div", "faro faro-sx", stadio);
    el("div", "faro faro-dx", stadio);
    el("div", "tribuna tribuna-alta", stadio);
    el("div", "tribuna tribuna-bassa", stadio);
    var flash = el("div", "flash-folla", stadio);
    for (var f = 0; f < 26; f++) {
      var lam = el("span", "", flash);
      lam.style.left = (Math.random() * 100).toFixed(1) + "%";
      lam.style.top = (Math.random() * 100).toFixed(1) + "%";
      lam.style.animationDelay = (Math.random() * 6).toFixed(2) + "s";
    }

    /* --- il prato -------------------------------------------------- */
    var prato = el("div", "prato", campo);
    el("div", "righe-prato", prato);
    /* Ogni riga del campo è un quadrilatero sottile con il suo ritaglio:
       così vanno in prospettiva, più strette in fondo e larghe davanti. */
    ["l-porta", "l-area-sx", "l-area-dx", "l-area-fr",
     "l-piccola-sx", "l-piccola-dx", "l-piccola-fr"].forEach(function (n) {
      el("div", "linea " + n, prato);
    });
    el("div", "arco", prato);
    el("div", "dischetto", prato);

    /* --- la porta -------------------------------------------------- */
    var porta = el("div", "porta", campo);
    var rete = el("div", "rete", porta);
    el("div", "palo palo-sx", porta);
    el("div", "palo palo-dx", porta);
    el("div", "traversa", porta);

    var portiere = el("div", "portiere", porta);
    el("div", "p-testa", portiere);
    el("div", "p-maglia", portiere);
    el("div", "p-braccio p-sx", portiere);
    el("div", "p-braccio p-dx", portiere);
    el("div", "p-guanto p-sx", portiere);
    el("div", "p-guanto p-dx", portiere);
    el("div", "p-gamba p-sx", portiere);
    el("div", "p-gamba p-dx", portiere);

    var mire = [];
    ZONE.forEach(function (z, i) {
      var m = el("button", "mira", porta);
      m.type = "button";
      m.style.left = z.x + "%";
      m.style.top = z.y + "%";
      m.setAttribute("aria-label", "Tira: " + z.nome);
      el("span", "mira-anello", m);
      el("span", "mira-croce", m);
      m.dataset.zona = String(i);
      mire.push(m);
    });

    /* --- il giocatore, di spalle ----------------------------------- */
    var giocatore = el("div", "giocatore", campo);
    el("div", "g-ombra", giocatore);
    el("div", "g-gamba g-sx", giocatore);
    el("div", "g-gamba g-dx", giocatore);
    el("div", "g-calzoncini", giocatore);
    var maglia = el("div", "g-maglia", giocatore);
    var nomeMaglia = el("span", "g-nome", maglia);
    nomeMaglia.textContent = nome;
    var numMaglia = el("span", "g-numero", maglia);
    numMaglia.textContent = numero;
    el("div", "g-braccio g-sx", giocatore);
    el("div", "g-braccio g-dx", giocatore);
    el("div", "g-testa", giocatore);

    /* --- il pallone ------------------------------------------------ */
    var pallone = el("div", "pallone", campo);
    el("div", "p-ombra", pallone);
    el("div", "p-sfera", pallone);
    var scia = el("div", "scia", campo);

    /* --- tabellone ed esiti ---------------------------------------- */
    var tabellone = el("div", "tabellone", campo);
    tabellone.innerHTML = '<span class="t-etichetta">RIGORE</span><span class="t-numero">1</span>';
    var contatore = tabellone.querySelector(".t-numero");

    var esito = el("div", "esito-rigore", campo);
    var gol = el("div", "gol-scritta", campo);
    gol.textContent = "GOL!";

    /* i coriandoli sono già pronti: partono da soli quando si segna */
    var coriandoli = el("div", "coriandoli", campo);
    var TINTE = ["#FFC53D", "#F04E5E", "#3FBF6F", "#5AA9FF", "#FFFFFF", "#FF8A3D"];
    for (var c = 0; c < 70; c++) {
      var pezzo = el("span", "", coriandoli);
      pezzo.style.left = (Math.random() * 100).toFixed(1) + "%";
      pezzo.style.background = TINTE[Math.floor(Math.random() * TINTE.length)];
      pezzo.style.setProperty("--sposta", ((Math.random() - 0.5) * 60).toFixed(1) + "vw");
      pezzo.style.setProperty("--giro", (360 + Math.random() * 900).toFixed(0) + "deg");
      pezzo.style.animationDelay = (Math.random() * 0.5).toFixed(2) + "s";
      pezzo.style.animationDuration = (1.5 + Math.random() * 1.4).toFixed(2) + "s";
      if (Math.random() < 0.35) pezzo.style.borderRadius = "50%";
    }

    scena.insertBefore(campo, scena.firstChild);

    /* =================================================================
       IL GIOCO
       ================================================================= */
    var tiri = 0;
    var occupato = false;

    function abilita(si) {
      mire.forEach(function (m) { m.disabled = !si; });
      campo.classList.toggle("pronto", si);
    }

    function pulisci() {
      campo.classList.remove("tira", "scossa", "parata");
      pallone.className = "pallone";
      pallone.style.removeProperty("--bx");
      pallone.style.removeProperty("--by");
      giocatore.className = "giocatore";
      portiere.className = "portiere";
      rete.className = "rete";
      scia.className = "scia";
      esito.className = "esito-rigore";
      esito.textContent = "";
    }

    function tira(zona) {
      if (occupato) return;
      occupato = true;
      abilita(false);

      var parata = Math.floor(Math.random() * ZONE.length);

      /* dove deve arrivare il pallone, in pixel veri */
      var rp = pallone.getBoundingClientRect();
      var rm = mire[zona].getBoundingClientRect();
      var dx = (rm.left + rm.width / 2) - (rp.left + rp.width / 2);
      var dy = (rm.top + rm.height / 2) - (rp.top + rp.height / 2);
      pallone.style.setProperty("--bx", dx.toFixed(1) + "px");
      pallone.style.setProperty("--by", dy.toFixed(1) + "px");
      scia.style.setProperty("--bx", dx.toFixed(1) + "px");
      scia.style.setProperty("--by", dy.toFixed(1) + "px");

      /* dove gonfia la rete */
      rete.style.setProperty("--hx", ZONE[zona].x + "%");
      rete.style.setProperty("--hy", ZONE[zona].y + "%");

      giocatore.classList.add("calcia");
      var ritardo = fermoImmagine ? 0 : 170;

      setTimeout(function () {
        pallone.classList.add("vola");
        scia.classList.add("accesa");
        campo.classList.add("scossa");
        portiere.classList.add("tuffo", "tuffo-" + parata);
      }, ritardo);

      setTimeout(function () {
        if (parata === zona) sbagliato();
        else segnato();
      }, ritardo + (fermoImmagine ? 20 : 470));
    }

    function segnato() {
      rete.classList.add("gonfia");
      pallone.classList.add("dentro");
      campo.classList.add("gol");
      gol.classList.add("mostrata");
      vinto();                       /* da qui in poi ci pensa la festa */
    }

    function sbagliato() {
      tiri++;
      campo.classList.add("parata");
      pallone.classList.add("respinto");
      portiere.classList.add("presa");
      esito.textContent = SFOTTO[Math.min(tiri - 1, SFOTTO.length - 1)];
      esito.classList.add("mostrato");

      setTimeout(function () {
        esito.classList.remove("mostrato");
        esito.classList.add("via");
      }, fermoImmagine ? 40 : 1500);

      setTimeout(function () {
        pulisci();
        contatore.textContent = String(tiri + 1);
        occupato = false;
        abilita(true);
      }, fermoImmagine ? 80 : 2000);
    }

    mire.forEach(function (m) {
      m.addEventListener("click", function (ev) {
        ev.preventDefault();
        tira(Number(m.dataset.zona));
      });
    });

    abilita(true);
  }

  return { attiva: attiva, prepara: prepara };
})();
