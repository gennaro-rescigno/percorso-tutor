# Ricerca sul mercato delle memecoin Solana — base di conoscenza

Data: 3 novembre 2026. Fonti lette integralmente (testo salvato nel branch `research-sources`, scaricato dal
workflow `memecoin research fetch`) più ricerche mirate. Per ogni dato indico la fonte e quanto è affidabile:
**[peer]** studio scientifico (preprint arXiv o conferenza), **[dati]** analisi su dati on-chain di aziende o
ricercatori indipendenti, **[vend]** materiale di chi vende un prodotto (da prendere con cautela),
**[nostro]** misurato dal nostro bot.

---

## 1. Il quadro in 10 punti

1. **Comprare "tutto" dopo il lancio perde soldi, sempre.** Comprando ogni token negoziabile 30 minuti dopo il
   lancio con costi realistici si perde in media il 31% dopo 1 ora, il 62% dopo 6 ore e il 56% dopo 24 ore. Solo
   l'1,3% raddoppia al netto dei costi. Anche a costo zero la perdita a 6 ore è del 59%. Nessuna delle 416
   strategie provate (filtri, ritardi, uscite, trailing stop) era significativamente positiva **[dati, Arrow Algo]**.
2. **Il 74% di chi compra memecoin perde SOL**: perdita mediana 13 $, 269 milioni di dollari persi in 10 settimane.
   Il miglior 1% degli acquirenti prende il 56% dei guadagni, il miglior 10% il 95%, e i bot "sandwich" vincono
   ogni settimana **[dati, Bitquery]**. Il dato CoinGecko "73% in profitto" (aprile 2026) misura solo chi ha già
   chiuso, con guadagni piccoli, ed è gonfiato dall'abbandono dei perdenti **[dati]**.
3. **I primi secondi appartengono agli addetti ai lavori.** Nel 38% dei lanci qualcuno diverso dal creatore compra
   già nel blocco 0; nel 21% il creatore compra con più wallet nello stesso "bundle" (mediana: il 10% dei token).
   I creatori e i loro bundle hanno incassato almeno 579 milioni di dollari, i bot sniper 31,5 milioni. **Il
   creatore vende entro il primo minuto nel 65% dei token** **[dati, Bitquery su 8,2 milioni di token]**.
   Il nostro dato: il creatore vende entro 5 minuti nel 61% dei lanci **[nostro]**.
4. **Solo lo 0,6–1% dei token si diploma** (riempie la curva e passa su PumpSwap) **[peer + dati]**. Circa un
   diploma su quattro è "costruito" da bot in meno di 60 secondi (mediana 6 acquirenti). I diplomi organici hanno
   in mediana 312 acquirenti e 853 operazioni e si diplomano in 9,8 minuti **[dati, PumpFunData]**.
5. **Dopo il diploma il prezzo crolla spesso subito.** Nei primi 10 minuti dopo il diploma il 38% tocca −80%, il
   63% scende del 40% dal massimo, solo il 15% tocca 2x. La grossa vendita che fa crollare il pool arriva in
   mediana 2,2 minuti dopo il diploma **[dati, Launchtape su 2.193 diplomi]**.
6. **La maggior parte muore in un giorno**: l'89% è di fatto morto entro 24 ore; il numero di wallet distinti nei
   primi 5 minuti è il miglior predittore di sopravvivenza (AUC 0,67 fuori campione) **[dati, GitHub
   memecoin-survival]**.
7. **La manipolazione è la norma, non l'eccezione.** Almeno il 17% delle transazioni sono wash trading e almeno il
   10% dei token sono copie. Il wash trading *aumenta* la probabilità di diploma (2,0% contro 0,9%) perché porta il
   token in prima pagina **[peer, Meme Coin Factories, 15 milioni di token]**. L'82,8% delle memecoin con
   rendimento oltre +100% mostra segni di crescita artificiale; il 62,9% dei pump-and-dump e dei rug era stato
   preceduto da wash trading **[peer, USENIX Security 2026]**. In media il 36,5% della supply è in mano a conti
   coordinati che sembrano indipendenti **[peer, MELT]**.
8. **Seguire i "call" degli influencer fa perdere**: chi compra 30 secondi dopo un call perde in mediana il 27,6% a
   5 minuti; c'è chi compra prima del call e vende dopo nel 72,6% dei casi **[dati, Substack, 770 call]**. Anche i
   migliori trader della classifica settimanale di pump.fun raddoppiano solo nel 40–67% dei loro call, e la media è
   gonfiata da pochi casi estremi **[vend, Xanguard]**.
9. **Copiare gli "smart wallet" non è dimostrato redditizio**: solo il 26% dei grandi guadagni dei wallet vincenti
   viene da trading "normale"; il 51% viene dalla vendita di token ricevuti per trasferimento (cioè addetti ai
   lavori) **[dati, Bitquery]**.
10. **La velocità è un'arma che non abbiamo gratis**: gli sniper professionali usano server dedicati, gRPC e
    bundle Jito per stare nel blocco 0 (meno di 0,4 secondi). Il nostro stream pubblico arriva con secondi di
    ritardo. **Qualunque strategia "corriamo per primi" è persa in partenza**: dobbiamo lavorare su orizzonti di
    minuti o ore, dove contano la selezione e la disciplina, non i millisecondi.

---

## 2. Il ciclo di vita di un token pump.fun (con i numeri)

