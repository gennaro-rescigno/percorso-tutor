# PROFITABILITY_RESEARCH_REPORT.md — Ricerca di strategie profittevoli sulle memecoin (4 novembre 2026)

**Verdetto in una riga.** Su 41 famiglie di strategie, circa 50.000 combinazioni generate automaticamente, quattro
periodi e sei dataset gratuiti reali, **nessuna strategia sulle memecoin ha un vantaggio statistico dimostrato fuori
campione** eseguibile con strumenti gratuiti. L'unico vantaggio misurato sulle memecoin è la velocità nello stesso
blocco, che non è eseguibile gratis. La strategia più credibile in assoluto non riguarda le memecoin: il trend su
BTC·ETH·SOL, che resta "promettente, non dimostrata".

Documenti collegati: metodo in `STRATEGY_RESEARCH.md`; classifica in `STRATEGY_COMPARISON.md` e
`STRATEGY_RANKING.csv`; stato del progetto in `PROJECT_AUDIT.md`; dettaglio di ogni studio in
`docs/RICERCA_MERCATO_MEMECOIN.md` (sezioni 9-10); report originali nel branch `research-results`.

## 1. Mercato analizzato

- **Nuovi lanci su pump.fun** (curva di bonding), dai primi 10 secondi alla prima ora, e il passaggio a PumpSwap.
- **Memecoin già quotate**: pool PumpSwap da 30 minuti a 48 ore dopo il diploma; memecoin con contratti perpetui
  e coppie spot su Binance (DOGE, SHIB, PEPE, BONK, FLOKI, WIF, POPCAT, FARTCOIN, TRUMP e altre 51) dal 2021.
- **Short, funding e liquidità** come moduli separati; **crypto affermate** come confronto.
- Altri launchpad (Raydium LaunchLab, Bonk.fun, Moonshot): **nessun dato storico gratuito verificato**; il solo
  dataset multi-piattaforma trovato (launchtape) contiene 2 ore di campione e non permette test.

## 2. Fonti utilizzate

| Fonte | Periodo | Osservazioni | Licenza |
|---|---|---|---|
| jocry/Pumpfun_Memecoin_Corpus (Hugging Face) | 5 giu – 14 lug 2026 | 798.430 token, 33,6 M operazioni con wallet, 1 M istantanee PumpSwap | MIT |
| loopholetape/pumpfun-launches | 31 ago – 27 ott 2026 | 1,36 M lanci | CC BY |
| bryceweiner/fly-trader-seed | 14 – 21 set 2026 | 1,03 M candele di 28.721 token | MIT |
| pumpdatafun/pump-fun-trades-sample | 15 ott 2026 | 42,2 M righe, transazioni fallite comprese | CC BY 4.0 |
| AratiKamat/red-pump-2026 | 8 mag – 10 giu 2026 | 833.079 lanci con esito | CC BY 4.0 |
| hussxamg04/trenches-pumpfun-forward-2026-08 | 6 – 13 ago 2026 | 85.442 token con dati X | PolyForm Noncommercial (solo ricerca) |
| data.binance.vision | 2018 – ott 2026 | 697 coppie spot, 918 perpetui con funding, delistati compresi | pubblico |
| Stream e API del bot (WebSocket Solana, PumpPortal, DexScreener, GeckoTerminal, Jupiter, RugCheck) | dal 1° nov 2026 | dati dal vivo | gratuiti |

Non usati: Birdeye, Helius, gRPC dedicati e ogni servizio a pagamento (vincolo). Le API sono state verificate
dal vivo sul server (tutte "ok" il 3 novembre); il sandbox di sviluppo non raggiunge questi host, per cui gli
studi girano sui runner di GitHub.

## 3. Qualità dei dati

- jocry: il 7% delle operazioni senza prezzo (token interi), il 3,4% con importi SOL incoerenti, il 20% attribuito
  al System Program (escluso dalle caratteristiche dei wallet), cinque cambi di regime documentati; trattati come
  indica la scheda del dataset. Tracciamento di 48 ore per token.
