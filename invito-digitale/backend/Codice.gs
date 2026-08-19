/* =====================================================================
   CODICE.GS — da incollare dentro Google Apps Script
   Riceve i messaggi anonimi e le conferme e li scrive in un foglio
   Google che vedi solo tu. Segui backend/ISTRUZIONI.md.
   ===================================================================== */

/* ---------- LE UNICHE TRE RIGHE DA CAMBIARE ---------- */

// Il codice che serve alla festeggiata per leggere i messaggi.
// Cambialo, e non dirlo a nessuno.
var CODICE_SEGRETO = 'MARTA18';

// Vuoi che i messaggi restino chiusi fino alla festa?
// Scrivi la data così: '2026-08-04T20:00:00'. Lascia '' per leggerli subito.
var APERTURA_MESSAGGI = '';

// true = salva anche l'ora esatta di ogni messaggio.
// Lascialo su false: sapere l'ora può far capire chi ha scritto cosa.
var SALVA_ORARIO = false;

/* ---------- da qui in giù non serve toccare niente ---------- */

var FUSO = 'Europe/Rome';

function foglio_(nome, intestazione) {
  var libro = SpreadsheetApp.getActiveSpreadsheet();
  var f = libro.getSheetByName(nome);
  if (!f) {
    f = libro.insertSheet(nome);
    f.appendRow(intestazione);
    f.getRange(1, 1, 1, intestazione.length).setFontWeight('bold');
    f.setFrozenRows(1);
  }
  return f;
}

function risposta_(oggetto) {
  return ContentService
    .createTextOutput(JSON.stringify(oggetto))
    .setMimeType(ContentService.MimeType.JSON);
}

function quando_() {
  var ora = new Date();
  return SALVA_ORARIO
    ? Utilities.formatDate(ora, FUSO, 'dd/MM/yyyy HH:mm')
    : Utilities.formatDate(ora, FUSO, 'dd/MM/yyyy');
}

function testoPulito_(v, massimo) {
  var t = String(v === undefined || v === null ? '' : v).trim();
  if (t.length > massimo) t = t.substring(0, massimo);
  // l'apice iniziale impedisce a Fogli di leggere il testo come formula
  return (t.charAt(0) === '=' || t.charAt(0) === '+') ? "'" + t : t;
}

/* ---------- ARRIVANO I DATI DAL SITO ---------- */
function doPost(e) {
  try {
    var richiesta = JSON.parse(e.postData.contents);

    if (richiesta.tipo === 'messaggio') {
      var testo = testoPulito_(richiesta.dati && richiesta.dati.testo, 2000);
      if (!testo) return risposta_({ esito: 'errore', motivo: 'messaggio vuoto' });

      // Salviamo solo la data e il testo: nessun nome, nessuna mail, nessun
      // indirizzo. Il messaggio è anonimo davvero.
      foglio_('Messaggi', ['Quando', 'Messaggio']).appendRow([quando_(), testo]);
      return risposta_({ esito: 'ok' });
    }

    if (richiesta.tipo === 'conferma') {
      var d = richiesta.dati || {};
      foglio_('Conferme', ['Quando', 'Nome', 'Presente', 'Accompagnatori', 'Allergie', 'Note'])
        .appendRow([
          Utilities.formatDate(new Date(), FUSO, 'dd/MM/yyyy HH:mm'),
          testoPulito_(d.nome, 120),
          testoPulito_(d.presenza, 10),
          testoPulito_(d.accompagnatori, 4),
          testoPulito_(d.allergie, 300),
          testoPulito_(d.note, 500)
        ]);
      return risposta_({ esito: 'ok' });
    }

    return risposta_({ esito: 'errore', motivo: 'tipo sconosciuto' });

  } catch (err) {
    return risposta_({ esito: 'errore', motivo: String(err) });
  }
}

/* ---------- LA FESTEGGIATA LEGGE ---------- */
function doGet(e) {
  try {
    var p = (e && e.parameter) || {};
    if (p.azione !== 'leggi') {
      return risposta_({ esito: 'errore', motivo: 'azione sconosciuta' });
    }
    if (String(p.codice || '').trim() !== CODICE_SEGRETO) {
      return risposta_({ esito: 'errore', motivo: 'codice non valido' });
    }

    var messaggi = leggiFoglio_('Messaggi');
    var conferme = leggiFoglio_('Conferme');

    var aperto = true, apreIl = '';
    if (APERTURA_MESSAGGI) {
      var data = new Date(APERTURA_MESSAGGI);
      if (!isNaN(data.getTime())) {
        aperto = new Date().getTime() >= data.getTime();
        apreIl = Utilities.formatDate(data, FUSO, "d/MM/yyyy 'alle' HH:mm");
      }
    }

    var fuori = {
      esito: 'ok',
      aperto: aperto,
      apreIl: apreIl,
      quanti: messaggi.length,
      conferme: conferme.map(function (r) {
        return {
          nome: r[1], presenza: r[2], accompagnatori: r[3],
          allergie: r[4], note: r[5]
        };
      })
    };

    if (aperto) {
      // mescoliamo l'ordine: così non si capisce chi ha scritto per primo
      var testi = messaggi.map(function (r) { return { quando: r[0], testo: r[1] }; });
      for (var i = testi.length - 1; i > 0; i--) {
        var j = Math.floor(Math.random() * (i + 1));
        var t = testi[i]; testi[i] = testi[j]; testi[j] = t;
      }
      fuori.messaggi = testi;
    }

    return risposta_(fuori);

  } catch (err) {
    return risposta_({ esito: 'errore', motivo: String(err) });
  }
}

function leggiFoglio_(nome) {
  var f = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(nome);
  if (!f || f.getLastRow() < 2) return [];
  return f.getRange(2, 1, f.getLastRow() - 1, f.getLastColumn()).getValues()
    .map(function (riga) { return riga.map(function (c) { return String(c); }); })
    .filter(function (riga) { return riga.join('').trim() !== ''; });
}

/* ---------- PROVA VELOCE ----------
   Premi "Esegui" su questa funzione per controllare che tutto funzioni:
   scrive un messaggio finto e poi lo cancella.
------------------------------------ */
function provaTutto() {
  doPost({ postData: { contents: JSON.stringify({
    azione: 'salva', tipo: 'messaggio', dati: { testo: 'Prova, cancellami pure.' }
  }) } });

  var lettura = doGet({ parameter: { azione: 'leggi', codice: CODICE_SEGRETO } });
  Logger.log(lettura.getContent());
  Logger.log('Se qui sopra vedi "esito":"ok" allora funziona tutto.');
}