| Fase | Cosa succede | Numeri |
|---|---|---|
| Creazione | Il creatore lancia il token (supply 1 miliardo, 2 miliardi in modalità "mayhem"); spesso compra subito, a volte con più wallet nello stesso bundle Jito | ~12 lanci al minuto (nostro stream); bundle del creatore nel 21% dei lanci |
| Blocco 0 / primi secondi | Sniper e bundle comprano prima che il token sia visibile sul sito | Acquisti di altri nel blocco 0: 38% dei token |
| Primo minuto | Il creatore vende spesso subito | Vendita del creatore entro 1 minuto: 65% |
| Curva | Prezzo su prodotto costante (30 SOL virtuali); commissione 1,25% (di cui 0,30% al creatore) | Un quarto arriva a 5 SOL nella curva, meno di uno su dieci a 20 SOL |
| Diploma | Con ~85 SOL reali la curva si chiude e nasce un pool PumpSwap (commissione ~0,25%); dal 2026 circa il 20% della liquidità di migrazione compra e brucia token nei primi 5 minuti ("BOOST") | 0,6–1% dei lanci; mediana 4–10 minuti per i diplomi organici |
| Primi 10 minuti dopo il diploma | Prese di profitto e grossi "dump" | 38% tocca −80%; 15% tocca 2x |
| Primo giorno | Quasi tutti muoiono; "precipizio delle 24 ore" | 79–89% morti o inattivi dopo un giorno |
| Lungo periodo | Pochissimi sopravvivono sopra il prezzo di lancio | 5 su 151 memecoin campionate sopra il prezzo di lancio (Talos) |

**Modalità mayhem** (da novembre 2025): un agente di pump.fun compra e vende in modo casuale per 24 ore con un
miliardo di token in più; quelli non usati vengono bruciati. Dai nostri dati: le operazioni dell'agente sono il
predittore più forte di crollo (AUC 0,86) **[nostro]**. Il bot li esclude.

---

## 3. Gli attori e le loro tattiche

- **Creatore / dev**: compra all'inizio, spesso con più wallet (bundle) per nascondere la concentrazione; vende
  presto. Tattiche: offuscare l'indirizzo del creatore (creare con un wallet e finanziarlo da altri), lanci in
  serie, copie di nomi di successo.
- **Sniper**: bot che comprano nei primi blocchi e rivendono ai ritardatari. Le coorti di sniper persistenti
  (1.012 "anelli" di wallet) sono associate a un +16% di acquirenti nella prima mezz'ora, ma l'effetto sui SOL
  investiti non è distinguibile da zero **[peer]**.
- **Squadre di wallet veloci** (cabal): gruppi di pochi wallet che comprano insieme. Sono associati a una
  probabilità 2–4 volte maggiore di arrivare a 20 SOL, ma **non** di diplomarsi, e non aggiungono informazione a
  quella già visibile dallo stato della curva **[peer]**.
- **Wash trading**: lo stesso indirizzo compra e vende la stessa quantità nella stessa transazione (regola WT1,
  impossibile dal sito: richiede contratti propri). Coinvolge l'8,26% dei token; più wash trading porta più
  probabilità di diploma (raddoppiare il wash trading porta +19% di probabilità) **[peer]**.
- **Vendite coordinate** (regola DP1/DP2): più indirizzi comprano, trasferiscono i token a un solo indirizzo che
  vende tutto insieme (mediana 7 mittenti) **[peer]**.
- **Copie**: lo stesso nome o simbolo di un token di successo. Gli originali si diplomano nel 9,2% dei casi, le
  copie nello 0,86%; ma il 17,7% dei diplomati è una copia **[peer]**.
- **Social**: i lanci che dichiarano un canale Telegram si diplomano 8,9 volte più spesso nei primi minuti
  (Cox HR 5,40) — ma lo studio è stato corretto più volte e il risultato vale come direzione, non come numero
  preciso **[peer, con riserva]**. Un market cap iniziale sopra il default (grosso primo acquisto del creatore) è
  il predittore singolo più forte (HR 4,51).
- **Influencer / call channel**: comprano prima del call e vendono ai seguaci **[dati]**.
- **Boost a pagamento su DexScreener**: aneddoticamente salita seguita da lento crollo; non esistono studi solidi
  **[vend]**.
- **Market-Manipulation-as-a-Service**: strumenti venduti per fare tutto questo senza competenze tecniche **[peer]**.

---

## 4. Cosa mostrano i bot e i terminali più usati

| Strumento | Ruolo | Funzioni |
|---|---|---|
| Axiom | terminale web, ~45% del volume spot Solana (giugno 2026) | scoperta token, migration sniper, ordini limite, wallet tracker |
| GMGN | analisi | smart money, verifica quota del dev, insider, bundle, sniper, "hot pumps", anti-MEV |
| Photon | terminale web leggero | scoperta rapida, trading |
| Trojan / BonkBot / Maestro | bot Telegram | sniper al lancio e alla migrazione, copy trading (fino a 40 wallet), DCA, protezione MEV |
| BullX | terminale | ha sospeso il trading a giugno 2026 |

Gli indicatori che tutti mostrano: **quota dei primi 10 holder, quota del dev, sniper, insider, bundle, wallet
nuovi, numero di holder, smart money**. Il nostro bot li calcola già quasi tutti dai dati gratuiti della
blockchain. Quello che non possiamo replicare gratis è la velocità (server dedicati, gRPC, bundle Jito) e le
etichette proprietarie dei wallet.

---

## 5. I segnali con un minimo di evidenza

