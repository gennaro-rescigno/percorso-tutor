/* =====================================================================
   SFONDO.JS — la pioggia di glitter e il giardino di rose
   Tutto disegnato dal codice: nessuna immagine da caricare.
   ===================================================================== */
(function () {
  "use strict";

  var fermoImmagine = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* piccolo generatore casuale con seme fisso: le rose restano sempre uguali */
  function caso(seme) {
    return function () {
      seme |= 0; seme = (seme + 0x6D2B79F5) | 0;
      var t = Math.imul(seme ^ (seme >>> 15), 1 | seme);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function preparaTela(tela) {
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var l = tela.clientWidth, a = tela.clientHeight;
    tela.width = Math.round(l * dpr);
    tela.height = Math.round(a * dpr);
    var ctx = tela.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return { ctx: ctx, l: l, a: a };
  }

  /* -------------------------------------------------------------------
     1. PIOGGIA DI GLITTER
     ------------------------------------------------------------------- */
  var telaGlitter = document.getElementById("glitter");
  if (telaGlitter) {
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

    function ridimensionaGlitter() {
      var m = preparaTela(telaGlitter);
      ctxG = m.ctx; largG = m.l; altG = m.a;
      popola();
    }

    function disegnaScintille(t) {
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
      disegnaScintille(t);
      requestAnimationFrame(anima);
    }

    ridimensionaGlitter();
    if (fermoImmagine) {
      disegnaScintille(0);                  // campo fermo, senza movimento
    } else {
      requestAnimationFrame(anima);
    }
    window.addEventListener("resize", function () {
      ridimensionaGlitter();
      if (fermoImmagine) disegnaScintille(0);
    });
  }

  /* -------------------------------------------------------------------
     2. IL GIARDINO DI ROSE IN FONDO ALLA PAGINA
     ------------------------------------------------------------------- */
  var telaRose = document.getElementById("rose");
  if (telaRose) {

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

      /* tre corone di petali, sempre più piccole verso il centro */
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

    function disegnaRose() {
      var m = preparaTela(telaRose);
      var ctx = m.ctx, L = m.l, A = m.a;
      ctx.clearRect(0, 0, L, A);

      /* tre file: quelle dietro più piccole e slavate, quelle davanti piene */
      var file = [
        { n: 7, y: 0.68, r: 0.20, velo: 0.45, tinte: { chiaro: "#F2D5D1", luce: "#FBEFEC", ombra: "rgba(198,146,141,0.22)" } },
        { n: 6, y: 0.88, r: 0.26, velo: 0.70, tinte: { chiaro: "#EFCDC8", chiaro2: "", luce: "#FCF2EF", ombra: "rgba(190,136,130,0.26)" } },
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

    disegnaRose();
    var attesa;
    window.addEventListener("resize", function () {
      clearTimeout(attesa);
      attesa = setTimeout(disegnaRose, 150);
    });
  }
})();
