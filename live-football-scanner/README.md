# Live Football Intelligence Scanner

Sistema che individua automaticamente le partite di calcio **in corso**, ne analizza statistiche e
andamento, stima con un modello statistico validato la probabilità di ogni mercato quotato e mostra **solo**
le selezioni con quota ≥ 1,75 ed Expected Value positivo *dopo* un margine di errore prudenziale.
Se nessuna selezione supera i filtri, la dashboard lo dice: **NESSUNA OPPORTUNITÀ CON EDGE STATISTICO SUFFICIENTE.**

> Strumento di analisi statistica, non un consiglio di scommessa. Le quote dei bookmaker incorporano un margine
> e molte informazioni: un vantaggio stimato può essere un errore del modello. Il gioco è vietato ai minori e
> può causare dipendenza.

## Avvio rapido

Requisiti: Python 3.11+, Node 18+ (solo per compilare la dashboard), una chiave **API-Football**.

```bash
cd live-football-scanner
cp .env.example .env          # inserisci API_FOOTBALL_KEY (e, se vuoi, THE_ODDS_API_KEY)
./run.sh                      # installa, compila la dashboard e avvia su http://127.0.0.1:8000
```

Per verificare che i dati live arrivino davvero dalle API (4 richieste API-Football):

```bash
cd backend && python -m scripts.verify_live
```

Lo script stampa le partite live del momento, quali statistiche sono presenti (xG compreso), quante quote
in-play sono state normalizzate, i mercati esclusi e la quota residua del piano, poi salva un report JSON in
`backend/data/`. Se una chiamata fallisce, il controllo risulta **FAIL** e nessun dato viene sostituito.