| Segnale | Direzione | Forza dell'evidenza |
|---|---|---|
| Molti wallet distinti e molte operazioni nei primi minuti | più sopravvivenza; nei nostri dati più probabilità di raddoppio (AUC 0,79) | buona, replicata |
| Prezzo già salito molto a 5 minuti | **meno** probabilità di raddoppiare dopo (AUC 0,22) | nostro, da replicare |
| Token già sceso dal massimo a 5 minuti, con molta attività | più probabilità di raddoppio (AUC 0,82) | nostro, da replicare |
| Curva riempita molto in fretta | più crolli (AUC 0,73) | nostro, da replicare |
| Mayhem / operazioni dell'agente | più crolli (AUC 0,86) | nostro, forte |
| Grosso primo acquisto del creatore | più diplomi (HR 4,51) | peer |
| Canale Telegram dichiarato | più diplomi (fino a 8,9x nei primi minuti) | peer, con riserva |
| Wash trading atomico (WT1) | più diplomi | peer |
| Token copia (non il primo con quel nome) | meno diplomi | peer |
| Il creatore detiene ancora più del 5% al diploma | **meno** −80% (33,6% contro 47,4%) | dati, controintuitivo |
| Diplomi in meno di 60 secondi con pochi acquirenti | diploma "costruito" da bot | dati |

Attenzione: un segnale che predice il diploma o la sopravvivenza **non** è automaticamente redditizio. Dopo costi,
slittamento e crolli nei primi minuti, quasi tutti i vantaggi spariscono (punto 1). Per questo ogni idea va
verificata con i rendimenti netti e fuori campione.

---

## 6. Dove può stare un vantaggio realistico per noi

1. **Evitare, prima ancora che scegliere.** Il miglior contributo provato è ridurre le perdite: MELT riduce le
   perdite fino a 34 punti percentuali escludendo i lanci ad alto rischio. Escludere mayhem, copie, bundle grossi,
   diplomi costruiti dai bot e creatori seriali è un vantaggio reale e misurabile.
2. **Orizzonti dove la velocità non conta**: da 5 minuti a qualche ora dopo il lancio, oppure dopo il primo crollo
   post-diploma, quando i bot veloci hanno già fatto il loro giro.
3. **Uscite rapide e disciplinate**: quasi tutto succede nei primi minuti; tenere a lungo è statisticamente
   perdente (il 67% è morto entro 6 ore).
4. **Statistica onesta**: con centinaia di ipotesi qualcuna sembrerà vincente per caso. Ogni strategia va
   corretta per test multipli (Bonferroni / false discovery rate) e verificata su periodi diversi (giugno-luglio,
   settembre-ottobre, novembre dal vivo) prima di fidarsi.

---

## 7. Ipotesi da mettere alla prova (registrate prima di guardare i risultati)

| Codice | Ipotesi | Perché |
|---|---|---|
| H1 "dip attivo" | Lanci con molta attività a 5–15 minuti ma già scesi dal picco, esclusi mayhem e copie | Nostri dati (AUC 0,82); evita di comprare in cima |
| H2 "post-diploma" | Entrare dopo il primo grande dump post-diploma (2–10 minuti), solo diplomi organici (>100 acquirenti), uscita entro 30 minuti | I bot veloci hanno già venduto; diplomi organici più robusti |
| H3 "evitare e basta" | Stesse strategie esistenti con un filtro anti-manipolazione (mayhem, copie, bundle >20%, diplomi in <60 s) | Ridurre le perdite è il vantaggio più documentato |
| H4 "creatore fermo" | Token in cui il creatore non ha venduto e detiene ancora una quota | Dato Launchtape controintuitivo da verificare |
| H5 "social" | Lanci con Telegram/sito dichiarati e prima attività organica | Effetto social (con riserva) |

Ogni ipotesi viene prima verificata sui **dataset storici gratuiti** e poi, se sopravvive, provata **dal vivo in un
portafoglio virtuale separato**, con il cancello statistico (almeno 50 operazioni, 14 giorni, intervallo di
confidenza sopra zero, correzione per test multipli). Nessuna entra nel portafoglio principale senza la tua
approvazione.

---

## 8. Dataset storici gratuiti

| Dataset | Licenza | Contenuto | Periodo |
|---|---|---|---|
| jocry/Pumpfun_Memecoin_Corpus | MIT | 798.430 lanci, 33,6 milioni di operazioni, stato della curva ogni 15 s, esiti post-diploma | 5 giugno – 14 luglio 2026 |
| loopholetape/pumpfun-launches | CC BY 4.0 | 2,3 milioni di lanci con esito (diploma, rug), caratteristiche del primo minuto, primi 30 minuti di 39.967 pool PumpSwap | 31 agosto – 27 ottobre 2026 |
| bryceweiner/fly-trader-seed | MIT | candele al minuto PumpSwap con flussi, wallet e dati di lancio | aprile – settembre 2026 |
| AratiKamat/red-pump-2026 | CC BY 4.0 | 860.213 lanci con esito (attenzione: etichette distorte dal metodo di raccolta, documentato dagli autori) | maggio – giugno 2026 |
| launchtape/solana-launch-tape | licenza propria | campione gratuito di 2 ore di tutte le operazioni su curva e PumpSwap | ottobre 2026 |

Si analizzano sui runner gratuiti di GitHub (non sul server, per non rallentare il bot).

---

## 9. Risultati dei nostri studi storici (3 novembre 2026)

Eseguiti sui runner gratuiti di GitHub (workflow `memecoin historical study`), risultati completi nel branch
`research-results` (`loop_curve.md`, `postgrad.md`). Le regole sono state scritte **prima** di vedere i risultati
(il testo della pre-registrazione è in testa a ogni rapporto) e i costi sono inclusi.

### 9.1 Cosa succede ai lanci (loopholetape, 1,36 milioni di lanci "classici", 31 agosto – 27 ottobre)