- loopholetape: campionamento delle caratteristiche, cuciture del decodificatore (27 settembre, 8 ottobre): gestite
  come da scheda.
- fly-trader-seed: la scheda parla di aprile-settembre, il file contiene una settimana.
- red-pump: etichette del collettore (0,20% di diplomi, molto meno degli altri dataset).
- trenches: i dati su X arrivano in mediana 20,5 s dopo il loro timestamp; **utilizzabili alla decisione su 0 token**.
- Dati del bot: ritardo mediano dello stream 28,7 s; 15.429 lanci e 565.231 operazioni registrati.

## 4. Pattern individuati (fatti, non strategie)

1. **La finestra utile dura secondi.** La probabilità di un raddoppio prima di un dimezzamento è il 14,3% a 10 s dal
   lancio, l'8,9% a 30 s, il 2,5% a 5 minuti; dopo 30 s il token mediano non supera più il prezzo del momento
   nell'ora successiva (574.105 momenti, jocry).
2. **I segnali sono informativi ma il prezzo li incorpora già.** A 3-5 minuti numero di acquisti e accelerazione
   prevedono il diploma con AUC 0,85-0,89, ma nessuna combinazione segnale × entrata × uscita guadagna (46.284
   strategie).
3. **Pump artificiali**: molti wallet nello stesso secondo, grandi acquisti iniziali del creatore e creatori seriali
   portano a più diplomi e anche a più rug; chi entra dopo perde di più (−9,8% contro −5,2% a operazione).
4. **Wallet con un buon passato**: dove sono presenti i token si diplomano 6 volte di più, ma l'operazione resta
   negativa (−3,4%); copiarli rende +9,1% solo allo stesso prezzo, −5,4% con 1 secondo di ritardo.
5. **Esecuzione**: sulla curva fallisce l'85% delle transazioni di acquisto nei primi 10 s (soprattutto bot che
   ripetono; il wallet mediano non fallisce mai).
6. **Memecoin quotate**: dopo il diploma il prezzo mediano a 30 minuti è al 2% del prezzo iniziale (settembre-ottobre);
   anche il filtro di trend, l'unico effetto robusto altrove, sulle memecoin perde meno che tenerle ma non guadagna in
   modo affidabile (+4,6% annuo, merito di PEPE e FLOKI).
7. **Progetti**: link social e descrizione alla creazione predicono il diploma (top 10%: ×5,6), senza prova di profitto.

## 5. Strategie testate

Nuovi lanci: tenere fino al diploma (7 regole), entrate a 1-5 minuti (18), modello a 5-10 minuti, dopo il diploma
(36), copia dei wallet (3 s, 10 s, 1 s, istante), motore di scoperta (46.284), paper trading dal vivo (principale,
Laboratorio, x_safe, x_curve, x_copy). Memecoin quotate: regole PumpSwap (21), modello portabile 1-4 h, fornire
liquidità (33), motore di scoperta (3.456), hype / rotture / pullback / forza / modello a 1-3 giorni su 100 monete
(18 + 17 varianti di robustezza), trend giornaliero e a 4 ore su 60 memecoin. Short (18), funding (16). Crypto
affermate: trend, momentum tra monete, rotture.

## 6. Strategie scartate

Tutte quelle con media fuori campione non positiva: 32 su 41 nella classifica (dettaglio in `STRATEGY_COMPARISON.md`).
Le più istruttive: comprare sulla curva e tenere fino al diploma (−13% / −25% a operazione: il mercato prezza la
probabilità di diploma); entrate brevi sulla curva (perdono anche senza costi); copiare i wallet con qualunque
ritardo realizzabile; fornire liquidità (la commissione dello 0,20% non copre la discesa); lo short dopo l'hype (il
41% delle posizioni viene fermato da squeeze del 15%); il funding dopo il 2021.

## 7. Strategie promettenti (non dimostrate)