Sviluppo con hot reload: `uvicorn app.main:app --reload` in `backend/` e `npm run dev` in `frontend/`
(apri http://localhost:5173; le chiamate `/api` e `/ws` vengono inoltrate a FastAPI).

## Come funziona

```
API-Football ──┐  partite live · eventi · statistiche · quote in-play · forma
The Odds API ──┤  (opzionale) quote multi-bookmaker
               ▼
   Scanner (ogni 30-60 s) ──► SQLite / PostgreSQL
     1. snapshot delle statistiche   → finestre ultimi 5 / 10 / 15 minuti
     2. quote normalizzate           → solo mercati con regole di liquidazione univoche
     3. modello in-play              → intensità di gol e corner per minuto + catena di Markov sul punteggio
     4. motore di valore             → probabilità implicita ed equa, EV, EV prudenziale, filtri, confidenza
     5. ciclo di vita                → nuova / aggiornata / non più valida (con motivo)
     6. liquidazione                 → esito, profitto, calibrazione (backtesting in avanti)
               ▼
   FastAPI (REST + WebSocket) ──► Dashboard React
```

| Cartella | Contenuto |
|---|---|
| `backend/app/providers/` | client API-Football e The Odds API, normalizzazione dei mercati |
| `backend/app/engine/` | variabili del modello, previsione (catena di Markov), mercati e liquidazione, EV e confidenza, spiegazioni |
| `backend/app/services/` | scanner, costruzione dello stato live dagli snapshot, backtesting |
| `backend/training/` | download StatsBomb, costruzione del dataset, stima GLM (cluster-robusta), validazione |
| `backend/models/inplay_model.json` | modello addestrato (coefficienti, covarianze, report di validazione, margini) |
| `frontend/` | dashboard React + TypeScript (Vite) |
| `docs/ANALISI_API.md` | confronto tra provider, costi, limiti, scelte |
| `docs/MODELLO.md` | modello statistico, validazione e limiti |

### Formule

* Probabilità implicita = 1 / quota. Probabilità equa = quote del bookmaker senza margine (normalizzazione proporzionale).
* EV = p × quota − 1 (con rimborsi e mezze vincite calcolati esattamente per linee intere e asiatiche).
* p prudenziale = 10° percentile della probabilità sotto l'incertezza dei parametri − errore di calibrazione
  fuori campione della famiglia di mercato. EV prudenziale = p prudenziale × quota − 1.

### Filtri obbligatori (tutti configurabili in `.env`)

Quota ≥ 1,75 · EV prudenziale ≥ +3% · vantaggio prudenziale ≥ 3 punti · quota aggiornata da ≤ 90 s e non sospesa ·
risultato del feed quote uguale a quello del feed partita · statistiche live presenti · non prima del 5' e non
oltre l'88' · incertezza del modello non eccessiva · distanza dal prezzo equo del mercato ≤ 18 punti
(oltre: anomalia, esclusa).
Un'opportunità viene **subito** rimossa se la quota scende sotto 1,75, se il mercato viene sospeso, se cambia il
risultato o se la partita finisce. Se invece l'EV oscilla attorno alla soglia, viene rimossa dopo due cicli
consecutivi sotto soglia. Le opportunità rimosse restano visibili, con il motivo, in "Opportunità non più valide".

## Dashboard

* **Dashboard live**: partite live, numero di opportunità, ultimo aggiornamento, quota API residua; filtri per
  campionato, quota minima, minuto, mercato e confidenza; classifica delle opportunità con probabilità stimata,
  prudenziale, implicita ed equa, EV, confidenza, motivazioni statistiche e fattori di rischio.
* **Dettaglio partita**: statistiche a confronto, dati disponibili e mancanti, finestre 5/10/15', andamento dei
  tiri, forma (ultime 10, casa/trasferta, Over 1.5/2.5/3.5, entrambe a segno), output del modello con quote
  eque, e tutte le quote valutate con il motivo di ogni esclusione.
* **Storico & performance**: % vinte, profitto, yield, ROI sul bankroll, EV atteso contro realizzato, CLV,
  drawdown, curva del profitto e calibrazione, suddivisi per mercato, campionato, fascia di quota e confidenza.
* **Modello & validazione**: metriche fuori campione, calibrazione, margini e coefficienti.
* **Fonti dati**: stato dei provider, quote residue, registro di ogni chiamata API (prova di provenienza dei
  dati) e mercati del feed non mappati.

## API del backend

| Endpoint | Descrizione |
|---|---|
| `GET /api/state` · `WS /ws` | stato live (partite, opportunità attive, invalidate, stato provider) |
| `GET /api/fixtures/{id}` | analisi completa di una partita |
| `GET /api/opportunities?status=` | storico opportunità |
| `GET /api/backtest` | metriche di performance e calibrazione |
| `GET /api/model` | modello, validazione, coefficienti |
| `GET /api/provider-log` | registro delle chiamate ai provider |
| `GET /api/health` · `POST /api/scan` | stato del sistema · scansione immediata |

## Test

```bash
cd backend && python -m pytest -q
```

I test coprono: coerenza delle distribuzioni, linee asiatiche, draw no bet, formula dell'EV (esempio
quota 2,00 e p = 58% → +16%), de-vig, parser API-Football e The Odds API sui formati documentati,
riconoscimento dei mercati, e un **ciclo completo dello scanner** su un trasporto HTTP simulato *solo nel test*
(rilevazione, invalidazione sotto 1,75, liquidazione e backtest).

## Stato della verifica

* Componenti verificati in sviluppo: training e validazione su 2.014 partite reali StatsBomb; 14 test superati;
  server FastAPI avviato con tutti gli endpoint che rispondono; dashboard compilata e controllata nel browser
  (tema chiaro e scuro, larghezza mobile, nessun errore in console).
* **Non ancora verificato: la ricezione di dati live reali.** L'ambiente di sviluppo non aveva chiavi API e la
  sua policy di rete blocca gli host dei provider (risposta `403` dal proxy, mostrata in modo esplicito dalla
  dashboard e da `verify_live.py`). Il primo passo sulla tua macchina è eseguire `python -m scripts.verify_live`
  con la tua chiave.
* Il formato di `/odds/live` è implementato secondo la documentazione pubblica. I nomi dei mercati sono
  riconosciuti con regole prudenti: dopo il primo avvio controlla in "Fonti dati" i mercati non mappati e, se
  serve, aggiungi le regole in `backend/app/providers/market_map.py`.
* PostgreSQL è supportato tramite SQLAlchemy (`DATABASE_URL`) ma è stato provato solo SQLite.

Dati di addestramento: StatsBomb Open Data (https://github.com/statsbomb/open-data), con attribuzione a StatsBomb.