| Fatto | Settembre | Ottobre |
|---|---|---|
| Lanci classici che si diplomano | 3,56% | 2,79% |
| Diplomi avvenuti entro 1 minuto dal lancio (quasi sempre costruiti da bot/bundle) | 75,6% | 66,7% |
| Lanci in cui il creatore vende | 66,6% | 67,6% |
| Tempo mediano alla prima vendita del creatore | 22 s | 16 s |
| Curve che arrivano almeno a 20 SOL reali | 12,0% | 10,9% |
| Il creatore non compra all'inizio: diplomi / rug | 0,89% / 9,6% | 0,54% / 8,4% |
| Il creatore compra più di 5 SOL: diplomi / rug | 33,0% / 66,5% | 23,9% / 76,7% |
| Più di 10 wallet "bundle" nei primi 10 s: diplomi / rug | 21,3% / 79,1% | 13,9% / 85,8% |
| Creatore al primo lancio: diplomi | 3,0% | 6,2% |
| Creatore con oltre 50 lanci precedenti: diplomi / rug | 1,25% / 88,2% | 0,85% / 66,6% |
| Nome già usato da un lancio precedente (oltre la 6ª volta): diplomi | 5,4% | 3,9% |

Lettura: i lanci che si diplomano di più sono quelli con **grandi acquisti iniziali del creatore e molti wallet
bundle**, cioè i diplomi "costruiti" che avvengono in pochi secondi e su cui un bot gratuito non può arrivare in
tempo. Gli stessi lanci hanno anche i tassi di rug più alti.

### 9.2 Comprare sulla curva e tenere fino al diploma (o alla morte della curva)

Idea verificata: sulla curva il prezzo non può scendere sotto il prezzo iniziale, quindi la perdita massima è
limitata, mentre il diploma vale molte volte il prezzo d'ingresso. **Risultato: perde sempre.** Su 2,2 milioni di
istantanee di 547.350 token, per ogni combinazione di età (da 0 a 15 minuti) e riserva della curva (da 0 a 85 SOL)
la quota di token che si diplomano è circa **la metà** di quella necessaria per andare in pari. Esempi: con
riserva tra 20 e 40 SOL si diploma il 15% (servirebbe il 30%); tra 40 e 85 SOL il 48% (servirebbe il 75%).
Le 7 regole pre-registrate (anche con filtri su creatore, insider, bundle, attività) perdono tutte tra il **13% e
il 25% per operazione**, con intervalli di confidenza interamente negativi e lo stesso risultato in entrambe le
metà del periodo. Il mercato "prezza" correttamente la probabilità di diploma, e le commissioni fanno il resto.

### 9.3 Comprare dopo il diploma (jocry giugno-luglio, 5.669 diplomi; loopholetape settembre-ottobre, 27.096 pool)

- Dopo 30 minuti dall'apertura del pool il prezzo mediano è al **2% del prezzo iniziale**; il 58,9% dei pool
  finisce sotto il 10% del prezzo iniziale, e chi tocca quel livello lo fa in mediana dopo 8,6 minuti.
- In giugno-luglio a 30 minuti dal diploma la mediana è ×0,58 e il 37% è già sotto ×0,2.
- 36 combinazioni pre-registrate (entrata a 1/5/10/30 minuti, tenuta 1/6/24 ore, quattro filtri): **nessuna
  positiva e stabile**. Le medie sono dominate da pochi casi estremi (e cambiano segno tra la prima e la seconda
  metà del periodo), le mediane sono fortemente negative (da −4% a −92%). Anche "ha retto il primo crollo" perde
  (−6% a 1 ora, intervallo interamente negativo); "diploma organico" non aiuta.

### 9.4 Entrate a breve termine sulla curva (loopholetape, 330.000 token tra 1 e 5 minuti di vita)

Sei regole pre-registrate (qualsiasi momento, slancio, ritracciamento, ritracciamento forte, flusso di acquisti,
ritracciamento + flusso) con uscita dopo 1, 3 o 10 minuti: **18 combinazioni su 18 perdono** (dal −8% al −16% per
operazione con i costi) e **perdono anche senza costi** (dal −1,5% al −10%): nei primi minuti il prezzo tende a
scendere, qualunque sia il segnale. Comprare dopo una forte salita ("slancio") è il peggio (−10% lordo a 3 minuti);
comprare dopo un ritracciamento non è meglio della media. Nota: nei nostri dati di novembre un ritracciamento con
molta attività è associato a più raddoppi (AUC 0,82), ma questo non basta a rendere positivo il rendimento medio,
perché i raddoppi restano pochi e le perdite degli altri pesano di più. Le regole R1, R2 e R6 del laboratorio
(ritracciamento + attività) verificheranno lo stesso dal vivo: lo storico fa prevedere che non funzioneranno.

### 9.5 I wallet che guadagnano: esiste un'abilità? Si può copiare? (jocry, giugno-luglio, 23,4 milioni di operazioni)

- Su 574.000 wallet solo il **27,9% è in guadagno** sulle curve; i perdenti perdono in totale 356.049 SOL, i
  vincenti guadagnano 193.625 SOL (la differenza va in commissioni, ai creatori, esclusi dal conteggio, e a operazioni
  che il corpus non contiene). Il miglior 1% dei
  wallet prende il **59,8%** di tutti i guadagni (in linea con Bitquery: 56%).
- **L'abilità persiste**: in 11 finestre su 11 la correlazione di rango tra il rendimento di un wallet in 3 giorni e
  nei 3 successivi è positiva (da 0,22 a 0,68). Il 10% migliore di una finestra guadagna in media circa **+5%** a
  posizione nella finestra dopo, gli altri perdono circa −6%.
