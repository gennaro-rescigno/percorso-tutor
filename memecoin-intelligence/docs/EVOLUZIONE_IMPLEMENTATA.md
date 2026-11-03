# Evoluzione implementata (fasi 0–9) — cosa fa ora il bot

Questo documento descrive ciò che è stato **costruito e verificato** dopo l'audit e la ricerca
([EVOLUZIONE_FASE1_FASE2.md](EVOLUZIONE_FASE1_FASE2.md)). Vincolo rispettato: **0 € di costi aggiuntivi**
(nessuna API a pagamento, nessun abbonamento, nessun modello AI nel ciclo operativo, nessuna transazione reale).

## 1. In una frase

Il bot ora legge **direttamente dalla blockchain Solana**, gratis e in tempo reale, ogni lancio e ogni operazione
di pump.fun, verifica da solo la sicurezza dei contratti, analizza i wallet dei primi acquirenti, fotografa ogni
lancio in istanti precisi, registra cosa succede davvero dopo 4 ore e misura con la statistica quali segnali
funzionano. Le novità vengono provate in **portafogli virtuali separati** e non entrano mai in produzione da sole.

## 2. Fonti dati (tutte gratuite)

| Fonte | Uso | Limiti e protezioni |
|---|---|---|
| WebSocket pubblico Solana (`logsSubscribe` sul programma pump.fun) | lanci, ogni compravendita, migrazioni | ~300 messaggi/s; l'80-88% sono transazioni fallite e vengono scartate senza decodifica. Il nodo pubblico chiude ogni iscrizione dopo ~15-25 s (misurato nella prova generale): il bot tiene **2 connessioni ridondanti** sfasate, elimina i doppioni per firma e si riconnette in 1 s; ogni interruzione reale (tutte le connessioni giù) viene registrata |
| IDL ufficiale pump.fun | formato esatto degli eventi e della curva | controllo settimanale automatico (workflow `memecoin contract check`) |
| RPC pubblico Solana | sicurezza del mint, stato della curva, wallet, simulazioni | budget per metodo al minuto, cache, pausa automatica sui 429; si possono aggiungere RPC gratuiti personali (file `data/secrets/rpc_urls`, mai pubblicato) |
| PumpPortal | solo nuovi token (gratuito) | le iscrizioni alle **operazioni** ora richiedono una chiave finanziata con SOL: **disattivate** (sostituite dallo stream blockchain) |
| Jupiter (chiave gratuita) | quote e transazioni di vendita per la simulazione | 1 richiesta/s |
| Jito (statistiche pubbliche) | tip floor | solo informativo |

## 3. Sicurezza propria (fase 2)

Il bot legge il **mint** del token e classifica ogni estensione Token-2022:

* **bloccanti** (critiche/alte): mint authority, freeze authority, delegato permanente, transfer hook attivo o
  attivabile, tassa sui trasferimenti, conti congelati di default, token non trasferibile, pausa,
  trasferimenti confidenziali, saldi modificabili, **estensioni sconosciute** (mai considerate sicure);
* **avvisi**: metadati modificabili, tassa attivabile in futuro, chiusura del mint.

Per i token classici legge anche i metadati Metaplex. **Il dato on-chain vale più di RugCheck**: se non sono
d'accordo, il bot usa la blockchain e lo scrive nel registro.

Inoltre: **simulazione di vendita** di un holder reale (Jupiter + `simulateTransaction`, gratuita, nulla viene
firmato). Risultato a tre stati: riuscita / bloccata dal token / non verificabile. Solo un blocco evidente del token
diventa un "fallimento"; tutto il resto resta "non verificato".

Scoperta reale (novembre 2026): i token pump.fun in **modalità "mayhem"** hanno un prezzo spinto da un agente di
pump.fun (la riserva virtuale cresce più dei SOL realmente pagati). Il bot li marca come **non organici**, non
calcola per loro un indice di opportunità e non li compra mentre sono sulla curva.

## 4. Wallet intelligence (fase 3)

Per i candidati migliori, il bot analizza i primi 20 acquirenti: chi li ha finanziati (prima transazione del
wallet), da quanto esiste il wallet, se il finanziatore è un "hub" (exchange/servizio con ≥ 1000 transazioni in 6 ore).
I **cluster** si formano solo da collegamenti di fatto:

* stesso finanziatore (non hub);
* finanziato dal creatore;
* finanziato da un altro dei primi acquirenti.

