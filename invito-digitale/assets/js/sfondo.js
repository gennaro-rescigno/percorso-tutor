/* =====================================================================
   SFONDO.JS — quello che si muove dietro all'invito.
   Due mondi, scelti da  tema:  dentro config.js:
     "cipria"    → pioggia di glitter e giardino di rose
     "discoteca" → palla specchiata, fasci di luce e pista da ballo
   Tutto disegnato dal codice: nessuna immagine da caricare.
   ===================================================================== */
(function () {
  "use strict";

  var fermoImmagine = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var tema = (window.CONFIG && window.CONFIG.tema) || "cipria";

  var telaGlitter = document.getElementById("glitter");
  var telaRose = document.getElementById("rose");

  /* piccolo generatore casuale con seme fisso: il disegno resta sempre uguale */
  function caso(seme) {
    return function () {
      seme |= 0; seme = (seme + 0x6D2B79F5) | 0;
      var t = Math.imul(seme ^ (seme >>> 15), 1 | seme);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function preparaTela(tela, densitaMassima) {
    var dpr = Math.min(window.devicePixelRatio || 1, densitaMassima || 2);
    var l = tela.clientWidth, a = tela.clientHeight;
    tela.width = Math.round(l * dpr);
    tela.height = Math.round(a * dpr);
    var ctx = tela.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return { ctx: ctx, l: l, a: a };
  }

  /* =====================================================================
     TEMA CIPRIA
     ===================================================================== */

  function pioggiaDiGlitter() {
    var ctxG, largG, altG, scintille = [];

    function nuovaScintilla(iniziale) {
      return {
        x: Math.random() * largG,
        y: iniziale ? Math.random() * altG : -10,
        r: 0.5 + Math.random() * 1.7,
        v: 6 + Math.random() * 26,          // pixel al secondo
        onda: Math.random() * Math.PI * 2,
        ampiezza: 4 + Math.random() * 16,
        fase: Math.random() * Math.PI * 2,
        ritmo: 0.6 + Math.random() * 1.8,
        scia: Math.random() < 0.22           // qualcuna lascia una scia sottile
      };
    }

    function popola() {
      var quante = Math.round(Math.min(150, (largG * altG) / 5200));
      scintille = [];
      for (var i = 0; i < quante; i++) scintille.push(nuovaScintilla(true));
    }

    function ridimensiona() {
      var m = preparaTela(telaGlitter);
      ctxG = m.ctx; largG = m.l; altG = m.a;
      popola();
    }

    function disegna(t) {
      ctxG.clearRect(0, 0, largG, altG);
      for (var i = 0; i < scintille.length; i++) {
        var s = scintille[i];
        var x = s.x + Math.sin(t * 0.0006 * s.ritmo + s.onda) * s.ampiezza;
        var luce = 0.35 + 0.65 * Math.abs(Math.sin(t * 0.0011 * s.ritmo + s.fase));

        if (s.scia) {
          var g = ctxG.createLinearGradient(x, s.y - 26, x, s.y);
          g.addColorStop(0, "rgba(255,255,255,0)");
          g.addColorStop(1, "rgba(255,255,255," + (luce * 0.28).toFixed(3) + ")");
          ctxG.fillStyle = g;
          ctxG.fillRect(x - 0.4, s.y - 26, 0.8, 26);
        }

        ctxG.beginPath();
        ctxG.arc(x, s.y, s.r, 0, Math.PI * 2);
        ctxG.fillStyle = "rgba(255,252,250," + (luce * 0.9).toFixed(3) + ")";
        ctxG.fill();

        if (s.r > 1.5) {                    // le più grandi brillano a croce
          ctxG.strokeStyle = "rgba(255,255,255," + (luce * 0.4).toFixed(3) + ")";
          ctxG.lineWidth = 0.6;
          ctxG.beginPath();
          ctxG.moveTo(x - s.r * 2.6, s.y); ctxG.lineTo(x + s.r * 2.6, s.y);
          ctxG.moveTo(x, s.y - s.r * 2.6); ctxG.lineTo(x, s.y + s.r * 2.6);
          ctxG.stroke();
        }
      }
    }

    var ultimo = 0;
    function anima(t) {
      var dt = ultimo ? Math.min((t - ultimo) / 1000, 0.05) : 0;
      ultimo = t;
      for (var i = 0; i < scintille.length; i++) {
        var s = scintille[i];
        s.y += s.v * dt;
        if (s.y - 30 > altG) scintille[i] = nuovaScintilla(false);
      }
      disegna(t);
      requestAnimationFrame(anima);
    }

    ridimensiona();
    if (fermoImmagine) disegna(0); else requestAnimationFrame(anima);
    window.addEventListener("resize", function () {
      ridimensiona();
      if (fermoImmagine) disegna(0);
    });
  }

  function giardinoDiRose() {
    /* un petalo: una goccia che parte dal centro del fiore */
    function petalo(ctx, angolo, raggio, larghezza) {
      var cx = Math.cos(angolo) * raggio, cy = Math.sin(angolo) * raggio;
      var a1 = angolo - larghezza, a2 = angolo + larghezza;
      ctx.beginPath();
      ctx.moveTo(0, 0);
      ctx.quadraticCurveTo(Math.cos(a1) * raggio * 1.15, Math.sin(a1) * raggio * 1.15, cx, cy);
      ctx.quadraticCurveTo(Math.cos(a2) * raggio * 1.15, Math.sin(a2) * raggio * 1.15, 0, 0);
      ctx.closePath();
    }

    function rosa(ctx, x, y, r, giro, t) {
      ctx.save();
      ctx.translate(x, y);
      ctx.rotate(giro);

      var corone = [
        { quanti: 9, raggio: 1.00, largo: 0.50 },
        { quanti: 7, raggio: 0.72, largo: 0.56 },
        { quanti: 5, raggio: 0.46, largo: 0.66 }
      ];
      for (var c = 0; c < corone.length; c++) {
        var co = corone[c];
        /* chiaro al centro, appena più carico in punta: dà profondità agli strati */
        var sfuma = ctx.createRadialGradient(0, 0, r * 0.04, 0, 0, r * co.raggio * 1.05);
        sfuma.addColorStop(0, t.luce);
        sfuma.addColorStop(0.62, t.luce);
        sfuma.addColorStop(1, t.chiaro);
        for (var i = 0; i < co.quanti; i++) {
          var a = (i / co.quanti) * Math.PI * 2 + c * 0.5;
          petalo(ctx, a, r * co.raggio, co.largo);
          ctx.fillStyle = sfuma;
          ctx.fill();
          ctx.strokeStyle = t.ombra;      /* il filo d'ombra separa un petalo dall'altro */
          ctx.lineWidth = Math.max(0.35, r * 0.008);
          ctx.stroke();
        }
      }

      /* il bocciolo centrale: una spirale, il segno che dice "rosa" */
      ctx.beginPath();
      for (var k = 0; k <= 34; k++) {
        var ang = k * 0.38 + 0.6;
        var rad = r * 0.05 + k * r * 0.0072;
        var px = Math.cos(ang) * rad, py = Math.sin(ang) * rad;
        if (k === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
      }
      ctx.strokeStyle = t.ombra;
      ctx.lineWidth = Math.max(0.5, r * 0.035);
      ctx.lineCap = "round";
      ctx.stroke();

      ctx.restore();
    }

    function perla(ctx, x, y, r) {
      var g = ctx.createRadialGradient(x - r * 0.35, y - r * 0.4, r * 0.1, x, y, r);
      g.addColorStop(0, "rgba(255,255,255,0.98)");
      g.addColorStop(0.6, "rgba(250,236,232,0.9)");
      g.addColorStop(1, "rgba(224,188,183,0.8)");
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fillStyle = g;
      ctx.fill();
    }

    /* un piccolo brillante a quattro punte */
    function brillante(ctx, x, y, r) {
      ctx.save();
      ctx.translate(x, y);
      ctx.beginPath();
      ctx.moveTo(0, -r);
      ctx.quadraticCurveTo(0, 0, r, 0);
      ctx.quadraticCurveTo(0, 0, 0, r);
      ctx.quadraticCurveTo(0, 0, -r, 0);
      ctx.quadraticCurveTo(0, 0, 0, -r);
      ctx.fillStyle = "rgba(255,255,255,0.9)";
      ctx.fill();
      ctx.restore();
    }

    function disegna() {
      var m = preparaTela(telaRose);
      var ctx = m.ctx, L = m.l, A = m.a;
      ctx.clearRect(0, 0, L, A);

      /* tre file: quelle dietro più piccole e slavate, quelle davanti piene */
      var file = [
        { n: 7, y: 0.68, r: 0.20, velo: 0.45, tinte: { chiaro: "#F2D5D1", luce: "#FBEFEC", ombra: "rgba(198,146,141,0.22)" } },
        { n: 6, y: 0.88, r: 0.26, velo: 0.70, tinte: { chiaro: "#EFCDC8", luce: "#FCF2EF", ombra: "rgba(190,136,130,0.26)" } },
        { n: 5, y: 1.08, r: 0.32, velo: 0.92, tinte: { chiaro: "#EBC5BF", luce: "#FDF6F3", ombra: "rgba(178,120,114,0.30)" } }
      ];

      for (var k = 0; k < file.length; k++) {
        var f = file[k];
        ctx.globalAlpha = f.velo;
        var rnd = caso(2024 + k * 131);
        for (var i = 0; i < f.n; i++) {
          var x = ((i + 0.5) / f.n) * L + (rnd() - 0.5) * (L / f.n) * 0.9;
          var y = A * f.y + (rnd() - 0.5) * A * 0.07;
          var r = A * f.r * (0.75 + rnd() * 0.5);
          rosa(ctx, x, y, r, rnd() * Math.PI * 2, f.tinte);
          if (rnd() < 0.55) perla(ctx, x + r * (0.9 + rnd() * 0.6), y - r * (0.5 + rnd() * 0.6), 1.8 + rnd() * 3);
          if (rnd() < 0.3) brillante(ctx, x - r * (0.8 + rnd()), y - r * (0.6 + rnd() * 0.5), 2.5 + rnd() * 3);
        }
      }
      ctx.globalAlpha = 1;

      /* sfumatura in alto, così le rose nascono dallo sfondo */
      var velo = ctx.createLinearGradient(0, 0, 0, A * 0.62);
      velo.addColorStop(0, "rgba(0,0,0,1)");
      velo.addColorStop(1, "rgba(0,0,0,0)");
      ctx.globalCompositeOperation = "destination-out";
      ctx.fillStyle = velo;
      ctx.fillRect(0, 0, L, A * 0.62);
      ctx.globalCompositeOperation = "source-over";
    }

    disegna();
    var attesa;
    window.addEventListener("resize", function () {
      clearTimeout(attesa);
      attesa = setTimeout(disegna, 150);
    });
  }

  /* =====================================================================
     TEMA DISCOTECA
     ===================================================================== */

  function luciDaDiscoteca() {
    var TINTE = ["#FF2E88", "#35E7E0", "#7B3CF0", "#FF2E88", "#35E7E0", "#FFC24B"];

    var ctxL, L, A;              // la tela grande: fasci, palla, puntini
    var ctxP, LP, AP;            // la tela in fondo: la pista
    var fasci = [], puntini = [], pulviscolo = [], pozze = [];
    var raggioPalla, xPalla, yPalla;

    /* --- i fasci delle teste mobili --------------------------------- */
    function costruisciFasci() {
      fasci = [];
      var quanti = L < 420 ? 4 : 6;
      for (var i = 0; i < quanti; i++) {
        var lungo = Math.max(L, A) * 1.5;
        fasci.push({
          x: L * (0.12 + 0.76 * (i / Math.max(1, quanti - 1))),
          tinta: TINTE[i % TINTE.length],
          lungo: lungo,
          largo: lungo * (0.075 + (i % 3) * 0.025),
          centro: (i % 2 ? -1 : 1) * (0.15 + (i % 3) * 0.12),
          ampiezza: 0.32 + (i % 4) * 0.09,
          ritmo: 0.16 + (i % 5) * 0.045,
          fase: i * 1.7
        });
      }
    }

    /* Tre passate sempre più larghe e più deboli: i bordi si sfumano
       senza dover applicare un blur a tutta la tela (che costerebbe caro). */
    var PASSATE = [
      { largo: 0.30, forza: 1.00 },
      { largo: 0.62, forza: 0.42 },
      { largo: 1.00, forza: 0.20 }
    ];

    function disegnaFascio(f, t) {
      var angolo = f.centro + Math.sin(t * f.ritmo + f.fase) * f.ampiezza;
      ctxL.save();
      ctxL.translate(f.x, -A * 0.06);
      ctxL.rotate(angolo);

      for (var k = 0; k < PASSATE.length; k++) {
        var pa = PASSATE[k];
        var g = ctxL.createLinearGradient(0, 0, 0, f.lungo);
        g.addColorStop(0, tinta(f.tinta, 0.34 * pa.forza));
        g.addColorStop(0.35, tinta(f.tinta, 0.20 * pa.forza));
        g.addColorStop(0.75, tinta(f.tinta, 0.07 * pa.forza));
        g.addColorStop(1, tinta(f.tinta, 0));

        ctxL.beginPath();
        ctxL.moveTo(0, 0);
        ctxL.lineTo(-f.largo * pa.largo, f.lungo);
        ctxL.lineTo(f.largo * pa.largo, f.lungo);
        ctxL.closePath();
        ctxL.fillStyle = g;
        ctxL.fill();
      }

      /* la lampada da cui parte il fascio */
      var lampada = ctxL.createRadialGradient(0, 0, 0, 0, 0, f.largo * 0.9);
      lampada.addColorStop(0, tinta(f.tinta, 0.75));
      lampada.addColorStop(1, tinta(f.tinta, 0));
      ctxL.fillStyle = lampada;
      ctxL.beginPath();
      ctxL.arc(0, 0, f.largo * 0.9, 0, Math.PI * 2);
      ctxL.fill();

      ctxL.restore();
    }

    function tinta(hex, alfa) {
      var n = parseInt(hex.slice(1), 16);
      return "rgba(" + ((n >> 16) & 255) + "," + ((n >> 8) & 255) + "," + (n & 255) + "," + alfa + ")";
    }

    /* --- la palla specchiata -----------------------------------------
       Sta appesa sopra la busta. Quando l'invito si apre sale e sparisce:
       resterebbe ferma sopra i testi e non si leggerebbe più niente.     */
    function disegnaPalla(giro, presenza) {
      if (presenza < 0.01) return;
      var y = yPalla - (1 - presenza) * A * 0.3;

      ctxL.save();
      ctxL.globalAlpha = presenza;

      /* il filo a cui è appesa */
      ctxL.strokeStyle = "rgba(255,255,255,0.2)";
      ctxL.lineWidth = 1;
      ctxL.beginPath();
      ctxL.moveTo(xPalla, 0);
      ctxL.lineTo(xPalla, y - raggioPalla);
      ctxL.stroke();

      /* l'alone attorno */
      var alone = ctxL.createRadialGradient(xPalla, y, raggioPalla * 0.5, xPalla, y, raggioPalla * 3.6);
      alone.addColorStop(0, "rgba(222,208,255,0.42)");
      alone.addColorStop(0.45, "rgba(190,150,255,0.14)");
      alone.addColorStop(1, "rgba(190,150,255,0)");
      ctxL.fillStyle = alone;
      ctxL.beginPath();
      ctxL.arc(xPalla, y, raggioPalla * 3.6, 0, Math.PI * 2);
      ctxL.fill();

      /* la sfera, illuminata da sinistra in alto */
      var sfera = ctxL.createRadialGradient(
        xPalla - raggioPalla * 0.35, y - raggioPalla * 0.4, raggioPalla * 0.1,
        xPalla, y, raggioPalla);
      sfera.addColorStop(0, "#B9AEDC");
      sfera.addColorStop(0.6, "#5B4E85");
      sfera.addColorStop(1, "#241C42");
      ctxL.beginPath();
      ctxL.arc(xPalla, y, raggioPalla, 0, Math.PI * 2);
      ctxL.fillStyle = sfera;
      ctxL.fill();

      /* le facce a specchio */
      var righe = 9, colonne = 16;
      for (var i = 0; i < righe; i++) {
        var lat = -Math.PI / 2 + ((i + 0.5) / righe) * Math.PI;
        var cosLat = Math.cos(lat);
        for (var j = 0; j < colonne; j++) {
          var lon = (j / colonne) * Math.PI * 2 + giro;
          var dz = cosLat * Math.cos(lon);
          if (dz <= 0.04) continue;                    // faccia girata dall'altra parte
          var dx = cosLat * Math.sin(lon), dy = Math.sin(lat);
          var lato = (raggioPalla * 2.3 / colonne) * (0.6 + 0.4 * dz);
          var luce = Math.pow(dz, 0.55) * (0.35 + 0.65 * Math.abs(Math.sin(lon * 3.1 + lat * 4.7)));
          ctxL.fillStyle = "rgba(248,244,255," + luce.toFixed(3) + ")";
          ctxL.fillRect(xPalla + dx * raggioPalla - lato / 2, y + dy * raggioPalla - lato / 2, lato, lato);
        }
      }

      ctxL.restore();
    }

    /* --- i puntini di luce che la palla sparge nella stanza ---------- */
    function costruisciPuntini() {
      puntini = [];
      var rnd = caso(77);
      var quanti = L < 420 ? 55 : 85;
      for (var i = 0; i < quanti; i++) {
        puntini.push({
          lon: rnd() * Math.PI * 2,
          lat: (rnd() - 0.5) * 1.5,
          r: 1.4 + rnd() * 3.4,
          tinta: rnd() < 0.72 ? "#EDE6FF" : TINTE[Math.floor(rnd() * 3)]
        });
      }
    }

    function disegnaPuntini(giro, forzaGenerale) {
      var distanza = Math.max(L, A) * 1.15;
      for (var i = 0; i < puntini.length; i++) {
        var p = puntini[i];
        var lon = p.lon + giro;
        var cosLat = Math.cos(p.lat);
        var dz = cosLat * Math.cos(lon);
        if (dz >= -0.05) continue;                     // il raggio va dietro la palla
        var dx = cosLat * Math.sin(lon), dy = Math.sin(p.lat) + 0.35;
        var x = xPalla + dx * distanza;
        var y = yPalla + dy * distanza * 0.55;
        if (x < -30 || x > L + 30 || y < -30 || y > A + 30) continue;

        var forza = Math.min(1, -dz) * 0.85 * forzaGenerale;
        var g = ctxL.createRadialGradient(x, y, 0, x, y, p.r * 3.2);
        g.addColorStop(0, tinta(p.tinta, forza));
        g.addColorStop(0.4, tinta(p.tinta, forza * 0.35));
        g.addColorStop(1, tinta(p.tinta, 0));
        ctxL.fillStyle = g;
        ctxL.beginPath();
        ctxL.arc(x, y, p.r * 3.2, 0, Math.PI * 2);
        ctxL.fill();
      }
    }

    /* --- il pulviscolo che si vede dentro i fasci -------------------- */
    function costruisciPulviscolo() {
      pulviscolo = [];
      var quante = Math.round(Math.min(70, (L * A) / 12000));
      for (var i = 0; i < quante; i++) {
        pulviscolo.push({
          x: Math.random() * L,
          y: Math.random() * A,
          r: 0.4 + Math.random() * 1.1,
          v: 3 + Math.random() * 12,
          onda: Math.random() * Math.PI * 2
        });
      }
    }

    function disegnaPulviscolo(t) {
      for (var i = 0; i < pulviscolo.length; i++) {
        var p = pulviscolo[i];
        var x = p.x + Math.sin(t * 0.5 + p.onda) * 9;
        ctxL.beginPath();
        ctxL.arc(x, p.y, p.r, 0, Math.PI * 2);
        ctxL.fillStyle = "rgba(226,214,255,0.5)";
        ctxL.fill();
      }
    }

    /* --- la pista: le pozze di luce sul pavimento -------------------- */
    function costruisciPozze() {
      pozze = [];
      var quante = LP < 420 ? 4 : 6;
      for (var i = 0; i < quante; i++) {
        pozze.push({
          base: LP * (0.1 + 0.8 * (i / Math.max(1, quante - 1))),
          tinta: TINTE[(i + 1) % TINTE.length],
          rx: LP * (0.16 + (i % 3) * 0.06),
          ry: AP * (0.3 + (i % 2) * 0.12),
          y: AP * (0.55 + (i % 3) * 0.16),
          ampiezza: LP * (0.1 + (i % 4) * 0.05),
          ritmo: 0.19 + (i % 5) * 0.05,
          fase: i * 2.1
        });
      }
    }

    function disegnaPista(t) {
      ctxP.clearRect(0, 0, LP, AP);
      ctxP.globalCompositeOperation = "lighter";

      for (var i = 0; i < pozze.length; i++) {
        var p = pozze[i];
        var x = p.base + Math.sin(t * p.ritmo + p.fase) * p.ampiezza;
        var battito = 0.55 + 0.45 * Math.abs(Math.sin(t * 0.9 + p.fase));

        ctxP.save();
        ctxP.translate(x, p.y);
        ctxP.scale(1, p.ry / p.rx);
        var g = ctxP.createRadialGradient(0, 0, 0, 0, 0, p.rx);
        g.addColorStop(0, tinta(p.tinta, 0.5 * battito));
        g.addColorStop(0.45, tinta(p.tinta, 0.16 * battito));
        g.addColorStop(1, tinta(p.tinta, 0));
        ctxP.fillStyle = g;
        ctxP.beginPath();
        ctxP.arc(0, 0, p.rx, 0, Math.PI * 2);
        ctxP.fill();
        ctxP.restore();
      }

      /* la linea del pavimento, dove la luce rimbalza */
      var riga = ctxP.createLinearGradient(0, AP * 0.82, 0, AP);
      riga.addColorStop(0, "rgba(123,60,240,0)");
      riga.addColorStop(1, "rgba(123,60,240,0.28)");
      ctxP.fillStyle = riga;
      ctxP.fillRect(0, AP * 0.82, LP, AP * 0.18);

      ctxP.globalCompositeOperation = "source-over";
    }

    /* --- montaggio ---------------------------------------------------- */
    function ridimensiona() {
      var m = preparaTela(telaGlitter, 1.5);
      ctxL = m.ctx; L = m.l; A = m.a;
      raggioPalla = Math.max(20, Math.min(38, L * 0.075));
      xPalla = L * 0.5;
      yPalla = Math.max(raggioPalla * 2.2, A * 0.13);
      costruisciFasci();
      costruisciPuntini();
      costruisciPulviscolo();

      if (telaRose) {
        var n = preparaTela(telaRose, 1.5);
        ctxP = n.ctx; LP = n.l; AP = n.a;
        costruisciPozze();
      }
    }

    /* 1 finché la busta è ancora lì, 0 quando l'invito è aperto */
    function palleggio() {
      var scena = document.getElementById("scenaBusta");
      return (scena && !scena.classList.contains("andata")) ? 1 : 0;
    }

    var presenzaPalla = -1;

    function disegnaTutto(secondi) {
      if (presenzaPalla < 0) presenzaPalla = palleggio();
      else presenzaPalla += (palleggio() - presenzaPalla) * 0.045;

      ctxL.clearRect(0, 0, L, A);

      ctxL.globalCompositeOperation = "lighter";
      for (var i = 0; i < fasci.length; i++) disegnaFascio(fasci[i], secondi);
      disegnaPuntini(secondi * 0.26, 0.5 + 0.5 * presenzaPalla);
      disegnaPulviscolo(secondi);
      ctxL.globalCompositeOperation = "source-over";

      disegnaPalla(secondi * 0.26, presenzaPalla);

      if (ctxP) disegnaPista(secondi);
    }

    var ultimo = 0;
    function anima(t) {
      var secondi = t / 1000;
      if (!fermoImmagine) {
        for (var i = 0; i < pulviscolo.length; i++) {
          var p = pulviscolo[i];
          p.y -= p.v * (ultimo ? Math.min((t - ultimo) / 1000, 0.05) : 0);
          if (p.y < -10) { p.y = A + 10; p.x = Math.random() * L; }
        }
      }
      ultimo = t;
      disegnaTutto(secondi);
      requestAnimationFrame(anima);
    }

    ridimensiona();
    if (fermoImmagine) disegnaTutto(4.2); else requestAnimationFrame(anima);

    var attesa;
    window.addEventListener("resize", function () {
      clearTimeout(attesa);
      attesa = setTimeout(function () {
        ridimensiona();
        if (fermoImmagine) disegnaTutto(4.2);
      }, 150);
    });
  }

  /* =====================================================================
     Si accende il tema giusto
     ===================================================================== */
  if (tema === "discoteca") {
    if (telaGlitter) luciDaDiscoteca();
  } else {
    if (telaGlitter) pioggiaDiGlitter();
    if (telaRose) giardinoDiRose();
  }
})();