- **Ma copiarli qualche secondo dopo non basta**: scegliendo ogni giorno i 50 migliori dei 3 giorni prima e
  copiandone gli acquisti del giorno dopo (4.163 copie, 34 giorni), il risultato è **−5,9% a copia con 3 secondi di
  ritardo** e −6,5% con 10 secondi, contro −9,1% copiando 50 wallet a caso. La selezione aiuta (circa +3 punti
  rispetto al caso, con intervalli separati), ma non rende positivo il risultato: il vantaggio di quei wallet sta nei
  primi secondi e nel momento esatto della vendita, che un seguace in ritardo non ottiene.
- **Il vantaggio dura meno di un secondo** (studio `jocry_copy2`, stesse 4.163 occasioni): la copia perfetta, allo
  stesso prezzo del wallet copiato, renderebbe **+9,1%** a copia (stabile, sopra il controllo); con **1 secondo** di
  ritardo diventa **−5,4%**. Nessuna variante realizzabile è positiva: wallet "lenti" −5,4%, uscita fissa dopo 2 minuti
  −4,2%, consenso di due wallet −10,5%. Copiare i migliori è una gara di velocità che si vince solo nello stesso
  blocco, cioè con infrastruttura veloce a pagamento (gRPC dedicato, bundle Jito), esclusa dai vincoli della demo, e
  anche così contro molti altri bot che fanno la stessa cosa.
- Dal vivo, l'esperimento di copia del bot resta attivo come verifica su novembre (con il ritardo reale dello stream:
  una copia non può partire prima che l'operazione sia arrivata al bot).

### 9.6 Token già quotati su PumpSwap (fly-trader-seed: una settimana, 14-21 settembre, 28.721 token)

Nota: la scheda del dataset parla di aprile-settembre, ma le candele contenute nel file coprono solo questa settimana
(1,03 milioni di candele da 1 minuto). La vita mediana di un token dopo il diploma è di **2 ore** (ultima ora con
scambi); solo il 32% viene ancora scambiato dopo 24 ore. Sette regole pre-registrate (qualsiasi ora, slancio,
slancio forte, ritracciamento, sopravvissuti con liquidità, sopravvissuti senza vendite di insider, accumulo), tenute
1, 4 o 24 ore con la commissione reale del pool, l'impatto sul prezzo e le priority fee: **21 combinazioni su 21 non
positive**, dal −4% al −43% per operazione; le due migliori (ritracciamento e slancio forte, 1 ora) sono intorno a
zero con intervalli molto larghi. Una settimana non basta per escludere tutto, ma niente indica un vantaggio.

### 9.7 Un modello che impara quando entrare per 5-10 minuti (loopholetape, 1,26 milioni di momenti, 547.350 token)

Modello ad alberi (gradient boosting) con 24 caratteristiche note al momento della decisione, allenato solo sui
giorni passati e giudicato su quelli successivi (`loop_model`). Al primo passaggio le selezioni a 10 minuti
risultavano molto positive (+22% / +92%): **era un errore dello studio**. Il 71% dei token non aveva più dati 10
minuti dopo (erano morti) e lo studio li scartava, lasciando solo i sopravvissuti. La verifica (`loop_model2`)
li conta al loro valore finale e allena il modello sulla prima metà dei giorni, giudicandolo solo sulla seconda:
**tutte le selezioni perdono**, dal −7% al −10% per operazione a 5 e a 10 minuti, con il diploma tagliato del 30% o
del 50%. Il modello guarda soprattutto la riserva della curva e il calo dal massimo; prevede bene l'ordine dei
risultati (correlazione 0,61), ma anche i token migliori secondo lui restano in media sotto zero dopo i costi.

### 9.8 Un modello "portabile" per i token quotati, tenuta 1 e 4 ore (jocry giugno-luglio + settembre da un'altra fonte)

Caratteristiche che esistono per qualsiasi token su un DEX (rendimenti a 5 minuti, 1 ora e 6 ore, distanza dal
massimo, volume rispetto alla liquidità, accelerazione del volume, quota di acquisti, numero di operazioni,
capitalizzazione rispetto alla liquidità, età). Allenato su giugno-luglio (walk-forward) e poi applicato invariato a
una settimana di settembre presa da un'altra fonte (`dex_model`). Al primo passaggio settembre sembrava enormemente
positivo (+57% / +1.047%) con solo il 3% di operazioni vincenti: **altro errore dello studio**, perché la vendita
non teneva conto della liquidità e incassava picchi di prezzo in pool quasi vuoti. Con ogni vendita fatta dentro il
pool, con la sua riserva reale in quel momento: **tutte le 32 combinazioni perdono**, dal −3% al −47% a giugno-luglio
e dal −9% al −57% a settembre.

### 9.9 Conclusione onesta (3 novembre 2026)

