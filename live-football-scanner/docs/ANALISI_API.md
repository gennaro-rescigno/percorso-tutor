# Analisi delle fonti dati (ottobre 2026)

> **Attenzione:** l'ambiente cloud in cui è stato sviluppato il progetto blocca, per policy di rete, tutti gli host
> dei provider sportivi (api-sports.io, the-odds-api.com, sportmonks.com, ESPN, SofaScore, FotMob,
> football-data.org/co.uk). Prezzi e limiti qui sotto vengono quindi da ricerche web, spesso **pagine di
> terze parti o di concorrenti**, e vanno verificati sulle pagine ufficiali prima di acquistare un piano.
> Lo script `backend/scripts/verify_live.py` misura sul campo, con le tue chiavi, cosa restituisce davvero ogni fonte.

## Confronto

| | API-Football (api-sports.io) | Sportmonks Football API | The Odds API | Altre |
|---|---|---|---|---|
| Partite live, eventi | Sì (`/fixtures?live=all`, eventi, rossi, cambi) | Sì | No (solo quote; punteggi in un endpoint a parte) | football-data.org: solo punteggi, top campionati |
| Statistiche live | Tiri, tiri in porta/fuori/respinti, in area, corner, possesso, falli, cartellini, parate, passaggi; **xG** (`expected_goals`) solo per alcuni campionati | Ricche, inclusi attacchi e attacchi pericolosi (da verificare per piano); xG live solo con l'add-on "xG Advanced" | No | — |
| Attacchi pericolosi, big chances, xGOT | **Non forniti** | Attacchi / attacchi pericolosi sì (da verificare); xG come add-on | No | — |
| Quote **in-play** | Sì, `/odds/live` (flag `stopped` / `blocked` / `main`; nessuno storico; la partita esce dal feed poco dopo la fine) | Sì, solo con l'add-on "Odds & Predictions" / Premium Odds | Sì per i mercati principali (h2h, totals, spreads), multi-bookmaker, REST senza streaming | Betfair Exchange API: quote e liquidità reali, serve un conto e una app key |
| Copertura | 1.100+ competizioni | Per piano: 5 / 30 / 120 campionati | ~50 campionati di calcio | — |
| Piano gratuito | 100 richieste/giorno | 2 campionati (Superliga danese, Premiership scozzese) | 500 crediti/mese | — |
| Piani a pagamento (fonti terze, da verificare) | Pro ~19 $/mese (7.500 req/giorno), Ultra ~29 $ (75.000/giorno), Mega ~39 $ (150.000/giorno) | Starter ~29 €/mese (5 campionati), Growth ~99 € (30), Pro ~249 € (120), più gli add-on quote e xG | 20K crediti ~30 $/mese, 100K ~59 $/mese, fino a ~249 $ | — |
| Costo di una chiamata | 1 richiesta | 1 richiesta | mercati × regioni crediti (`/sports` gratis) | — |

Fonti consultate: [getbruin.com, API-Football](https://getbruin.com/docs/ingestr/soccer-sources/api-football.html),
[oddspapi.io, alternativa ad API-Football](https://oddspapi.io/blog/?p=3128),
[guida ufficiale API-Football](https://www.api-football.com/news/post/how-to-get-started-with-api-football-the-complete-beginners-guide),
[Sportmonks, piani](https://www.sportmonks.com/football-api/plans-pricing),
[Sportmonks, xG](https://docs.sportmonks.com/v3/endpoints-and-entities/endpoints/expected-xg),
[Sportmonks, quote in-play](https://docs.sportmonks.com/v3/tutorials-and-guides/tutorials/odds-and-predictions/live-inplay-odds),
[sportsapis.dev, The Odds API](https://sportsapis.dev/apis/the-odds-api),
[oddspapi.io, limiti del piano gratuito di The Odds API](https://oddspapi.io/blog/the-odds-api-free-tier-limits).

## Scelta architetturale

1. **API-Football come fonte primaria.** È l'unica fonte economica che fornisce **dalla stessa sorgente** lo
   stato della partita, le statistiche e le quote in-play. Questo permette il controllo di coerenza più
   importante: il risultato e il minuto riportati dal feed quote devono coincidere con quelli del feed partita,
   altrimenti la quota è considerata non affidabile (gol appena segnato, mercato non ancora riprezzato).
2. **The Odds API come seconda fonte, opzionale.** Aggiunge più bookmaker su 1X2 e Over/Under. Non conosce lo
   stato della partita: le sue quote valgono solo se aggiornate *dopo* l'ultimo gol osservato. Viene interrogata
   al massimo ogni 120 s, perché i crediti costano.
3. **Sportmonks** è l'alternativa se servono attacchi pericolosi e xG live su molti campionati, ma con gli
   add-on il costo supera di parecchio quello di API-Football. Il codice è organizzato per provider
   (`app/providers/`), quindi aggiungerlo significa scrivere un solo modulo che produca gli stessi oggetti normalizzati.
4. **Escluse** le fonti non ufficiali (SofaScore, FotMob: termini d'uso, blocchi anti-bot) e quelle prive di dati live.
5. **StatsBomb Open Data** (gratuito, eventi con xG) è usato **solo per addestrare e validare** il modello.

## Consumo di richieste stimato (API-Football)

Ogni ciclo fa 1 chiamata `/fixtures?live=all`, poi `ceil(N/20)` chiamate `/fixtures?ids=` per statistiche ed
eventi, 1 chiamata `/odds/live` e fino a 4 chiamate per la forma delle squadre (in cache per 12 ore).
Con 60 partite live e un ciclo ogni 45 s: circa 6-9 richieste per ciclo, cioè 480-720 l'ora. Un sabato pieno
di calcio supera quindi le 7.500 richieste del piano Pro: **conviene il piano Ultra**, oppure limitare i
campionati con `LEAGUE_WHITELIST`. Lo scanner legge gli header di quota (`x-ratelimit-requests-remaining`),
sospende i download di forma sotto le 150 richieste residue e si mette in pausa per 10 minuti se riceve un errore di quota.

## Cosa non è disponibile (e non viene simulato)

* Attacchi pericolosi, big chances, xGOT, pressione offensiva "proprietaria": API-Football non li fornisce.
  La dashboard li elenca come mancanti.
* xG live: solo per alcuni campionati. Se manca si usa il modello basato su tiri, tiri in porta e corner,
  e la confidenza scende.
* Mercati con regole di liquidazione dipendenti dal bookmaker (handicap asiatico in-play "resto della partita",
  booking points, marcatori) non vengono proposti. Compaiono nell'elenco dei "mercati non mappati".
* Cartellini (Over/Under): esclusi per ora. Le regole su come contare il secondo giallo o il rosso diretto
  cambiano da bookmaker a bookmaker.
* "Gol nei prossimi 10 minuti": il modello lo calcola sempre e mostra la quota equa. Viene proposto come
  opportunità solo se il feed offre una quota verificabile su una finestra fissa di 10 minuti
  (ad esempio "Goal between 70:00 - 79:59").
