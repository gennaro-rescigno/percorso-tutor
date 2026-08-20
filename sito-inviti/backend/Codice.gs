/* =====================================================================
   CODICE.GS — un solo script per TUTTI gli inviti.
   Si prepara una volta sola: da lì in poi ogni invito nuovo funziona
   senza toccare più niente qui dentro.

   Tre schede nel foglio (si creano da sole):
     Registro  → invito | festeggiata | codice | apertura | creato
     Messaggi  → invito | quando | testo
     Conferme  → invito | id | quando | nome | presente | ospiti | allergie | note

   Chi può fare cosa:
     - chiunque abbia il link dell'invito può SCRIVERE (messaggio, conferma)
       e chiedere se un nome è già preso;
     - per LEGGERE i messaggi e le conferme, o per CANCELLARE un invitato,
       serve il codice della festeggiata, che sta solo nel Registro e non
       compare da nessuna parte dentro alle pagine.
   ===================================================================== */

var FUSO = 'Europe/Rome';

/* ---------------------------------------------------------------- utili */

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

function testoPulito_(v, massimo) {
  var t = String(v === undefined || v === null ? '' : v).trim();
  if (t.length > massimo) t = t.substring(0, massimo);
  /* l'apice iniziale impedisce a Fogli di leggere il testo come formula */
  return (t.charAt(0) === '=' || t.charAt(0) === '+') ? "'" + t : t;
}

/* Per confrontare due nomi: via accenti, maiuscole, punteggiatura e
   spazi doppi. Così "Mario  Rossi" e "mario rossi" sono lo stesso. */
function nomeConfronto_(nome) {
  return String(nome || '')
    .toLowerCase()
    .normalize('NFD').replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9 ]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function righe_(nome) {
  var f = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(nome);
  if (!f || f.getLastRow() < 2) return [];
  return f.getRange(2, 1, f.getLastRow() - 1, f.getLastColumn()).getValues();
}

/* Cerca l'invito nel Registro. Torna null se non c'è: un invito che non
   è registrato non può scrivere niente, così nessuno può usare lo script
   per riempire il foglio di roba a caso. */
function invitoRegistrato_(invito) {
  var id = String(invito || '').trim();
  if (!id) return null;
  var tutte = righe_('Registro');
  for (var i = 0; i < tutte.length; i++) {
    if (String(tutte[i][0]).trim() === id) {
      return {
        invito: id,
        festeggiata: String(tutte[i][1] || ''),
        codice: String(tutte[i][2] || '').trim(),
        apertura: String(tutte[i][3] || '').trim(),
        riga: i + 2
      };
    }
  }
  return null;
}

function codiceGiusto_(reg, codice) {
  return reg && reg.codice !== '' && String(codice || '').trim() === reg.codice;
}

function nuovoId_() {
  return Utilities.getUuid().replace(/-/g, '').substring(0, 12);
}

/* ------------------------------------------------- arrivano i dati */

function doPost(e) {
  try {
    var r = JSON.parse(e.postData.contents);
    var reg = invitoRegistrato_(r.invito);
    if (!reg) return risposta_({ esito: 'errore', motivo: 'invito sconosciuto' });

    /* --- un messaggio anonimo ------------------------------------- */
    if (r.azione === 'salva' && r.tipo === 'messaggio') {
      var testo = testoPulito_(r.dati && r.dati.testo, 2000);
      if (!testo) return risposta_({ esito: 'errore', motivo: 'messaggio vuoto' });
      /* solo la data e il testo: nessun nome, nessuna mail, nessun indirizzo */
      foglio_('Messaggi', ['Invito', 'Quando', 'Messaggio'])
        .appendRow([reg.invito, Utilities.formatDate(new Date(), FUSO, 'dd/MM/yyyy'), testo]);
      return risposta_({ esito: 'ok' });
    }

    /* --- una conferma di presenza ---------------------------------- */
    if (r.azione === 'salva' && r.tipo === 'conferma') {
      var d = r.dati || {};
      var nome = testoPulito_(d.nome, 120);
      if (!nome) return risposta_({ esito: 'errore', motivo: 'nome vuoto' });

      /* se non ha già detto "sì, sono un altro", non si registra due volte */
      if (!d.forza && giaPresente_(reg.invito, nome).length) {
        return risposta_({ esito: 'doppione', simili: giaPresente_(reg.invito, nome) });
      }

      foglio_('Conferme', ['Invito', 'Id', 'Quando', 'Nome', 'Presente', 'Ospiti', 'Allergie', 'Note'])
        .appendRow([
          reg.invito,
          nuovoId_(),
          Utilities.formatDate(new Date(), FUSO, 'dd/MM/yyyy HH:mm'),
          nome,
          testoPulito_(d.presenza, 10),
          testoPulito_(d.accompagnatori, 4),
          testoPulito_(d.allergie, 300),
          testoPulito_(d.note, 500)
        ]);
      return risposta_({ esito: 'ok' });
    }

    /* --- "questo nome è già preso?" -------------------------------- */
    if (r.azione === 'controlla') {
      /* Torna solo i nomi uguali a quello chiesto, mai la lista intera:
         così non si può usare per sfogliare gli invitati. */
      return risposta_({ esito: 'ok', simili: giaPresente_(reg.invito, r.nome) });
    }

    /* --- la festeggiata cancella un invitato ----------------------- */
    if (r.azione === 'elimina') {
      if (!codiceGiusto_(reg, r.codice)) {
        return risposta_({ esito: 'errore', motivo: 'codice non valido' });
      }
      var f = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Conferme');
      if (!f || f.getLastRow() < 2) return risposta_({ esito: 'errore', motivo: 'niente da cancellare' });
      var v = f.getRange(2, 1, f.getLastRow() - 1, f.getLastColumn()).getValues();
      for (var i = 0; i < v.length; i++) {
        if (String(v[i][0]).trim() === reg.invito && String(v[i][1]).trim() === String(r.id || '').trim()) {
          f.deleteRow(i + 2);
          return risposta_({ esito: 'ok' });
        }
      }
      return risposta_({ esito: 'errore', motivo: 'invitato non trovato' });
    }

    return risposta_({ esito: 'errore', motivo: 'azione sconosciuta' });

  } catch (err) {
    return risposta_({ esito: 'errore', motivo: String(err) });
  }
}