| Strategia | Fonte, periodo | N | Risultato fuori campione | Perché non basta | Affidabilità |
|---|---|---|---|---|---|
| Trend BTC·ETH·SOL (media 50 giorni) | Binance 2022-2026 | 141 operazioni | +31,2% annuo, max DD −42% | intervallo dello Sharpe [−0,09; 1,83] tocca lo zero | media-alta |
| Trend su 60 memecoin (media 50) | Binance 2022-2026 | 1.474 | +4,6% annuo, max DD −60% | negativa con costi doppi; dipende da 2 monete | bassa |
| Hype con BTC in trend (3 giorni) | Binance top 100 2022-2026 | 1.216 | +11,7% annuo | 6 varianti vicine su 17 positive; perde con costi doppi o ritardo | bassa |
| Rottura del massimo + uscita per slancio perso | jocry giu-lug | 368 | +6,6% medio (mediana −12,6%) | misurata su tutti i giorni, il motore non la conferma | molto bassa |
| Short dei nuovi listing (3 giorni) | Binance perpetui 2022-2026 | 526 | +3,7% annuo | negativa con costi doppi e un giorno di ritardo | bassa |
| Copia perfetta dei wallet migliori | jocry giu-lug | 4.163 | +9,1% a operazione | non eseguibile senza stesso blocco | non eseguibile |

## 8. Performance storiche (metriche principali)

Per ogni strategia del motore di scoperta il report calcola profitto netto, ROI su 2 SOL, win rate, profit factor,
expectancy, vincita e perdita media, max drawdown, Sharpe e Sortino giornalieri, numero di operazioni, massima serie
di perdite, commissioni, tempo medio di permanenza, ordini non eseguibili (`discovery_*_test.csv` nel branch dei
risultati). Esempio, le due migliori sulle memecoin quotate nei giorni di test (consolidamento + uscita a 4 ore): 360
operazioni, **−10,7% a operazione** (IC da −15,5% a −4,7%), 25,6% vincenti, vincita media +29,2%, perdita media
−24,4%, profit factor 0,41, serie massima di 18 perdite. Il capitale di riferimento è 2 SOL e il controvalore in euro è
calcolato dal prezzo corrente di SOL (circa 167 € il 3 novembre), mai fisso.

## 9. Limiti dei test

- I dataset storici gratuiti coprono pochi mesi del 2026 e un solo giorno con le transazioni fallite.
- Nessun dato storico gratuito per altri launchpad né per l'hype social utilizzabile al momento della decisione.
- Le istantanee PumpSwap di jocry sono ogni 5 minuti: le uscite rapide sono approssimate.
- Il trend sulle crypto affermate ha meno di 5 anni fuori campione.
- Molti test multipli: le soglie (t ≥ 3, Benjamini-Hochberg, giorni di test letti una volta) riducono i falsi
  positivi ma non li azzerano; per questo una strategia deve anche superare il paper trading dal vivo.

## 10. Costi considerati

Commissione della curva 1,25% per lato; commissioni PumpSwap per fascia di capitalizzazione (1,25% → 0,30%);
impatto del proprio ordine sulla riserva; vendita attraverso il prodotto costante del pool; commissioni di rete
0,0002 SOL a transazione (sopra il 90° percentile misurato sul server); slittamento di latenza; ritardo dei dati 0 /
3 / 30 s; stress con commissioni doppie e 3% di slittamento aggiuntivo; su Binance 0,05-0,10% di commissione più
0,05-0,20% di slittamento e funding reale.

## 11. Rischi

- **Rischio di strategia**: con aspettativa negativa, nessun dimensionamento rende positivo il risultato; la
  frazione di Kelly per un'aspettativa negativa è zero.
- **Rischio di esecuzione**: dati in ritardo, transazioni fallite, gap sugli stop (dal vivo la maggior parte delle
  perdite chiude "stop superato in gap").