Nessun peso inventato. Limite dichiarato: i wallet finanziati tramite exchange o più passaggi non vengono collegati
(la quota coordinata è quindi una **stima per difetto**). Storico del creatore: lanci negli ultimi 30 giorni/24 ore,
migrazioni e crolli dei suoi token, dal **nostro** archivio (serve almeno un giorno di raccolta perché conti).

## 5. Caratteristiche della curva (fase 4)

Calcolate solo con le operazioni avvenute **fino a quel momento** (nessuno sguardo al futuro): acquirenti unici,
venditori, SOL comprati/venduti, pressione d'acquisto, acquisti nel blocco di creazione, sniper nei primi 3 slot,
comportamento del creatore, concentrazione, flipper, progresso e velocità della curva, distanza dal massimo,
acquirenti nell'ultimo minuto. Per ogni finestra il bot misura la **copertura** dello stream (quota del tempo in cui
almeno una connessione era attiva, salvata come `stream_coverage`): sotto il 97% i dati sono marcati **incompleti**
e non vengono usati (un'assenza di dati non è mai letta come "nessuna attività").

Per i token sulla curva, prezzo e candele da 1 minuto arrivano dallo stream (esatti, in tempo reale) e il bot
**risparmia GeckoTerminal** per gli altri token.

## 6. Feature store ed esiti reali (fase 1)

Ogni lancio (anche quelli che muoiono subito: niente survivorship bias) viene fotografato a **1, 5 e 15 minuti**.
Dopo **4 ore** si registra l'esito reale dalle candele dello stream: rendimento massimo/minimo/finale a 60 e 240
minuti, se ha **raddoppiato prima di dimezzarsi**, se è **crollato dell'80%** entro un'ora, se è migrato.
Conservazione: operazioni iniziali 3 giorni, candele dello stream 10 giorni, wallet 30 giorni, lanci e istantanee
etichettate 90 giorni.

## 7. Indici di rischio e opportunità (fase 6)

Due indici **separati** 0–100, spiegabili fattore per fattore. Ogni fattore vale 0 (ok), ½ (attenzione) o 1
(rischio/forte) con soglie di partenza convenzionali e **pesi uguali**. **Non sono probabilità** e lo dice la
dashboard. Un dato mancante abbassa la copertura, non migliora il punteggio; sotto il 50% di copertura l'indice è
"non determinabile". **L'opportunità non può mai superare la sicurezza.**

| Regola | Modalità | Effetto |
|---|---|---|
| ONCHAIN_SECURITY | applicata | blocca gli acquisti in tutti i portafogli |
| MAYHEM_CURVE | applicata | idem |
| SELL_SIM_FAILED | applicata | idem |
| HIGH_RISK_INDEX, COORDINATED_SUPPLY, CREATOR_SOLD, SERIAL_DEPLOYER | shadow | registrate; applicate solo nell'esperimento x_safe |

## 8. Esperimenti e cancello di promozione (fasi 7 e 9)

* **x_safe** — come il Laboratorio, ma salta i token segnalati dalle regole shadow: misura quanto valgono quelle regole.
* **x_curve** — nuova strategia **O · Curva organica**, sui lanci pump.fun tra 2 e 15 minuti di vita, con domanda
  ampia e indipendente. Parametri fissati in anticipo (versione 1) per un test fuori campione onesto. Esecuzione
  simulata sulla curva esatta di pump.fun (prodotto costante sulle riserve virtuali) con commissioni e priority fee.

Un esperimento è "promuovibile" solo con: ≥ 50 operazioni chiuse, ≥ 14 giorni, intervallo di confidenza al 95% del
rendimento medio sopra zero, meglio del Laboratorio con p < 0,05. **Anche allora il bot non cambia nulla da solo:
serve la tua approvazione esplicita.**

## 9. Ricerca (fase 9, senza autonomia sulle decisioni)

Ogni ora: AUC di ogni caratteristica (con intervallo di confidenza bootstrap) rispetto a "raddoppio" e "crollo",
verifica degli indici, regressione logistica **walk-forward** (addestrata sul passato, provata sul periodo
successivo), effetto delle regole shadow. Sotto 300 osservazioni o 30 casi positivi il verdetto è
**"dati insufficienti"**.

## 10. Esecuzione realistica (fase 5)

Priority fee misurata ogni 10 minuti (`getRecentPrioritizationFees` sul programma pump.fun) e tip floor Jito.
La simulazione usa `max(fee configurata, 75° percentile misurato)`, con un tetto di 0,005 SOL: le misure possono solo
rendere la simulazione **più prudente**.

## 11. Affidabilità (fase 0)

* pool RPC con budget, cache e failover; contatori visibili in "Salute del sistema";
* stream con riconnessione e registro delle interruzioni (anche dei riavvii del server);
* scrittura dei dati in blocco ogni 15 secondi; salvataggio finale allo spegnimento;
* **backup fuori dal server gratuito**: ogni ora il server pubblica lo stato essenziale (senza segreti) e ogni giorno
  il workflow `memecoin state backup` lo copia nel branch `bot-state` (con la copia del giorno prima).
  Ripristino su un server nuovo: `mci state-import --file state.json` (solo su database vuoto);
* controllo settimanale del formato ufficiale di pump.fun.

## 12. Dashboard

Nuove pagine: **Esperimenti**, **Lanci pump.fun live**, **Ricerca**, **Salute del sistema**; nella pagina di ogni
token la sezione **analisi on-chain** (indici con i fattori, sicurezza letta dalla blockchain, primi minuti sulla
curva, wallet e cluster con le prove, storico del creatore, istantanee e esiti). Telegram `/status` mostra lo stato
dello stream. I messaggi automatici restano solo acquisti e vendite del portafoglio principale.

## 13. Diario degli eventi, studio degli eventi e laboratorio delle regole (3 novembre 2026)

* **Diario di ogni lancio** (tabella `token_events`, conservata 30 giorni): dallo stesso stream gratuito, operazione
  per operazione, il bot annota i fatti con ora e prezzo: acquisti e vendite del creatore (anche "vende tutto"),
  acquirenti nel blocco 0, acquisti e vendite di almeno 2 SOL, wash trade atomici (stesso wallet compra e vende
  nella stessa transazione), soglie della riserva della curva (5, 10, 20, 40, 60, 80 SOL), cali dal massimo del 50% e
  dell'80%, picchi di acquisti, diploma, 30 minuti senza scambi, nomi già usati. Visibile nella pagina di ogni token.
* **Studio degli eventi** (ogni ora, pagina Ricerca): per ogni tipo di fatto, cosa è successo nei 60 minuti dopo
  (variazione mediana, quota che tocca +100% o −50%, quota che si diploma), confrontato con un momento qualsiasi
  della stessa età. Le finestre con lo stream interrotto sono escluse.
* **Laboratorio delle regole** (ogni ora, pagina Ricerca): 7 regole d'ingresso e 3 uscite **fissate il 3 novembre
  2026 prima di vederne i risultati**, applicate a ogni lancio osservato dopo quella data, con latenza, commissioni,
  priority fee e stop riempito a −60%. Verdetto "promettente" solo con almeno 300 casi fuori campione, intervallo
  di confidenza sopra zero e correzione per test multipli. Non cambia nulla da solo.
* **Studi storici gratuiti** sui runner di GitHub (workflow `memecoin historical study`): vedi
  [RICERCA_MERCATO_MEMECOIN.md](RICERCA_MERCATO_MEMECOIN.md), sezione 9.

## 14. Cosa NON è stato fatto, e perché

* **Trading reale**: resta disattivato (serve il tuo consenso esplicito).
* **Modifiche automatiche alla strategia di produzione**: vietate; solo esperimenti shadow con cancello statistico.
* **gRPC/Yellowstone, Helius a pagamento, PumpPortal con chiave finanziata, Birdeye, Bitquery, X/Twitter**: a pagamento.
* **Pesi "intelligenti" o modelli addestrati in produzione**: senza dati sufficienti sarebbero overfitting; il
  modulo di ricerca dirà quando (e se) i dati lo giustificano.
* **Copy-trading di "smart wallet"**: senza uno storico verificato dei loro risultati sarebbe una scommessa; i dati
  per valutarlo ora vengono raccolti (wallet e lanci).

## 15. Cosa aspettarsi

Nelle prime **4 ore** non ci sono esiti; nei primi **giorni** la ricerca dirà "dati insufficienti" (è corretto).
Con ~700 lanci all'ora, le 300 osservazioni minime per orizzonte arrivano in poche ore, ma i casi positivi (raddoppi
veri) sono rari: servono probabilmente **alcuni giorni** per conclusioni robuste e **settimane** per un verdetto sugli
esperimenti (50 operazioni chiuse). Nessun risultato positivo verrà dichiarato prima.