function giaPresente_(invito, nome) {
  var cerca = nomeConfronto_(nome);
  if (!cerca) return [];
  var fuori = [];
  righe_('Conferme').forEach(function (riga) {
    if (String(riga[0]).trim() !== invito) return;
    if (nomeConfronto_(riga[3]) === cerca) {
      fuori.push({ nome: String(riga[3]), quando: String(riga[2]) });
    }
  });
  return fuori;
}

/* ------------------------------------------- la festeggiata legge */

function doGet(e) {
  try {
    var p = (e && e.parameter) || {};
    if (p.azione !== 'leggi') return risposta_({ esito: 'errore', motivo: 'azione sconosciuta' });

    var reg = invitoRegistrato_(p.invito);
    if (!reg) return risposta_({ esito: 'errore', motivo: 'invito sconosciuto' });
    if (!codiceGiusto_(reg, p.codice)) return risposta_({ esito: 'errore', motivo: 'codice non valido' });

    var messaggi = [], conferme = [];
    righe_('Messaggi').forEach(function (r) {
      if (String(r[0]).trim() === reg.invito) messaggi.push({ quando: String(r[1]), testo: String(r[2]) });
    });
    righe_('Conferme').forEach(function (r) {
      if (String(r[0]).trim() !== reg.invito) return;
      conferme.push({
        id: String(r[1]), quando: String(r[2]), nome: String(r[3]),
        presenza: String(r[4]), accompagnatori: String(r[5]),
        allergie: String(r[6]), note: String(r[7])
      });
    });

    var aperto = true, apreIl = '';
    if (reg.apertura) {
      var data = new Date(reg.apertura);
      if (!isNaN(data.getTime())) {
        aperto = new Date().getTime() >= data.getTime();
        apreIl = Utilities.formatDate(data, FUSO, "d/MM/yyyy 'alle' HH:mm");
      }
    }

    var fuori = {
      esito: 'ok', aperto: aperto, apreIl: apreIl,
      quanti: messaggi.length, conferme: conferme
    };

    if (aperto) {
      /* mescolati: così nemmeno l'ordine di arrivo dice chi ha scritto */
      for (var i = messaggi.length - 1; i > 0; i--) {
        var j = Math.floor(Math.random() * (i + 1));
        var t = messaggi[i]; messaggi[i] = messaggi[j]; messaggi[j] = t;
      }
      fuori.messaggi = messaggi;
    }
    return risposta_(fuori);

  } catch (err) {
    return risposta_({ esito: 'errore', motivo: String(err) });
  }
}

/* ---------------------------------------------------- prova veloce
   Premi "Esegui" su questa funzione dopo aver messo almeno una riga
   nel Registro: controlla che scrittura, doppioni e lettura funzionino.
------------------------------------------------------------------- */
function provaTutto() {
  var reg = righe_('Registro')[0];
  if (!reg) { Logger.log('Aggiungi prima una riga nella scheda Registro.'); return; }
  var invito = String(reg[0]).trim(), codice = String(reg[2]).trim();

  doPost({ postData: { contents: JSON.stringify({
    azione: 'salva', tipo: 'messaggio', invito: invito, dati: { testo: 'Prova, cancellami pure.' } }) } });

  Logger.log(doPost({ postData: { contents: JSON.stringify({
    azione: 'controlla', invito: invito, nome: 'Mario Rossi' }) } }).getContent());

  Logger.log(doGet({ parameter: { azione: 'leggi', invito: invito, codice: codice } }).getContent());
  Logger.log('Se vedi "esito":"ok" qui sopra, funziona tutto.');
}
