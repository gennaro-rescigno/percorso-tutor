# Motore di probabilità: modello e validazione

## 1. Idea

Per ogni minuto di gioco ancora da disputare, ciascuna squadra ha un'**intensità di gol** λ (gol al minuto),
stimata con una **regressione di Poisson (GLM, link logaritmico)**:

```
log λ_i(s) = β · x_i(s)        (s = minuto futuro, i = squadra che attacca)
```

Le variabili `x` sono le stesse in addestramento e in produzione (`backend/app/engine/features.py`):

| Gruppo | Variabili |
|---|---|
| Tempo | fasce 0-15 / 15-30 / 30-45 / 45-60 / 60-75 / 75-90, recupero 1° e 2° tempo |
| Punteggio *al minuto s* | svantaggio ≤-2 / -1, vantaggio +1 / ≥+2, interazioni "in svantaggio/vantaggio nel finale", gol totali |
| Contesto | casa/trasferta, superiorità/inferiorità numerica (rossi), forma pre-partita (attacco squadra, difesa avversaria) |
| Partita finora | ritmo di tiri, tiri in porta, (xG) cumulati per 90', con shrinkage verso la media |
| Ultimi 10' | tiri, tiri in porta, corner, (xG) degli ultimi 10', **interagiti con la distanza temporale** (0-5', 5-15', 15-30', >30'): la pressione recente pesa sui minuti vicini e svanisce dopo |

Tre varianti: `goals_context` (senza statistiche live), `goals_stats` (tiri / tiri in porta / corner, sempre
disponibili su API-Football), `goals_xg` (usata solo quando il feed fornisce xG live per entrambe le squadre).
Un quarto GLM con la stessa struttura stima l'intensità dei **calci d'angolo**. La sovradispersione dei corner
residui è gestita con una binomiale negativa (α stimato col metodo dei momenti).

## 2. Dalla λ alle probabilità dei mercati

Il punteggio evolve come una **catena di Markov** minuto per minuto: in ogni minuto la probabilità di gol
dipende dal punteggio in quel momento (chi è sotto spinge, chi è sopra gestisce). La distribuzione dei gol
residui si calcola **esattamente** con programmazione dinamica su 9×9 stati, senza rumore Monte Carlo
(impostazione alla Dixon & Robinson, 1998). Da questa distribuzione derivano Over/Under (anche linee asiatiche
.25/.75 e intere con rimborso), entrambe segnano, 1X2, doppia chance, draw no bet, gol squadra, risultato esatto,
mercati del 1° tempo e del 2° tempo, prossimo gol, gol in una finestra di 10 minuti e corner.

Il recupero non è noto in anticipo: la durata di ogni minuto oltre il 45' / 90' è pesata con la distribuzione
empirica del recupero nelle competizioni 2020-2024 (media ≈ 3,2' nel 1° tempo, ≈ 5,8' nel 2° tempo).

## 3. Incertezza e margine prudenziale

1. **Incertezza dei parametri.** La covarianza dei coefficienti è *robusta per cluster* (partita), perché i minuti
   della stessa partita non sono indipendenti. Si estraggono 200 vettori di coefficienti e si ripete il calcolo:
   si ottiene una distribuzione della probabilità; il **10° percentile** è il punto di partenza prudenziale.
2. **Errore di calibrazione fuori campione.** Al 10° percentile si sottrae il **peggior errore di calibrazione
   (ECE)** osservato in validazione per quella famiglia di mercati (minimo 1,5 punti).
3. `EV prudenziale = p_prudenziale × quota − 1` (con rimborsi / mezze vincite gestiti esattamente).

Una selezione viene mostrata solo se: quota ≥ 1,75, EV prudenziale ≥ 3%, vantaggio prudenziale ≥ 3 punti,
quota fresca (≤ 90 s) e non sospesa, risultato coerente tra feed quote e feed partita, statistiche live presenti,
incertezza non eccessiva, e **distanza dalla probabilità equa del mercato ≤ 18 punti** (oltre, si assume che il
mercato conosca qualcosa che il modello non vede: anomalia, esclusa).

La **confidenza** (alta / media / bassa) è un punteggio 0-100 sulla *qualità della stima* (completezza dei dati,
finestre recenti disponibili, ampiezza dell'intervallo, qualità di calibrazione della famiglia, accordo con il
mercato, freschezza della quota). Non è la probabilità che l'evento si verifichi.

## 4. Dati e suddivisione

Fonte: **StatsBomb Open Data** (eventi minuto per minuto con xG), scaricati da `training/statsbomb_download.py`.