| Famiglia di strategie | Dati | Risultato |
|---|---|---|
| Comprare sulla curva e tenere fino al diploma | 547.350 token, set-ott | perde (−13% / −25%) |
| Entrate a breve sulla curva (slancio, ritracciamento, flusso) | 330.000 token, set-ott | perde, anche senza costi |
| Comprare dopo il diploma (1-30 min, tenuta 1-24 h) | 5.669 diplomi, giu-lug | nessuna positiva e stabile |
| Regole sui token già quotati | 28.721 token, set | nessuna positiva |
| Copiare i wallet migliori con 1-10 s di ritardo | 4.163 copie, giu-lug | perde (−5% / −6%) |
| Copiare i wallet migliori **nello stesso istante** | stesse occasioni | **+9%**, ma richiede velocità da infrastruttura a pagamento |
| Modello che sceglie quando entrare per 5-10 minuti | 1,26 milioni di momenti, set-ott | perde (−7% / −10%) dopo la correzione |
| Modello portabile per token quotati, 1 e 4 ore | 1 milione di momenti giu-lug + 152.656 set | perde (da −3% a −57%) |
| Fornire liquidità ai pool PumpSwap (fare il banco), 1 h - 3 giorni | 5.067 token giu-lug + 19.242 set | perde (da −4% a −52%), sezione 9.10 |
| Short sui perpetui Binance di altcoin e memecoin, 1-3 giorni | 918 contratti 2020-2026 | nessuna regge (la migliore +3,7% annuo, negativa con costi doppi), sezione 10.2 |

1. Con i vincoli della demo (dati e infrastruttura gratuiti, nessuna velocità da blocco 0) **non è stata trovata
   nessuna strategia profittevole**, su milioni di casi e quattro periodi diversi. È coerente con la letteratura: i
   guadagni vanno a creatori e insider, a chi è più veloce e a chi manipola (cose che non faremo).
2. L'unico vantaggio misurato è la **velocità**: il risultato dei wallet migliori è reale e persistente, ma sparisce
   entro un secondo. Provarlo davvero richiederebbe un'infrastruttura veloce a pagamento: è una decisione con costi,
   che spetta solo a te, e anche così la concorrenza di bot professionali è forte.
3. Il bot continua a raccogliere prove fuori campione senza rischi: diario degli eventi, laboratorio delle regole,
   esperimento di copia con il ritardo reale, esperimenti x_safe e x_curve, Laboratorio. Nulla viene promosso senza
   il cancello statistico e senza la tua approvazione.

### 9.10 Fare il banco: fornire liquidità ai pool PumpSwap (`dex_lp`)

Chi fornisce liquidità a un pool PumpSwap riceve lo 0,20% di ogni scambio (la commissione resta nel pool; chiunque
può aggiungere liquidità a un token diplomato), ma tiene metà della posizione nel token: se il token scende, perde
anche lui (in SOL la posizione vale la radice quadrata della variazione di prezzo, più le commissioni incassate).
Posizione da 1 SOL con commissioni di swap, impatto sul prezzo e fee di rete; cinque regole pre-registrate (qualsiasi
momento, pool molto scambiato, sopravvissuti, sopravvissuti calmi, flusso equilibrato), tenuta 1, 4, 24 e 72 ore; A =
jocry giugno-luglio (5.067 token), B = fly-trader-seed settembre (19.242 token, ogni scambio).

| Regola (tenuta 1 h / 4 h) | Commissioni incassate | Effetto del prezzo | Netto A giu-lug | Netto B settembre | Comprare il token (A) |
|---|---|---|---|---|---|
| Q0 qualsiasi momento | +0,9% / +1,2% | −12% / −19% | −13% / −20% | −5% / −6% | −10% / −17% |
| Q1 pool molto scambiato | +1,8% / +2,5% | −21% / −34% | −21% / −34% | −22% / −38% | −16% / −26% |
| Q2 sopravvissuto (24 h, riserva ≥ 50 SOL) | +0,02% / +0,05% | −4% / −9% | −5% / −10% | −5% / −9% | −9% / −14% |
| Q3 sopravvissuto calmo | +0,02% / +0,05% | −2% / −7% | −4% / −9% | (pochi casi) | −6% / −13% |
| Q4 flusso equilibrato | +0,3% / +0,7% | −5% / −12% | −7% / −13% | −8% / −19% | −8% / −11% |

