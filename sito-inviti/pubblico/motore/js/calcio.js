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

  /* Le due figure sono disegnate a mano in SVG: ogni pezzo del corpo
     è un gruppo con la sua cerniera, così braccia e gambe si muovono
     davvero invece di scivolare tutte insieme. */
  var PORTIERE_SVG =
    "<svg class=\"p-fig\" viewBox=\"0 0 220 300\" xmlns=\"http://www.w3.org/2000/svg\" aria-hidden=\"true\" focusable=\"false\">" +
    "<defs>" +
    "<linearGradient id=\"kMag\" x1=\"0\" y1=\"0\" x2=\".4\" y2=\"1\"><stop offset=\"0\" stop-color=\"#FFDD6B\"/><stop offset=\".48\" stop-color=\"#F2A81C\"/><stop offset=\"1\" stop-color=\"#B96A06\"/></linearGradient>" +
    "<linearGradient id=\"kMan\" x1=\"0\" y1=\"0\" x2=\"1\" y2=\"1\"><stop offset=\"0\" stop-color=\"#FFD25A\"/><stop offset=\"1\" stop-color=\"#C87C09\"/></linearGradient>" +
    "<linearGradient id=\"kPel\" x1=\".15\" y1=\"0\" x2=\".9\" y2=\"1\"><stop offset=\"0\" stop-color=\"#F6CBA4\"/><stop offset=\"1\" stop-color=\"#C0834F\"/></linearGradient>" +
    "<linearGradient id=\"kPan\" x1=\"0\" y1=\"0\" x2=\".3\" y2=\"1\"><stop offset=\"0\" stop-color=\"#2A4467\"/><stop offset=\"1\" stop-color=\"#0C1A2B\"/></linearGradient>" +
    "<linearGradient id=\"kCal\" x1=\"0\" y1=\"0\" x2=\".4\" y2=\"1\"><stop offset=\"0\" stop-color=\"#24405F\"/><stop offset=\"1\" stop-color=\"#0E1F33\"/></linearGradient>" +
    "<linearGradient id=\"kGua\" x1=\".2\" y1=\"0\" x2=\".85\" y2=\"1\"><stop offset=\"0\" stop-color=\"#FFFFFF\"/><stop offset=\".5\" stop-color=\"#A8F0C4\"/><stop offset=\"1\" stop-color=\"#22935A\"/></linearGradient>" +
    "<linearGradient id=\"kCap\" x1=\".2\" y1=\"0\" x2=\".8\" y2=\"1\"><stop offset=\"0\" stop-color=\"#4A3225\"/><stop offset=\"1\" stop-color=\"#1C110A\"/></linearGradient>" +
    "<clipPath id=\"kTaglio\"><path d=\"M87 80 q-9 5-10 16 l-3 40 q-1 8 1 14 l1 4 q17 6 34 6 q17 0 34-6 l1-4 q2-6 1-14 l-3-40 q-1-11-10-16 q-11-5-23-5 q-12 0-23 5 z\"/></clipPath>" +
    "<linearGradient id=\"kVol\" x1=\"0\" y1=\"0\" x2=\"1\" y2=\"0\"><stop offset=\"0\" stop-color=\"#000000\" stop-opacity=\".3\"/><stop offset=\".28\" stop-color=\"#000000\" stop-opacity=\"0\"/><stop offset=\".7\" stop-color=\"#000000\" stop-opacity=\"0\"/><stop offset=\"1\" stop-color=\"#000000\" stop-opacity=\".38\"/></linearGradient>" +
    "<radialGradient id=\"kOmb\" cx=\".5\" cy=\".5\" r=\".5\"><stop offset=\"0\" stop-color=\"#000000\" stop-opacity=\".55\"/><stop offset=\"1\" stop-color=\"#000000\" stop-opacity=\"0\"/></radialGradient>" +
    "</defs>" +
    "<ellipse class=\"k-ombra\" cx=\"110\" cy=\"291\" rx=\"54\" ry=\"12\" fill=\"url(#kOmb)\"/>" +
    "<g class=\"k-corpo\">" +
    "  <!-- GAMBE (dietro al busto) -->" +
    "  <g class=\"k-arto k-gamba k-gsx\">" +
    "    <line class=\"k-coscia\" x1=\"99\" y1=\"166\" x2=\"95\" y2=\"226\"/>" +
    "    <g class=\"k-arto k-stinco-g k-ssx\">" +
    "      <line class=\"k-calza\" x1=\"95\" y1=\"226\" x2=\"93\" y2=\"276\"/>" +
    "      <path class=\"k-fascia\" d=\"M87 234 L103 234\"/>" +
    "      <g class=\"k-scarpa\">" +
    "        <path class=\"k-scarpa-c\" d=\"M85 271 q-16 3 -18 12 q-1 7 8 7 l24 0 q7 0 7-7 l-1-11 z\"/>" +
    "        <path class=\"k-scarpa-l\" d=\"M69 285 l43 0\" />" +
    "        <path class=\"k-scarpa-b\" d=\"M83 274 q-9 2 -11 7\"/>" +
    "      </g>" +
    "    </g>" +
    "  </g>" +
    "  <g class=\"k-arto k-gamba k-gdx\">" +
    "    <line class=\"k-coscia\" x1=\"121\" y1=\"166\" x2=\"125\" y2=\"226\"/>" +
    "    <g class=\"k-arto k-stinco-g k-sdx\">" +
    "      <line class=\"k-calza\" x1=\"125\" y1=\"226\" x2=\"127\" y2=\"276\"/>" +
    "      <path class=\"k-fascia\" d=\"M117 234 L133 234\"/>" +
    "      <g class=\"k-scarpa\">" +
    "        <path class=\"k-scarpa-c\" d=\"M135 271 q16 3 18 12 q1 7-8 7 l-24 0 q-7 0-7-7 l1-11 z\"/>" +
    "        <path class=\"k-scarpa-l\" d=\"M151 285 l-43 0\" />" +
    "        <path class=\"k-scarpa-b\" d=\"M137 274 q9 2 11 7\"/>" +
    "      </g>" +
    "    </g>" +
    "  </g>" +
    "  <!-- PANTALONCINI -->" +
    "  <path class=\"k-panta\" d=\"M84 148 L136 148 L139 176 q-1 6-8 6 l-14 0 q-4 0-5-5 l-2-12 l-2 12 q-1 5-5 5 l-14 0 q-7 0-8-6 z\"/>" +
    "  <path class=\"k-panta-riga\" d=\"M85.5 152 L83 176\"/>" +
    "  <path class=\"k-panta-riga\" d=\"M134.5 152 L137 176\"/>" +
    "  <!-- BUSTO -->" +
    "  <g clip-path=\"url(#kTaglio)\">" +
    "    <path class=\"k-maglia\" d=\"M70 70 h80 v110 h-80 z\"/>" +
    "    <path class=\"k-maglia-om\" d=\"M70 72 q40-14 80 0 l0 22 q-40-14-80 0 z\"/>" +
    "    <path class=\"k-maglia-fi\" d=\"M70 84 q40-14 80 0 l0 5 q-40-14-80 0 z\"/>" +
    "    <path class=\"k-maglia-fi\" d=\"M70 150 h80 v6 h-80 z\"/>" +
    "    <path class=\"k-maglia-la\" d=\"M70 96 l10 0 l-3 84 l-10 0 z\"/>" +
    "    <path class=\"k-maglia-la\" d=\"M150 96 l-10 0 l3 84 l10 0 z\"/>" +
    "    <text class=\"k-numero\" x=\"110\" y=\"136\">1</text>" +
    "    <path class=\"k-maglia-vo\" d=\"M70 70 h80 v110 h-80 z\"/>" +
    "  </g>" +
    "  <path class=\"k-colletto\" d=\"M99 76 q11 9 22 0 l3 5 q-14 11-28 0 z\"/>" +
    "  <!-- TESTA -->" +
    "  <path class=\"k-collo\" d=\"M101 62 l18 0 l1 14 q-10 5-20 0 z\"/>" +
    "  <ellipse class=\"k-orecchio\" cx=\"90\" cy=\"46\" rx=\"4.5\" ry=\"6\"/>" +
    "  <ellipse class=\"k-orecchio\" cx=\"130\" cy=\"46\" rx=\"4.5\" ry=\"6\"/>" +
    "  <ellipse class=\"k-viso\" cx=\"110\" cy=\"44\" rx=\"20\" ry=\"22\"/>" +
    "  <path class=\"k-capelli\" d=\"M90 42 q-2-22 20-23 q22 1 20 23 q-3-9-9-11 q-11 6-22 2 q-6 2-9 9 z\"/>" +
    "  <path class=\"k-sopr\" d=\"M99 39 q5-3 9-1\"/>" +
    "  <path class=\"k-sopr\" d=\"M121 39 q-5-3-9-1\"/>" +
    "  <ellipse class=\"k-occhio\" cx=\"103\" cy=\"46\" rx=\"2.6\" ry=\"3\"/>" +
    "  <ellipse class=\"k-occhio\" cx=\"117\" cy=\"46\" rx=\"2.6\" ry=\"3\"/>" +
    "  <path class=\"k-bocca\" d=\"M105 56 q5 4 10 0\"/>" +
    "  <!-- BRACCIA (davanti) -->" +
    "  <g class=\"k-arto k-braccio k-bsx\">" +
    "    <line class=\"k-manica\" x1=\"87\" y1=\"84\" x2=\"73\" y2=\"130\"/>" +
    "    <g class=\"k-arto k-avambraccio k-asx\">" +
    "      <line class=\"k-pelle\" x1=\"73\" y1=\"130\" x2=\"64\" y2=\"182\"/>" +
    "      <g class=\"k-guanto k-gua-sx\">" +
    "        <path class=\"k-gua-c\" d=\"M46 182 q-11 4-11 15 q0 15 12 19 q12 4 21-4 q7-7 6-19 q-1-10-10-13 z\"/>" +
    "        <path class=\"k-gua-p\" d=\"M49 187 q-8 4-8 13 q0 10 9 14\"/>" +
    "        <path class=\"k-gua-d\" d=\"M41 190 l20-5 M41 199 l21-4 M44 208 l20-5\"/>" +
    "        <path class=\"k-gua-po\" d=\"M58 173 l16 5 l-4 11 l-16-5 z\"/>" +
    "      </g>" +
    "    </g>" +
    "  </g>" +
    "  <g class=\"k-arto k-braccio k-bdx\">" +
    "    <line class=\"k-manica\" x1=\"133\" y1=\"84\" x2=\"147\" y2=\"130\"/>" +
    "    <g class=\"k-arto k-avambraccio k-adx\">" +
    "      <line class=\"k-pelle\" x1=\"147\" y1=\"130\" x2=\"156\" y2=\"182\"/>" +
    "      <g class=\"k-guanto k-gua-dx\">" +
    "        <path class=\"k-gua-c\" d=\"M174 182 q11 4 11 15 q0 15-12 19 q-12 4-21-4 q-7-7-6-19 q1-10 10-13 z\"/>" +
    "        <path class=\"k-gua-p\" d=\"M171 187 q8 4 8 13 q0 10-9 14\"/>" +
    "        <path class=\"k-gua-d\" d=\"M179 190 l-20-5 M179 199 l-21-4 M176 208 l-20-5\"/>" +
    "        <path class=\"k-gua-po\" d=\"M162 173 l-16 5 l4 11 l16-5 z\"/>" +
    "      </g>" +
    "    </g>" +
    "  </g>" +
    "</g>" +
    "</svg>";

  var GIOCATORE_SVG =
    "<svg class=\"g-fig\" viewBox=\"0 0 200 340\" xmlns=\"http://www.w3.org/2000/svg\" aria-hidden=\"true\" focusable=\"false\">" +
    "<defs>" +
    "<linearGradient id=\"jPel\" x1=\".15\" y1=\"0\" x2=\".9\" y2=\"1\"><stop offset=\"0\" stop-color=\"#F0BF93\"/><stop offset=\"1\" stop-color=\"#B8794A\"/></linearGradient>" +
    "<linearGradient id=\"jCap\" x1=\".2\" y1=\"0\" x2=\".85\" y2=\"1\"><stop offset=\"0\" stop-color=\"#5A3A26\"/><stop offset=\"1\" stop-color=\"#231409\"/></linearGradient>" +
    "<linearGradient id=\"jPan\" x1=\"0\" y1=\"0\" x2=\".3\" y2=\"1\"><stop offset=\"0\" stop-color=\"#25405F\"/><stop offset=\"1\" stop-color=\"#0B1728\"/></linearGradient>" +
    "<linearGradient id=\"jCal\" x1=\"0\" y1=\"0\" x2=\".4\" y2=\"1\"><stop offset=\"0\" stop-color=\"#22405E\"/><stop offset=\"1\" stop-color=\"#0D1E31\"/></linearGradient>" +
    "<linearGradient id=\"jSca\" x1=\".1\" y1=\"0\" x2=\".9\" y2=\"1\"><stop offset=\"0\" stop-color=\"#FF6A3D\"/><stop offset=\"1\" stop-color=\"#B32C0C\"/></linearGradient>" +
    "<linearGradient id=\"jMan\" x1=\"0\" y1=\"0\" x2=\"1\" y2=\"1\"><stop offset=\"0\" stop-color=\"#FDFBF6\"/><stop offset=\"1\" stop-color=\"#C9CFD8\"/></linearGradient>" +
    "<pattern id=\"jRighe\" width=\"26\" height=\"10\" patternUnits=\"userSpaceOnUse\" x=\"9\">" +
    "  <rect width=\"26\" height=\"10\" fill=\"#F6F7F9\"/>" +
    "  <rect width=\"13\" height=\"10\" fill=\"#17324F\"/>" +
    "</pattern>" +
    "<linearGradient id=\"jVolume\" x1=\"0\" y1=\"0\" x2=\"1\" y2=\"0\">" +
    "  <stop offset=\"0\" stop-color=\"#000000\" stop-opacity=\".34\"/>" +
    "  <stop offset=\".26\" stop-color=\"#000000\" stop-opacity=\"0\"/>" +
    "  <stop offset=\".72\" stop-color=\"#000000\" stop-opacity=\"0\"/>" +
    "  <stop offset=\"1\" stop-color=\"#000000\" stop-opacity=\".42\"/>" +
    "</linearGradient>" +
    "<radialGradient id=\"jOmb\" cx=\".5\" cy=\".5\" r=\".5\"><stop offset=\"0\" stop-color=\"#000000\" stop-opacity=\".5\"/><stop offset=\"1\" stop-color=\"#000000\" stop-opacity=\"0\"/></radialGradient>" +
    "<clipPath id=\"jTaglioMaglia\"><path d=\"M67 88 q-11 6-13 19 l-5 44 q-1 9 2 16 l3 8 q23 8 46 8 q23 0 46-8 l3-8 q3-7 2-16 l-5-44 q-2-13-13-19 q-15-7-33-7 q-18 0-33 7 z\"/></clipPath>" +
    "</defs>" +
    "<ellipse class=\"g-ombra\" cx=\"100\" cy=\"322\" rx=\"46\" ry=\"10\" fill=\"url(#jOmb)\"/>" +
    "<g class=\"g-corpo\">" +
    "  <!-- GAMBE -->" +
    "  <g class=\"g-arto g-gamba g-gsx\">" +
    "    <line class=\"g-coscia\" x1=\"87\" y1=\"192\" x2=\"84\" y2=\"252\"/>" +
    "    <g class=\"g-arto g-stinco-g g-ssx\">" +
    "      <line class=\"g-calza\" x1=\"84\" y1=\"252\" x2=\"83\" y2=\"302\"/>" +
    "      <path class=\"g-fascia\" d=\"M76 260 L92 260\"/>" +
    "      <g class=\"g-scarpa\">" +
    "        <path class=\"g-scarpa-c\" d=\"M74 297 q-9 2-10 10 q-1 8 8 9 l22 0 q7-1 7-9 l-1-10 z\"/>" +
    "        <path class=\"g-scarpa-s\" d=\"M64 308 l40 0 l0 4 q0 4-5 4 l-30 0 q-5 0-5-4 z\"/>" +
    "        <path class=\"g-scarpa-t\" d=\"M73 301 l22 0 M74 305 l21 0\"/>" +
    "      </g>" +
    "    </g>" +
    "  </g>" +
    "  <g class=\"g-arto g-gamba g-gdx\">" +
    "    <line class=\"g-coscia\" x1=\"113\" y1=\"192\" x2=\"116\" y2=\"252\"/>" +
    "    <g class=\"g-arto g-stinco-g g-sdx\">" +
    "      <line class=\"g-calza\" x1=\"116\" y1=\"252\" x2=\"117\" y2=\"302\"/>" +
    "      <path class=\"g-fascia\" d=\"M108 260 L124 260\"/>" +
    "      <g class=\"g-scarpa\">" +
    "        <path class=\"g-scarpa-c\" d=\"M126 297 q9 2 10 10 q1 8-8 9 l-22 0 q-7-1-7-9 l1-10 z\"/>" +
    "        <path class=\"g-scarpa-s\" d=\"M136 308 l-40 0 l0 4 q0 4 5 4 l30 0 q5 0 5-4 z\"/>" +
    "        <path class=\"g-scarpa-t\" d=\"M127 301 l-22 0 M126 305 l-21 0\"/>" +
    "      </g>" +
    "    </g>" +
    "  </g>" +
    "  <!-- PANTALONCINI -->" +
    "  <path class=\"g-panta\" d=\"M68 168 L132 168 L136 202 q-1 7-9 7 l-17 0 q-5 0-6-6 l-4-14 l-4 14 q-1 6-6 6 l-17 0 q-8 0-9-7 z\"/>" +
    "  <path class=\"g-panta-riga\" d=\"M70.5 173 L67 203\"/>" +
    "  <path class=\"g-panta-riga\" d=\"M129.5 173 L133 203\"/>" +
    "  <!-- MAGLIA -->" +
    "  <g clip-path=\"url(#jTaglioMaglia)\">" +
    "    <rect x=\"40\" y=\"80\" width=\"120\" height=\"110\" fill=\"url(#jRighe)\"/>" +
    "    <rect x=\"40\" y=\"80\" width=\"120\" height=\"110\" fill=\"url(#jVolume)\"/>" +
    "  </g>" +
    "  <path class=\"g-maglia-b\" d=\"M67 88 q-11 6-13 19 l-5 44 q-1 9 2 16 l3 8 q23 8 46 8 q23 0 46-8 l3-8 q3-7 2-16 l-5-44 q-2-13-13-19 q-15-7-33-7 q-18 0-33 7 z\"/>" +
    "  <path class=\"g-colletto\" d=\"M83 82 q17 10 34 0 l3 7 q-20 11-40 0 z\"/>" +
    "  <text class=\"g-nome\" x=\"100\" y=\"118\">MARTA</text>" +
    "  <text class=\"g-numero\" x=\"100\" y=\"166\">18</text>" +
    "  <!-- TESTA -->" +
    "  <path class=\"g-collo\" d=\"M89 62 l22 0 l2 20 q-13 6-26 0 z\"/>" +
    "  <ellipse class=\"g-orecchio\" cx=\"77\" cy=\"46\" rx=\"5\" ry=\"7\"/>" +
    "  <ellipse class=\"g-orecchio\" cx=\"123\" cy=\"46\" rx=\"5\" ry=\"7\"/>" +
    "  <ellipse class=\"g-nuca\" cx=\"100\" cy=\"44\" rx=\"22\" ry=\"24\"/>" +
    "  <path class=\"g-capelli\" d=\"M78 46 q-1-27 22-27 q23 0 22 27 q0 14-6 20 q-16 7-32 0 q-6-6-6-20 z\"/>" +
    "  <path class=\"g-capelli-l\" d=\"M86 28 q12-7 26 0\" opacity=\".35\"/>" +
    "  <!-- BRACCIA -->" +
    "  <g class=\"g-arto g-braccio g-bsx\">" +
    "    <line class=\"g-manica\" x1=\"66\" y1=\"92\" x2=\"58\" y2=\"130\"/>" +
    "    <g class=\"g-arto g-avambraccio g-asx\">" +
    "      <line class=\"g-pelle\" x1=\"58\" y1=\"130\" x2=\"52\" y2=\"170\"/>" +
    "      <ellipse class=\"g-mano\" cx=\"51\" cy=\"177\" rx=\"8\" ry=\"9\"/>" +
    "    </g>" +
    "  </g>" +
    "  <g class=\"g-arto g-braccio g-bdx\">" +
    "    <line class=\"g-manica\" x1=\"134\" y1=\"92\" x2=\"142\" y2=\"130\"/>" +
    "    <g class=\"g-arto g-avambraccio g-adx\">" +
    "      <line class=\"g-pelle\" x1=\"142\" y1=\"130\" x2=\"148\" y2=\"170\"/>" +
    "      <ellipse class=\"g-mano\" cx=\"149\" cy=\"177\" rx=\"8\" ry=\"9\"/>" +
    "    </g>" +
    "  </g>" +
    "</g>" +
    "</svg>";

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
    portiere.innerHTML = PORTIERE_SVG;

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
    giocatore.innerHTML = GIOCATORE_SVG;
    /* il nome sulla maglia: se è lungo lo stringo, così non esce dai fianchi */
    var nomeMaglia = giocatore.querySelector(".g-nome");
    nomeMaglia.textContent = nome;
    if (nome.length > 8) {
      nomeMaglia.setAttribute("textLength", "80");
      nomeMaglia.setAttribute("lengthAdjust", "spacingAndGlyphs");
    }
    giocatore.querySelector(".g-numero").textContent = numero;

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