| Insieme | Contenuto | Partite |
|---|---|---:|
| Addestramento | Premier League, La Liga, Serie A, Ligue 1 2015/16, partite **prima** del 1° marzo 2016 | 1.074 |
| Validazione temporale | stessi campionati, partite dal 1° marzo 2016 (tutte successive all'addestramento) | 443 |
| Validazione esterna | Mondiali 2018 e 2022, Europei 2020 e 2024, Copa América 2024, Coppa d'Africa 2023, Indian Super League 2021/22, Bundesliga (stagioni di una squadra) 2015/16 e 2023/24 | 497 |

Nessuna partita usata per stimare i coefficienti è usata per validarli. Per ogni partita di validazione si fanno
previsioni ogni 5 minuti e all'intervallo (≈ 18.000 istanti), confrontandole con quanto accaduto davvero.

## 5. Risultati fuori campione (log-loss: più basso è meglio)

Baseline = Poisson a intensità costante (solo tempo residuo, nessuna informazione sulla partita).

**Validazione temporale** (443 partite, 8.394 istanti)

| Evento | N | Freq. | Baseline | Contesto | +Tiri | +xG | ECE (+Tiri) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Almeno un altro gol | 8394 | 69.4% | 0.4828 | 0.4750 | 0.4729 | 0.4733 | 2.3% |
| Over 2.5 finale | 6923 | 42.4% | 0.5495 | 0.5491 | 0.5478 | 0.5489 | 2.2% |
| Entrambe segnano | 6605 | 38.5% | 0.5962 | 0.5848 | 0.5853 | 0.5854 | 1.1% |
| Casa segna ancora | 8394 | 52.8% | 0.5931 | 0.5839 | 0.5827 | 0.5823 | 2.9% |
| Gol nei prossimi 10' | 8394 | 25.4% | 0.5672 | 0.5614 | 0.5601 | 0.5603 | 1.3% |
| Gol prima dell'intervallo | 3812 | 47.0% | 0.6224 | 0.6227 | 0.6220 | 0.6220 | 3.3% |
| Gol nel 2° tempo | 6295 | 73.3% | 0.5387 | 0.5291 | 0.5267 | 0.5274 | 3.7% |
| Esito 1X2 (3 classi) | 8394 | — | 0.7399 | 0.7148 | 0.7106 | 0.7118 | 2.0% |
| Prossimo gol (3 classi) | 8394 | — | 0.9549 | 0.9209 | 0.9176 | 0.9189 | 2.3% |

**Validazione esterna** (497 partite, 9.602 istanti)

| Evento | N | Freq. | Baseline | Contesto | +Tiri | +xG | ECE (+Tiri) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Almeno un altro gol | 9602 | 67.4% | 0.5069 | 0.5064 | 0.5062 | 0.5056 | 3.9% |
| Over 2.5 finale | 8048 | 40.1% | 0.5583 | 0.5569 | 0.5569 | 0.5557 | 5.0% |
| Entrambe segnano | 7382 | 38.0% | 0.5892 | 0.5902 | 0.5859 | 0.5857 | 2.5% |
| Casa segna ancora | 9602 | 47.9% | 0.6092 | 0.6064 | 0.6025 | 0.6023 | 3.7% |
| Gol nei prossimi 10' | 9602 | 23.6% | 0.5470 | 0.5466 | 0.5464 | 0.5460 | 2.1% |
| Gol prima dell'intervallo | 4283 | 45.5% | 0.6374 | 0.6313 | 0.6311 | 0.6300 | 4.4% |
| Gol nel 2° tempo | 7170 | 69.5% | 0.5653 | 0.5677 | 0.5686 | 0.5673 | 4.3% |
| Esito 1X2 (3 classi) | 9602 | — | 0.7917 | 0.7689 | 0.7631 | 0.7633 | 2.0% |
| Prossimo gol (3 classi) | 9602 | — | 0.9706 | 0.9595 | 0.9548 | 0.9541 | 3.2% |

Corner residui (validazione esterna): media stimata 4,71 contro 4,67 osservata, errore di calibrazione 1,3-1,4%.

### Come leggerli, onestamente

* Il modello batte la baseline su quasi tutti gli eventi in entrambe le validazioni; i guadagni più netti sono
  su 1X2 e prossimo gol (dove contano punteggio, espulsioni e forza delle squadre). I miglioramenti sono
  **piccoli in assoluto**: il calcio è dominato dal caso, e un modello costruito su statistiche pubbliche non
  può pretendere di battere sistematicamente un mercato che vede le stesse informazioni.
* Le statistiche live aggiungono poco rispetto al contesto. Il segnale che regge è il **ritmo di tiri
  cumulato**; i conteggi degli ultimi 10' hanno coefficienti piccoli e per lo più non significativi. Il modello quindi
  **non premia automaticamente "la pressione"**, ed è ciò che i dati supportano.
* Eccezione: sulla validazione esterna, per "gol nel 2° tempo" la baseline fa leggermente meglio.
* **Il modello tende a sottostimare i gol** nelle competizioni recenti (ad esempio 80'-fine: 18,6% stimato contro
  23,8% osservato). La causa principale è il recupero più lungo dal 2022; in produzione si usa la distribuzione
  del recupero moderna, ma il margine prudenziale (5 punti sui totali) resta alto proprio per questo.
* La valutazione economica (ROI, yield, CLV) **non è possibile sullo storico**, perché non esiste un archivio
  gratuito di quote in-play. Il sistema la misura in avanti, su ogni opportunità registrata (pagina
  "Storico & performance").

## 6. Limiti noti

* Coefficienti stimati sulla stagione 2015/16 dei top campionati. Su campionati minori, giovanili o femminili il
  modello si appoggia di più alla forma pre-partita e lo segnala con una confidenza più bassa.
* Le definizioni di "tiro" e "tiro in porta" di API-Football e di StatsBomb sono simili ma non identiche.
* Non modellati: infortuni, sostituzioni, motivazioni di classifica, meteo, nuove espulsioni future.
* Per le stagioni "di una squadra" (Bundesliga) la selezione non è casuale: sono usate solo per validare.

Per riaddestrare: `cd backend && python -m training.statsbomb_download && python -m training.train`
(circa 10 minuti; il file `models/inplay_model.json` contiene coefficienti, covarianze, report di validazione e margini).