**Tutte le 33 combinazioni misurabili (20 su A, 13 su B) sono negative** (q = 1), anche a 24 e 72 ore (dove però A non osserva più i token e il
risultato dipende dall'ipotesi sul prezzo finale). La commissione dello 0,20% è troppo piccola rispetto alla discesa
media dei token: si perde un po' meno che comprando, ma si perde. Nei pool PumpSwap chi incassa davvero sono la
piattaforma e il **creatore del token** (fino allo 0,95% di ogni scambio nei token piccoli), non chi fornisce liquidità.

---

## 10. Fuori dalle memecoin: le crypto affermate (Binance 2018 - ottobre 2026)

Su indicazione dell'utente ("qualunque coin, basta che funzioni nel tempo e abbia una logica") la ricerca si è
allargata alle crypto affermate. Dati: candele giornaliere di **697 coppie USDT di Binance, comprese quelle poi
tolte dal mercato** (LUNA, FTT...), archivio pubblico gratuito. Regole fissate prima, parametri scelti solo sul
2018-2021, giudizio sul 2022 - ottobre 2026; costi 0,15% per lato (`crypto_trend`, `crypto_trend2`).

| Strategia (fuori campione 2022-2026) | Rendimento annuo | Perdita massima |
|---|---|---|
| BTC comprato e tenuto | +11,3% | −67% |
| BTC solo sopra la media di 50 / 100 / 200 giorni | +20,0% / +20,8% / +27,3% | −51% / −37% / −32% |
| Le 10 crypto più scambiate comprate e tenute | −33,3% | −91% |
| Momentum tra monete (le 5 migliori ogni settimana) | da −29% a −72% | fino a −99,8% |
| Trend sulle 10 più scambiate, rottura dei massimi | da −17% a +4% | |
| **BTC + ETH + SOL, ognuno solo sopra la media di 50 giorni** | **+31,2%** | **−42%** |
| BTC + ETH + SOL comprati e tenuti | +1,4% | −80% |

- **Il filtro di trend è un effetto generale**: con la media di 50 giorni (scelta solo sul BTC del 2018-2021) batte
  il "compra e tieni" sia nel rendimento sia nella perdita massima su **6 monete su 7** (BTC, ETH, SOL, BNB, ADA,
  DOGE; non XRP), anche con **costi doppi** e con **un giorno intero di ritardo** nell'esecuzione.
- Anno per anno il portafoglio con filtro: 2022 −36% (contro −80%), 2023 +206% (contro +294%), 2024 +38% (contro
  +90%), 2025 +30% (contro −14%), 2026 fino a ottobre +6% (contro −19%). Rinuncia a parte dei grandi rialzi ed
  evita gran parte dei grandi crolli.
- **La logica**: nelle crypto i trend tendono a persistere (momentum nel tempo, documentato in letteratura, per
  esempio Liu e Tsyvinski, 2021) e le perdite più grandi arrivano nei crolli lunghi; uscire quando il prezzo scende
  sotto la media ne evita la maggior parte.
- **Limiti**: con meno di 5 anni fuori campione l'intervallo di confidenza dello Sharpe tocca lo zero (−0,09); il
  ritardo conta (con un giorno di ritardo +18,6% annuo invece di +31,2%); le altcoin, anche le più scambiate, nel
  2022-2026 hanno distrutto valore e nessuna strategia su di loro ha funzionato.
- **Nel bot**: portafoglio virtuale "Trend BTC·ETH·SOL" (pagina dedicata della dashboard), decisioni alla chiusura
  giornaliera delle 00:00 UTC con dati gratuiti (Binance, Kraken di riserva), 0,15% di costi per lato, confronto
  continuo con il compra e tieni. Nessuna operazione reale e nessun messaggio Telegram. Essendo giornaliera, servono
  mesi perché la verifica dal vivo dica qualcosa.

### 10.1 Operazioni brevi (1-3 giorni) su 100 monete, memecoin comprese (`crypto_daily`)

Le 100 crypto più scambiate di ogni giorno (in media 3,3 memecoin: DOGE, SHIB, PEPE, WIF, BONK, FLOKI, BOME...),
massimo 10 posizioni da un decimo del capitale, stop a −15%, costi 0,15-0,30% per lato. Fuori campione 2022-2026:

| Regola | Tenuta 1 / 2 / 3 giorni: rendimento annuo | Operazioni (3 giorni) |
|---|---|---|
| H1 hype (prezzo +10% in un giorno con volume triplo) | −30% / −21% / −20% | 1.725 |
| **H2 hype solo con BTC sopra la media di 50 giorni** | **−11% / +7,6% / +11,7%** | **1.216** |
| P1 comprare i cali in una moneta in salita | −52% / −59% / −58% | 2.941 |
| B1 rottura dei massimi a 20 giorni con volume doppio | −30% / −8% / −13% | 1.919 |
| S1 le 5 più forti degli ultimi 3 giorni | −41% / −40% / −44% | 2.550 |
| M1 modello che impara quando entrare | −56% / −55% / −65% | 4.446 |

- Solo **H2 a 2-3 giorni** è positiva in entrambi i periodi (2018-2021 +24% annuo a 3 giorni; 2022-2026 +11,7%),
  con +0,76% medio per operazione e il 39% di operazioni vincenti; ma l'intervallo di confidenza è molto largo
  (Sharpe da −0,50 a +1,35) e la perdita massima è −51%: **non dimostrata**.
- Il modello M1 guadagnava nel periodo di addestramento (+15/+29% annuo) e perde il 55-65% annuo dopo: è il caso
  tipico di un modello che impara il passato a memoria (sovra-adattamento).
- Confronto con il trend BTC·ETH·SOL (sezione 10): +31% annuo, perdita massima −42%, 141 operazioni, verificato su
  6 monete su 7 con costi doppi e ritardo. Le operazioni brevi su molte monete rendono meno e sono meno solide.

**Verifica di robustezza di H2 (`crypto_daily2`, varianti decise prima di guardare i risultati).** Positive fuori
campione **6 varianti su 17**:

| Variante (tenuta 3 giorni) | 2018-2021 | 2022-2026 | Perdita massima 2022-2026 |
|---|---|---|---|
| H2 originale | +24,1% | +11,7% | −51% |
| 8 soglie vicine (prezzo +5/10/15%, volume 2/3/5 volte) | da +4,7% a +39% | 7 negative su 8 (da −29,6% a +2,2%) | da −45% a −88% |
| filtro BTC a 100 giorni invece di 50 | +29,5% | −5,5% | −51% |
| stop a −10% / −25% | −0,9% / +36% | −2,0% / +6,0% | −62% / −64% |
| costi doppi | +9,2% | **−2,4%** | −64% |
| entrata un giorno dopo | +60,6% | **−2,2%** | −48% |
| solo memecoin (130 operazioni) | +2,0% | +12,0% | −17% |
| senza memecoin | +21,4% | +10,3% | −49% |

Anno per anno (H2 originale): 2018 +0,4%, 2019 −3,3%, 2020 −1,8%, 2021 +149%, 2022 −4,6%, 2023 +24%, 2024 +42%,
2025 −44%, 2026 +81%.

**Verdetto: H2 non è robusta.** Cambiando di poco le soglie diventa negativa, con costi doppi o un giorno di
ritardo perde, e il risultato dipende da pochi anni di euforia (2021, 2024, 2026) con un −44% nel 2025. Non viene
aggiunta al bot. Il sottoinsieme "solo memecoin" è positivo ma conta solo 130 operazioni, era quasi piatto nel
2018-2021 e usa un elenco di memecoin scritto oggi (conoscendo già quali sono sopravvissute): non è una prova.
L'unica regola che ha superato tutte le verifiche resta il trend di sezione 10.

### 10.2 Scommettere sulla discesa: short sui perpetui, 1-3 giorni (`crypto_short`)

Se comprare altcoin e memecoin perde, forse vendere allo scoperto guadagna. 918 perpetui USDT di Binance 2020-2026
(31 chiusi, inclusi; 36 memecoin), le 100 più scambiate ogni giorno, al massimo 10 posizioni da un decimo, garanzia 1x,
stop a +15% sul massimo del giorno, commissione 0,05% + slittamento 0,05-0,20% per lato, **funding reale** di Binance
accreditato o addebitato ogni giorno. Contesto: nel 2022-2026 il 53,9% di queste monete scende nei 3 giorni successivi,
ma la variazione media è solo −0,25% (mediana −0,67%): la discesa media è più piccola dei costi.

| Regola (fuori campione 2022-2026) | 1 / 2 / 3 giorni: rendimento annuo | Funding medio per operazione (3 giorni) | Fermate dallo stop (3 giorni) |
|---|---|---|---|
| SH1 vendere dopo l'hype (+10% e volume triplo) | −38% / −48% / −43% | −0,34% | 41% |
| SH2 SH1 solo con BTC sotto la media di 50 giorni | −6% / −8% / −5% | −0,71% | 40% |
| SS1 vendere le 5 più salite in 3 giorni | −58% / −53% / −45% | −0,20% | 28% |
| SN1 vendere i nuovi listing al secondo giorno | +1,3% / +0,6% / +3,7% | −0,21% | 41% |
| SF1 vendere quando il funding è >= 0,10% | −37% / −31% / −26% | +0,24% | 40% |
| SB1 seguire la debolezza con BTC in calo | −30% / −25% / −23% | −0,13% | 21% |

- **Nessuna regola regge.** L'unica positiva, vendere i nuovi listing (SN1), guadagna pochissimo (+3,7% annuo a
  3 giorni, intervallo dello Sharpe da −0,66 a 1,09) e diventa negativa con costi doppi (−1,8%) o entrando un giorno
  dopo (−0,6%).
