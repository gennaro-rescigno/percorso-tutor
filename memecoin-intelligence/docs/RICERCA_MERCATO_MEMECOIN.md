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

### 9.5 Cosa ne segue per il bot

1. Le strategie "semplici" sui lanci (comprare presto, tenere fino al diploma, comprare dopo il diploma, comprare
   i crolli, seguire lo slancio o il flusso, comprare i ritracciamenti) sono **verificate perdenti** su milioni di
   casi, quasi tutte anche prima dei costi: non le adotteremo.
2. Il valore che possiamo costruire gratis sta in tre cose: **evitare** (filtri che riducono le perdite),
   **orizzonti brevi con uscite rapide** misurati sul percorso completo dei prezzi (che solo il nostro stream ha),
   e **verifica fuori campione** continua prima di qualunque decisione.
3. Per questo il bot ora tiene un **diario di ogni lancio** (fatti on-chain con prezzo e ora), uno **studio di cosa
   succede dopo ogni tipo di evento** e un **laboratorio di regole** pre-registrate valutate su ogni lancio
   osservato dopo il 3 novembre 2026, con i costi. Nulla cambia nel portafoglio principale senza il tuo consenso.

---

## 10. Fonti principali

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