- **Rischio di controparte e manipolazione**: bundle, creatori seriali, rug, wash trading.
- **Rischio di sovra-adattamento**: un modello che guadagnava +15/+29% in addestramento ha perso il 55-65% dopo.
- **Gestione del capitale (2 SOL)**: il bot ha già profili conservativo / moderato / aggressivo, perdita massima per
  operazione, limite giornaliero, kill switch e la possibilità di non operare. Senza un vantaggio dimostrato la
  scelta corretta per le memecoin è **non allocare capitale reale**; niente martingala, niente aumenti per recuperare.

## 12. Prossimi esperimenti

1. **Verifica dal vivo** (gratuita, già attiva o da attivare in paper): trend BTC·ETH·SOL (in corso); "rottura del
   massimo + uscita per slancio perso" sulle memecoin quotate e "wallet dal buon passato" come filtro, registrati
   ora con regole fisse, da giudicare solo sui dati futuri.
2. **Esperimento di copia**: rivedere i criteri sui dati del registro del bot (oggi 0 leader idonei su 992).
3. **Hype social dal vivo**: il bot registra già boost DexScreener e token di tendenza con l'ora esatta; quando ci
   saranno settimane di dati, test onesto dell'hype su dati che il bot conosceva davvero al momento.
4. **Nuovi periodi**: rieseguire i motori di scoperta quando usciranno nuovi dataset gratuiti (es. altri giorni di
   pumpdata) per verificare che i verdetti negativi reggano.
5. **Decisione con costi (tua)**: un'infrastruttura veloce è l'unica via verso l'unico vantaggio misurato; anche così
   lo stesso blocco su Solana non è garantito (non c'è una mempool pubblica) e la concorrenza dei bot è forte.

## Risposte alle 10 domande prioritarie

1. **Quali nuovi lanci hanno la maggiore probabilità di un rialzo sfruttabile?** Quelli con molti acquisti in
   accelerazione e wallet dal buon passato: più probabilità di diploma (fino a ×6), ma nessun rialzo sfruttabile
   dopo i costi con i dati gratuiti.
2. **Quando conviene entrare?** Il rialzo esiste solo nei primi secondi (14% di raddoppi a 10 s, 2,5% a 5 minuti);
   con 28,7 s di ritardo dei dati è già tardi. Nessun momento tra 10 s e 60 minuti ha dato un'entrata profittevole.
3. **Quali wallet e comportamenti anticipano i movimenti?** I wallet con buon passato (abilità persistente, correlazione
   di rango 0,22-0,68 tra finestre) e l'accelerazione degli acquisti; i bundle anticipano diplomi "costruiti" e rug.
4. **Pump organico o artificiale?** Artificiale: molti wallet nello stesso secondo, grande acquisto del creatore,
   creatore seriale, wallet nuovi. Organico: più acquirenti unici nel tempo e wallet dal buon passato. Nessuno dei
   due gruppi rende positivo comprarli dopo.
5. **Quali memecoin esistenti offrono opportunità?** Nessuna famiglia di pattern ha retto fuori campione; il filtro
   di trend limita le perdite (−23% → +4,6% annuo) senza dimostrare un guadagno.
6. **Quali strategie hanno aspettativa positiva?** Nessuna sulle memecoin, eseguibile gratis e dimostrata.
7. **Quando prendere profitto?** Sulle memecoin quotate perdono meno le uscite rapide (1 ora: −5,2%) e lo stop −25% /
   obiettivo +50% (−5,8%) rispetto alla tenuta di 24 ore (−11,1%) e all'uscita parziale (−7,4%); sui lanci nessuna
   uscita rende positiva un'entrata negativa.
8. **Quando uscire per limitare la perdita?** Presto: la perdita media cresce con la durata (memecoin quotate: −5,2%
   a 1 h, −11,1% a 24 h); gli stop fissi sono spesso saltati in gap.
9. **Quanto capitale allocare?** Zero alle strategie memecoin finché nessuna è dimostrata; il paper trading continua.
10. **Quali strategie resistono a costi, slippage e mercati diversi?** Nessuna memecoin; il trend su BTC·ETH·SOL regge a
    costi doppi e un giorno di ritardo, ma il suo intervallo statistico tocca ancora lo zero.