- Dopo l'hype il **funding gioca contro chi vende**: chi è già corto paga (in media −0,3/−0,7% per operazione), e il
  40% delle posizioni viene fermato da rialzi improvvisi del 15% (le memecoin "squeezano" i venditori).
- Una nota sul primo calcolo: nella prima esecuzione il funding non veniva abbinato alle candele (date con e senza
  fuso orario); corretto e rieseguito con le stesse regole. Senza funding SN1 a 3 giorni faceva +6,0%: il funding
  pagato dai venditori ne mangia quasi metà.

## 11. Fonti principali

- Arrow Algo, *Solana Memecoin Trading: What 1,411 Launches Showed* — https://arrowalgo.com/solana-memecoin-trading/
- Bitquery, *Solana Memecoin Traders: 74% Lose Money* — https://bitquery.io/investigations/solana-memecoin-traders-lose-money
- Bitquery, *Pump.fun Devs' Bundles Made $579M+, Snipers Just $31.5M* — https://bitquery.io/investigations/pump-fun-snipers-bundles
- Szwajcok et al., *Meme Coin Factories* (arXiv 2609.10246) — https://arxiv.org/abs/2609.10246
- Mongardini, Mei, *A Midsummer Meme's Dream* (USENIX Security 2026, arXiv 2507.01963) — https://arxiv.org/abs/2507.01963
- *MELT / MemeTrans* (arXiv 2602.13480) — https://arxiv.org/abs/2602.13480
- Kamat, *Pump.fun Graduation Regime Windows* (arXiv 2607.02823, corretto) — https://arxiv.org/abs/2607.02823
- *Coordinated Sniper Cohorts on Pump.fun* (arXiv 2607.02795) — https://arxiv.org/abs/2607.02795
- Gafarov, *Early-Buyer Groups and Fast-Wallet Teams* (arXiv 2610.39458) — https://arxiv.org/abs/2610.39458
- Gafarov, *Serial Rug-Pull-Like Exits on Pump.fun* (arXiv 2610.41597) — https://arxiv.org/abs/2610.41597
- *The Memecoin Phenomenon* (arXiv 2512.11850) — https://arxiv.org/abs/2512.11850
- Launchtape, *What 2,193 pump.fun graduations did in their first 10 minutes* — https://dev.to/launchtape/what-2193-pumpfun-graduations-did-in-their-first-10-minutes-and-what-it-means-for-your-bot-4f70
- PumpFunData, *Graduation rate analysis* — https://pumpfundata.com/blog/pumpfun-graduation-rate-analysis
- CoinGecko, *Pump.fun traders are making a comeback* — https://www.coingecko.com/research/publications/pump-fun-traders-are-making-a-comeback
- Xanguard, *307 top-trader calls* — https://xanguard.tech/blog/pumpfun-caller-win-rates/
- *Inside the Economics of Pump.fun Call Channels* — https://moneyleavesclues.substack.com/p/inside-the-economics-of-pumpfun-call
- memecoin-survival (GitHub) — https://github.com/mahad1z/memecoin-survival
- pump-bundle-check (GitHub) — https://github.com/opsec-bot/pump-bundle-check
- IDL ufficiali pump.fun e PumpSwap — https://github.com/pump-fun/pump-public-docs
