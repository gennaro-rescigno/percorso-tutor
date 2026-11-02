# Evoluzione del bot — Fase 1 (Audit) e Fase 2 (Ricerca)

Data: 2 novembre 2026 · Stato del progetto al commit `1358040` (branch `main`) · **Nessuna modifica al codice in questa fase.**

**Come leggere i verdetti:**
- ✅ **Verificata**: confermata da documentazione o letteratura.
- 🧪 **Da sperimentare**: plausibile, ma va misurata sui nostri dati.
- ❌ **Non realizzabile**.
- 💸 **Non realizzabile gratuitamente**.
- ⚠️ **Non conveniente**.

**Limiti di questa ricerca, onestamente:**
- Dal mio ambiente di lavoro non posso aprire direttamente le pagine dei fornitori, perché la rete è filtrata. Ho usato la ricerca web e riporto le fonti trovate.
- Diversi numeri (rate limit, piani gratuiti) sono **in conflitto tra fonti diverse** o provengono da **siti terzi**: li segnalo come tali.
- Prima di usarli in produzione **il bot li misurerà da solo**, come già fa con GeckoTerminal.

---

## 0. Sintesi in 12 punti

1. **La base è solida, ma è un «bot di mercato», non ancora un bot di «wallet intelligence».**
   - Funzionano già: scoperta dei token, raccolta dati, sicurezza di base, strategie, rischio, paper trading, dashboard, Telegram, VPS con aggiornamenti automatici.
   - **Non legge mai la storia dei wallet**: niente grafo dei finanziamenti, niente storico dei deployer, niente cluster propri.
2. **Gli indicatori «insider» e «dev» oggi sono delegati a RugCheck**: un servizio esterno non ufficiale e senza contratto, quindi per noi una scatola nera.
3. **C'è codice scritto ma mai usato**: `early_buyer_concentration` e `coordinated_selling` in `backend/mci/onchain/wash.py` non vengono chiamati da nessuna parte. Anche il controllo «vendite coordinate» in `paper_trading/engine.py` legge un dato che nessuno compila.
4. **I pesi del punteggio (15/15/20/20/10/5/15) sono scelti a mano**, cioè arbitrari: proprio ciò che la direttiva vieta. Inoltre rischio e opportunità sono mescolati in un unico numero, anche se esistono esclusioni obbligatorie.
5. **Risultati finora: nessuna prova di un vantaggio statistico.**
   - 12 operazioni chiuse: media **+9,9%**, mediana **+0,3%**, deviazione standard **33%**.
   - **Intervallo di confidenza al 95%: da −11% a +31%.**
   - Togliendo la sola operazione migliore (+89%), la media scende a **+2,7%**.
6. **Quante operazioni servono:**
   - circa **43** se il vantaggio vero fosse +10% per operazione;
   - circa **170** se fosse +5%.

   Questo è l'ordine di grandezza da raggiungere prima di dichiarare qualcosa.
7. **Lo storico gratuito è peggiorato.** Secondo le fonti trovate, Dune ha ristretto il piano gratuito da settembre 2026. La strada affidabile e senza bias è **la raccolta in avanti che facciamo già**, da arricchire.
8. **Wallet intelligence gratis: fattibile, ma solo «a imbuto».**
   - La parte costosa (primi acquirenti, chi li ha finanziati, storico del deployer) costa circa 50–80 chiamate RPC per token.
   - Con RPC pubblico ed eventualmente il piano gratuito Helius si possono analizzare a fondo **decine di token all'ora**, non tutti i lanci.
9. **Le idee dell'altro sviluppatore sono in gran parte sensate e supportate dalla letteratura.**
   - Per esempio, nel dataset MemeTrans (oltre 41.000 lanci su Solana) i primi 10 acquirenti dei token ad alto rischio detengono **17 punti percentuali** di supply in più.
   - **Ma «tip Jito» non vuol dire «bundle», e «bundle» non vuol dire «truffa».** Va misurato, non assunto.
10. **Esecuzione «alla Jito»**: in DEMO si possono usare **dati reali sui costi** (fee di priorità, minimo delle tip), forniti gratis. Le probabilità di fallimento e di atterraggio delle transazioni **non sono misurabili senza transazioni reali**: vanno simulate con ipotesi esplicite e analisi di sensibilità.
11. **Intelligenza artificiale:**
   - un LLM nel ciclo operativo **non serve e non ci sta** sulla VPS (2 vCPU / 4 GB);
   - l'AI utile è il **machine learning classico** (LightGBM/XGBoost/regressione logistica) sui nostri dati, gratuito e locale.
12. **Costo totale realistico: 7,31 €/mese**, cioè solo la VPS già attiva. Tutto il resto può restare a 0 €. Le sole registrazioni opzionali (gratuite) sono **Helius free** e, se servisse, **Moralis free**.

---

## 1. Stato attuale del progetto (audit)

### 1.1 Dimensioni misurate

| Area | Righe di codice | Note |
|---|---|---|
| backtesting | 1.452 | motore, walk-forward, metriche, stress test, import universo (Dune) |
| collectors | 1.145 | DexScreener, GeckoTerminal, Jupiter, RugCheck, PumpPortal, RPC Solana, cambio SOL, social |
| paper_trading | 654 | motore principale + Laboratorio |
| risk_management | 647 | profili, dimensionamento, uscite, gestore |
| strategies | 640 | strategie A–E + indicatori |
| database | 581 | 12 tabelle (tokens, token_snapshots, candles, signals, positions, orders, fills, equity_snapshots, events, system_state, backtest_runs, alert_log) |
| execution | 555 | modello costi, esecutore paper, esecutore reale disattivato |
| telegram | 553 | bot comandi + notifiche |
| scanner | 515 | ciclo di scansione e arricchimento |
| api | 501 | FastAPI |
| scoring | 461 | punteggio 0–100 + filtri di esclusione |
| onchain | 145 | concentrazione holder, metriche wash trading |
| analytics, utils, social, altro | 1.948 | |
| **Test** | 2.227 righe, **123 funzioni di test, 126 casi** (eseguiti su SQLite e PostgreSQL in CI) | |
| **Dashboard** | 1.322 righe React | |

### 1.2 Infrastruttura e costi attuali
- **VPS Hetzner CX23** (2 vCPU, 4 GB RAM, 40 GB): **7,31 €/mese**, IVA e IPv4 inclusi. Pagata con un credito prepagato di 25 €.
- Docker Compose con PostgreSQL, worker, API, publisher della dashboard pubblica e backup giornaliero.
- Aggiornamento automatico ogni 10 minuti: solo versioni con test superati, con ritorno automatico alla versione precedente.
- **Uso misurato**: circa 0,8 GB di RAM e 3,3 GB di disco.
- **Servizi esterni usati, tutti gratuiti**: DexScreener, GeckoTerminal, Jupiter (chiave gratuita, 1 richiesta/s), RugCheck, PumpPortal, RPC pubblico Solana, CoinGecko e Kraken (cambio SOL/EUR).

### 1.3 Pipeline attuale

```
PumpPortal (WebSocket, nuovi token in tempo reale) ─┐
DexScreener (profili, coppie)                        ├─> Scanner ogni ~60 s (in pratica 1,5–2 min)
GeckoTerminal (nuovi pool, trending, candele)        ┘      │
                                                            ├─ arricchimento: Jupiter (prezzi, quote reali), RugCheck,
                                                            │   RPC (mint, largest accounts), GeckoTerminal (candele, pool, trade)
                                                            ├─ punteggio 0–100 (7 categorie, pesi fissi) + filtri di esclusione
                                                            ├─ strategie A–E → segnale → controllo dei prezzi → risk manager → paper (quote Jupiter)
                                                            └─ Laboratorio (stesse strategie, senza limiti, modello AMM)
Monitor posizioni ogni 20 s (prezzi DexScreener) → uscite (stop, take profit, trailing, volume, alert on-chain)
```

### 1.4 Dati già raccolti (senza survivorship bias, perché registrati in avanti)
- Dal 1° novembre: **circa 1.700 token** seguiti e registrati sulla VPS. Prima ce n'erano altri, raccolti dalle esecuzioni su GitHub e importati.
- Per ogni token: snapshot nel tempo, candele a 1 minuto (finestra di 6 ore), segnali con dati e motivi, e **esito dei segnali a 15 minuti, 1, 4 e 24 ore** (anche per quelli rifiutati).
- È la base giusta per la calibrazione statistica: va arricchita con dati sui wallet e conservata più a lungo, perché oggi gli snapshot si cancellano dopo 14 giorni.

### 1.5 Risultati finora (statistica onesta)
- **Portafoglio principale**: 12 operazioni chiuse, capitale +4,13%.
- **Rendimento per operazione**: media +9,9%, mediana +0,3%, deviazione standard 33,2%, **IC 95% [−11,2%; +31,0%]**.
- **Non significativo.** Il risultato dipende da 2 operazioni: MOVEMBER +89% e ANAKIN +52%.
- **Laboratorio**: ripartito il 2 novembre alle 16:20 dopo la correzione del prezzo d'ingresso. I numeri precedenti erano falsati e sono stati cancellati.

---

## 2. Funzionalità presenti (cosa NON va ricostruito)

| Area | Stato | Dettaglio |
|---|---|---|
| Discovery | ✅ funziona | PumpPortal in tempo reale, DexScreener, GeckoTerminal |
| Raccolta e storico | ✅ funziona | PostgreSQL, snapshot nel tempo, candele, eventi; backup giornaliero (sullo stesso disco) |
| Sicurezza di base | 🟡 parziale | mint/freeze authority, estensioni Token-2022 pericolose (dato RugCheck), percorso di vendita (Jupiter), impatto in vendita, liquidità, LP, controllo prezzi incoerenti |
| Concentrazione holder | 🟡 parziale | RugCheck (top 10, dev %, insider %), oppure RPC `getTokenLargestAccounts` come ripiego approssimato |
| Wash trading | 🟡 parziale | `wash_metrics` sugli scambi GeckoTerminal (trader unici, operazioni avanti e indietro, quota dei primi 5) |
| Wallet e deployer | 🔴 assente | il deployer viene salvato, ma non analizzato; nessuno storico dei wallet |
| Bonding curve | 🟡 minimo | riserve virtuali e prezzo da PumpPortal; gli scambi in tempo reale vengono raccolti solo per 20 token, tenuti in memoria e **mai analizzati** |
| Simulazione | 🟡 parziale | quote Jupiter reali per acquisto e vendita (simulazione di mercato); nessuna simulazione di transazione |
| Esecuzione | 🟡 parziale | commissioni del DEX e di rete, rent, slittamento fisso 0,3%, fallimenti casuali 2%; nessun modello di latenza o congestione |
| Punteggio | 🟡 euristico | 0–100 con pesi fissi + esclusioni obbligatorie e spiegazioni; non calibrato |
| Strategie e rischio | ✅ funziona | 5 strategie, 3 profili, dimensionamento con tetto di perdita in caso di rug, uscite, kill switch |
| Paper trading | ✅ funziona | portafoglio principale + Laboratorio senza limiti; ordini idempotenti; quote reali |
| Backtest | 🟡 motore pronto, mancano i dati | walk-forward e analisi out-of-sample implementati; manca uno storico gratuito ampio |
| Monitoraggio | ✅ funziona | dashboard privata e pubblica, workflow di controllo dello stato, Telegram, log |
| Test e CI | ✅ funziona | 126 casi di test, prova generale su Ubuntu pulito, aggiornamenti controllati |

---

## 3. Problemi e punti deboli trovati

| # | Problema | Evidenza | Impatto |
|---|---|---|---|
| P1 | **Codice morto** in `onchain/wash.py` | nessuna chiamata a `early_buyer_concentration` e `coordinated_selling`; `early_buyer_cluster_pct` viene letto da filtri e punteggio (`scoring/filters.py:102`, `scoring/scorer.py:203`) ma **non viene mai calcolato** | il filtro `EARLY_CLUSTER` (sniper/bundle iniziali) non può mai scattare |
| P2 | Controllo «vendite coordinate» inattivo | `engine._onchain_alert` legge `social_metrics["coordinated_selling"]`, che nessuno scrive | protezione dichiarata ma inesistente |
| P3 | Insider e dev % delegati a **RugCheck** | `collectors/rugcheck.py` | dipendenza da un'API non ufficiale; nessun controllo indipendente |
| P4 | **Pesi del punteggio arbitrari** | `scoring/scorer.py`, `CATEGORY_WEIGHTS` | il punteggio non è una probabilità; nessuna calibrazione |
| P5 | Rischio e opportunità nello stesso numero | stesso file | un forte momentum può compensare segnali di rischio non ancora esclusi |
| P6 | **Dipendenza da GeckoTerminal** per le candele | limite non pubblicato, blocchi frequenti (codice 429) | le strategie restano senza dati; il ciclo dura 1,5–2 minuti |
| P7 | Normalizzazione dei dati debole | ieri: candele in unità sbagliata e d'ingresso del Laboratorio (corretto) | serve uno strato di validazione dati sistematico |
| P8 | Scambi PumpPortal solo in memoria, solo 20 token | `scanner/service.py` (`pump_trades`) | dati preziosi persi a ogni riavvio |
| P9 | Esecuzione semplificata | fallimenti fissi 2%, slittamento fisso 0,3% | ottimismo possibile in condizioni di rete congestionata |
| P10 | Backup sullo stesso disco della VPS | `deploy/backup.sh` | se il disco si guasta, si perdono dati e backup insieme |
| P11 | Nessun test di contratto sulle API esterne | ieri: Hetzner `/datacenters` rimosso (errore 410) | i cambiamenti delle API si scoprono solo in produzione |
| P12 | Contatore giornaliero in UTC | il limite si azzera all'1:00 italiana | solo un fatto da documentare |
| P13 | Conservazione degli snapshot di 14 giorni | `worker.retention` | serve una conservazione più lunga (almeno aggregata) per la validazione |

---

## 4. Funzionalità mancanti rispetto all'architettura richiesta

- **Wallet intelligence propria**: primi acquirenti, chi finanzia chi, cluster con confidenza, storico dei deployer, wallet riutilizzati tra più token.
- **Analisi della bonding curve**: velocità di riempimento, acquirenti indipendenti stimati, quota di volume dei cluster, distribuzione degli acquisti, pressione nel tempo.
- **Rilevazione dei bundle**: acquisti nello stesso slot della creazione, tip Jito, finanziamento comune.
- **Sicurezza on-chain indipendente** da RugCheck: autorità, estensioni Token-2022, metadati modificabili, programma proprietario, stato della LP dopo la migrazione.
- **Simulazione della transazione** (`simulateTransaction`), separata dalla simulazione di mercato e dalla verifica di sicurezza.
- **Modello di esecuzione** con fee di priorità e tip reali, latenza dei dati misurata e scenari di congestione.
- **Due punteggi separati, Rischio e Opportunità, calibrati statisticamente** e spiegabili.
- **Feature store «point-in-time»**: le caratteristiche salvate come erano al momento della decisione, per evitare il data leakage.
- **Registro degli esperimenti e regola di promozione** delle configurazioni, solo dopo validazione fuori campione.
- **Backup fuori dalla VPS** e test di contratto sulle API.

---

## 5. Ricerca: le migliori risorse gratuite

> I numeri provengono dalle fonti indicate; dove sono in conflitto lo dico. «Terza parte» significa una fonte non ufficiale.

### 5.1 Blockchain e RPC

| Servizio | Costo | Limiti gratuiti | Registrazione / chiave | Note e limitazioni | Verdetto per noi |
|---|---|---|---|---|---|
| **RPC pubblico Solana** (`api.mainnet-beta.solana.com`) | 0 € | circa 100 richieste ogni 10 s per IP, circa 40 per lo stesso metodo (**solo fonti terze**, in conflitto) | no / no | senza garanzie, «non per produzione»; risponde 429 quando superi il limite ([OnFinality](https://onfinality.io/en/rpc-assistant/solana-public-rpc-endpoints), [GetBlock](https://getblock.io/blog/public-solana-rpc-url-everything-you-need-to-know/)) | ✅ base, con budget per metodo e cache |
| **WebSocket pubblico Solana** | 0 € | non documentato | no | `logsSubscribe` sul programma pump.fun genera molto traffico e la connessione può cadere | 🧪 solo come ripiego |
| **Helius** piano Free | 0 € | **1M crediti al mese, 10 richieste/s**; limiti più stretti su alcuni metodi (per esempio DAS 2/s, secondo una fonte terza) | sì / sì | **l'endpoint «funded-by» del Wallet API è riservato ai piani a pagamento** (sul Free risponde 403) ([prezzi](https://www.helius.dev/pricing), [piani](https://www.helius.dev/docs/billing/plans), [Wallet API](https://www.helius.dev/docs/wallet-api/overview.md)) | ✅ come seconda fonte RPC (registrazione gratuita) |
| **QuickNode** | — | 10M crediti e 15 richieste/s, ma **è una prova di 1 mese**, non un piano gratuito permanente | sì | ([prezzi](https://www.quicknode.com/pricing?via=Talix), [CostBench](https://costbench.com/software/blockchain-nodes/quicknode/free-plan/)) | ⚠️ non adatto a un uso 24/7 gratuito |
| **Alchemy** Free | 0 € | 30M unità di calcolo al mese, 300–500 al secondo (fonti in conflitto) | sì / sì | ([Alchemy](https://support.alchemy.com/articles/5827006872-what-is-included-in-the-free-tier)) | 🧪 riserva |
| **Chainstack** Developer | 0 € | 3M unità al mese; richieste al secondo su mainnet **in conflitto (0,5 o 25)** | sì / sì | ([limiti](https://docs.chainstack.com/docs/limits), [prezzi](https://chainstack.com/pricing/)) | 🧪 riserva |
| **dRPC** Free | 0 € | 50M–210M unità al mese (fonti in conflitto) | sì | ([CostBench](https://costbench.com/software/blockchain-nodes/drpc/free-plan/)) | 🧪 riserva |
| **Yellowstone gRPC** | — | **nessun piano gratuito stabile trovato**; QuickNode indica 100K risposte al giorno su piani free/trial | — | ([Chainstack](https://chainstack.com/learn/compare/best-yellowstone-grpc-providers-solana-2026/), [QuickNode](https://marketplace.quicknode.com/add-on/yellowstone-grpc)) | 💸 non serve: PumpPortal copre il tempo reale |

### 5.2 Trading e DEX

| Servizio | Costo | Limiti gratuiti | Chiave | Note | Verdetto |
|---|---|---|---|---|---|
| **Jupiter** | 0 € | 0,5 richieste/s senza chiave, **1 richiesta/s con la chiave gratuita** (già attiva); `lite-api` in dismissione, data ancora da annunciare | sì (gratuita) | ([setup](https://dev.jup.ag/portal/setup), [changelog](https://developers.jup.ag/changelog/2025-11)) | ✅ già in uso |
| **PumpPortal** Data API | 0 € | «gratis, con limiti» non quantificati; `subscribeNewToken`, `subscribeTokenTrade`, `subscribeAccountTrade` | no | non ufficiale (non è pump.fun) ([README](https://github.com/TrustPump/Pump-Fun-API)) | ✅ fonte principale per curva e acquirenti; capacità da misurare |
| **DexScreener** | 0 € | 60 richieste/min su profili e boost (ufficiale); circa 300/min sui dati DEX (fonte terza) | no | ([API](https://docs.dexscreener.com/api/reference)) | ✅ già in uso |
| **GeckoTerminal** pubblico | 0 € | limite non pubblicato | no | blocchi 429 frequenti; mitigati dal ritmo adattivo | ✅ con prudenza |
| **CoinGecko Demo** | 0 € | **10.000 chiamate al mese**, 100 al minuto; include gli endpoint on-chain | sì | 10k al mese bastano per circa 14 chiamate l'ora ([CoinGecko](https://www.coingecko.com/en/api/acquisition/entry-plans?locale=en)) | ⚠️ troppo poco come fonte principale; utile come riserva |
| **Birdeye** Standard | 0 € | **30.000 unità al mese, 1 richiesta/s**, API dei wallet 30 al minuto | sì | ([prezzi](https://docs.birdeye.so/docs/pricing), [rate limit](https://docs.birdeye.so/docs/rate-limiting)) | ⚠️ troppo poco per un uso 24/7 |
| **Raydium** API v3 | 0 € | limite progressivo per IP (dietro Cloudflare), circa 10/s secondo una fonte terza | no | ([docs](https://docs.raydium.io/sdk-api/rest-api)) | 🧪 per dati sui pool non pump.fun |
| **Meteora / Orca** | 0 € | non trovati documenti ufficiali sui limiti | no | | 🧪 da verificare all'integrazione |
| **Moralis** Free | 0 € | 40.000 unità al giorno; endpoint dedicati pump.fun (costo per endpoint da verificare) | sì | ([prezzi](https://www.moralis.com/pricing/), [unità di calcolo](https://docs.moralis.com/web3-data-api/solana/resources/compute-units-cu)) | 🧪 riserva per metadati e stato della curva |
| **Bitquery** | — | 1.000 punti di prova, 10 richieste al minuto; streaming solo a pagamento | sì | ([pump.fun API](https://bitquery.io/products/pumpfun-api)) | 💸 |
| **Dune** | — | da settembre 2026 il piano gratuito diventa **di sola visualizzazione** per gli account creati prima del 21/7/2026; i nuovi account partono con una prova di 14 giorni e 2.500 crediti | sì | ([Crypto Briefing](https://cryptobriefing.com/dune-free-plan-view-only-access/), [docs crediti](https://docs.dune.com/resources/credits-billing/how-credits-work)) | ⚠️ non più affidabile come fonte gratuita di storico |

### 5.3 Sicurezza

| Strumento | Costo | Limiti | Note | Verdetto |
|---|---|---|---|---|
| **RugCheck** API | 0 € | non documentati (non ho trovato la documentazione ufficiale) | già in uso: authority, rischi, insider, top holder | ✅ come **seconda opinione**, non come fonte unica |
| **GoPlus** Security | 0 € | 150K unità al mese, 30K al giorno (tabella del sito poco leggibile) | copre anche Solana, ma con analisi meno approfondite secondo una fonte terza ([GoPlus](https://gopluslabs.io/security-api)) | 🧪 terza opinione |
| **RPC `simulateTransaction`** | 0 € | come l'RPC | simula senza inviare; `sigVerify` e `replaceRecentBlockhash` non sono compatibili tra loro ([Solana docs](https://solana.com/docs/rpc/http/simulatetransaction.md), [Chainstack](https://docs.chainstack.com/reference/solana-simulatetransaction.md)) | ✅ tecnicamente disponibile; 🧪 per il test di vendita |
| **Controlli on-chain propri** (account del mint, Token-2022, metadati Metaplex) | 0 € | 1–3 chiamate RPC per token | **permanent delegate** (lo scammer brucia i token dal tuo wallet), **transfer hook** (può bloccare le vendite), **transfer fee** (tassa nascosta), **default frozen** ([Cointelegraph](https://cointelegraph.com/news/new-solana-scam-burn-tokens-from-inside-sol-wallets), [Zealynx](https://www.zealynx.io/glossary/transfer-hook)); `isMutable` e update authority dei metadati ([Metaplex](https://developers.metaplex.com/token-metadata/update)) | ✅ da implementare (oggi dipendiamo da RugCheck) |

### 5.4 Wallet intelligence: codice aperto e letteratura

| Risorsa | Cosa offre | Limiti | Verdetto |
|---|---|---|---|
| [GODMODE](https://github.com/netvyxe/godmode) | cluster di bundle tra i top holder (stessa fonte di finanziamento), tracciamento della catena dei finanziamenti | si basa su Helius; aggiornato circa 7 mesi fa; qualità da verificare | 🧪 riferimento per il metodo, non come dipendenza |
| [solana-sybil-score](https://github.com/opsec-bot/solana-sybil-score) | punteggio Sybil spiegabile, finanziatori condivisi | non segue i finanziamenti in USDC; non vede le farm finanziate da exchange | 🧪 riferimento |
| [Solana Forensic Analysis Tool](https://github.com/apostleoffinance/Solana-Forensic-Analysis-Tool) | DBSCAN su grafo + tracciamento dei finanziamenti | orientato alle frodi in generale | 🧪 riferimento |
| Metodo **Arbitrum / OpenBlock**: primo finanziamento + Louvain sul grafo dei trasferimenti | metodo documentato e riproducibile con `python-louvain`/`networkx` (gratuiti) ([forum Arbitrum](https://forum.arbitrum.foundation/t/openblock-labs-stip-efficacy-sybil-analysis-2-24/21441)) | si aggira finanziando ogni wallet da un exchange ([Wormhole](https://insightfulinfo.substack.com/p/breaking-down-the-wormhole-airdrop)) | ✅ metodo valido, con limiti noti |
| **Trusta**: Louvain/K-Core + filtro comportamentale | descritto in [ethresear.ch](https://ethresear.ch/t/trusta-s-ai-and-machine-learning-framework-for-robust-sybil-resistance-in-airdrops/16828) | codice non pubblico | ✅ come metodo |
| **MemeTrans** (arXiv 2602.13480) | **oltre 41.000 lanci, più di 200M transazioni, 122 caratteristiche, tracce dei bundle**; codice e dati pubblici ([paper](https://arxiv.org/html/2602.13480v1), repo `git-disl/MemeTrans`) | licenza e periodo coperto da verificare | ✅ **fonte molto utile** per progettare le caratteristiche e per un test esterno |
| **Catching the Rug** (arXiv 2608.20271) | 6,4M memecoin, XGBoost il migliore, finestra di previsione di 5 minuti; AUC-PR circa 0,80 secondo una recensione terza ([paper](https://arxiv.org/abs/2608.20271)) | numeri da controllare nel testo integrale | ✅ conferma che il machine learning precoce ha senso |
| **From Hype to Collapse** (arXiv 2603.24625) | 76.469 token candidati a rug su Orca, Raydium e Meteora; tasso di falsi positivi controllato a mano 0,26% ([paper](https://arxiv.org/pdf/2603.24625)) | non riguarda pump.fun | ✅ definizioni di rug utili per le etichette |

### 5.5 Jito ed esecuzione

| Risorsa | Costo | Note | Verdetto |
|---|---|---|---|
| **8 account per le tip Jito** (fissi, ottenibili con `getTipAccounts`) | 0 € | una tip è un trasferimento di SOL verso uno degli 8 account ([Jito docs](https://docs.jito.wtf/lowlatencytxnsend/)) | ✅ **rilevabile on-chain** gratis |
| **Tip floor API** (`bundles.jito.wtf/api/v1/bundles/tip_floor`) | 0 € | percentili delle tip arrivate a destinazione ([Chainstack](https://chainstack.com/jito-explained-bundles-tips-mev-solana/)) | ✅ costo realistico delle tip nella simulazione |
| `getRecentPrioritizationFees` (RPC standard) | 0 € | fee di priorità recenti | ✅ costo realistico delle fee |
| Riconoscere i bundle on-chain | — | **non esiste un marcatore ufficiale «bundle»** nei dati on-chain | 🧪 si stima con indizi: stesso slot della creazione, tip Jito, finanziatore comune, importi simili |

### 5.6 Intelligenza artificiale

| Opzione | Costo | Fattibilità sulla VPS CX23 | Verdetto |
|---|---|---|---|
| LLM a pagamento (Claude, OpenAI, …) nel ciclo operativo | a consumo | — | ❌ escluso dalla direttiva |
| **Ollama** con modello da 3B (per esempio Qwen 2.5 3B) | 0 € | circa 3,3 GB di RAM e 7–9 token/s su **4 vCPU** ([benchmark](https://github.com/nandan2003/edge-cpu-inference), [guida](https://azdigi.com/en/blog/kien-thuc-vps/installing-ollama-on-vps-ubuntu-run-private-ai-in-15-minutes)): **non ci sta** accanto al bot sulla nostra VPS (2 vCPU / 4 GB) | ⚠️ solo sul tuo PC, per analisi offline facoltative |
| **ML classico** (scikit-learn, LightGBM/XGBoost, regressione logistica; spiegazioni con SHAP) | 0 € | addestramento offline (PC o GitHub Actions), uso leggero sulla VPS | ✅ **la scelta giusta** (coerente con la letteratura) |

---

## 6. Valutazione delle idee dell'altro sviluppatore

### A. Wallet intelligence e tracciamento dei deployer
- **Valore: ✅ verificato dalla letteratura.** In MemeTrans gli insider dei token ad alto rischio usano più spesso account in bundle per nascondere la concentrazione, e i primi 10 e 20 acquirenti detengono 17 e 19 punti di supply in più.
- **Fattibile gratis, ma solo a imbuto.** Costo per un token analizzato a fondo, stimato con 20 primi acquirenti:
  - circa 22 chiamate per ricostruire i primi acquirenti (firme sull'account della bonding curve + transazioni);
  - circa 40 chiamate per risalire a chi li ha finanziati (primo SOL ricevuto da ciascuno);
  - 5–10 chiamate per lo storico del deployer.

  In totale **circa 65–80 chiamate**. L'RPC pubblico concede circa 40 chiamate allo stesso metodo ogni 10 s, come detto non verificato. Il collo di bottiglia è `getTransaction`, intorno a 4 al secondo: **tra 50 e 150 token l'ora nel caso migliore**, molti meno nella pratica.
- **Il sistema probabilistico richiesto è il disegno corretto.** I collegamenti tra due wallet vanno pesati con più indizi, ciascuno con la sua confidenza:
  - stesso finanziatore diretto;
  - finanziamento ravvicinato nel tempo;
  - importi simili;
  - acquisto nello stesso slot;
  - tip Jito nello stesso slot;
  - wallet nuovi;
  - presenza degli stessi wallet su più token.
- **Due trappole da gestire:**
  1. **I «finanziatori hub»** (exchange, bridge, servizi) finanziano migliaia di wallet non collegati tra loro. Si riconoscono dal numero altissimo di wallet finanziati, e i collegamenti che passano da loro vanno **scartati** o pesati molto poco.
  2. **Chi finanzia ogni wallet direttamente da un exchange sfugge** all'analisi dei finanziamenti, come riconosciuto anche nel caso Wormhole. Va compensato con indizi di comportamento: tempistica e slot.

**Verdetto: ✅ da fare, ma 🧪 l'efficacia va misurata sui nostri dati prima di farla pesare sulle decisioni.**

### B. Bonding curve e compratori «organici»
- **L'ipotesi è plausibile e misurabile**: curva riempita in fretta, ma da pochi wallet collegati, quindi attività artificiale.
- Su pump.fun i dati servono gratis: PumpPortal fornisce gli scambi con wallet e importi, e le riserve virtuali della curva.
- **Caratteristiche da calcolare in finestre di 1, 5 e 15 minuti:**
  - velocità di riempimento della curva;
  - acquirenti unici e **acquirenti indipendenti stimati** (unici meno quelli nei cluster);
  - quota di volume dei cluster;
  - indici di concentrazione degli acquisti (HHI/Gini);
  - rapporto tra acquisti e vendite e sua evoluzione;
  - quota di supply dei primi N acquirenti.
- **Jito e bundle:**
  - le tip sono **identificabili** con certezza;
  - **la tip da sola non è un segnale di truffa**, perché è normale per far arrivare prima la transazione;
  - un indizio forte è un acquisto **nello stesso slot della creazione**, soprattutto se il wallet è stato finanziato dal deployer o da un suo finanziatore.
- La curva va trattata come **un'ipotesi da validare**: prima si registrano le caratteristiche, poi se ne misura il potere predittivo sugli esiti (rug, prezzo a 1 e 24 ore), con divisione temporale dei dati.

**Verdetto: 🧪 da sperimentare, con priorità alta.** È il miglior rapporto tra valore e costo, perché i dati sono già gratuiti.

### C. Anti-rug e analisi del deployer
- **Già presenti**, in parte via RugCheck: liquidità, authority, percorso di vendita, impatto in vendita.
- **Da aggiungere, con controlli propri on-chain:**
  - estensioni Token-2022 lette direttamente dall'account del mint (permanent delegate, transfer hook, transfer fee, default frozen);
  - metadati modificabili (`isMutable` e update authority);
  - programma proprietario del token: Token classico o Token-2022;
  - stato della LP dopo la migrazione su PumpSwap: le fonti dicono che la pool viene migrata per intero e pump.fun non la tocca, ma **va verificato on-chain chi controlla i token LP**;
  - storico del deployer: quanti token ha creato e quanti sono «morti» o in rug entro 24 ore;
  - quota di supply del deployer e dei wallet collegati.
- **«Analisi delle prime 24 ore»** è in contraddizione con l'ingresso anticipato. Ha senso come caratteristica di rischio del **deployer**, misurata sui suoi token passati, non sul token corrente.

**Verdetto: ✅ da fare.** I controlli devono essere specifici per programma: pump.fun curve, PumpSwap, Raydium/Meteora, Token-2022.

### D. Simulazione prima dell'acquisto
Va mantenuta la distinzione che chiedi, perché sono tre cose diverse:
1. **Simulazione di mercato** (già presente): quote Jupiter reali per acquisto e vendita, con impatto e commissioni.
2. **Simulazione di transazione** (nuova): si costruisce la transazione di vendita, per esempio con Jupiter, per conto di **un wallet che possiede davvero il token** (un top holder), e la si simula via RPC senza firma. Scopre transfer hook che bloccano, account congelati ed errori del programma.
   - Limite: Jupiter consente 1 richiesta/s; inoltre serve un detentore valido, e su pump.fun all'inizio i detentori sono pochi.
3. **Verifica di sicurezza** (controlli on-chain del punto C).

**Avvertenza giusta (la tua):** una simulazione riuscita **non** garantisce di poter vendere dopo, allo stesso prezzo.

**Verdetto:** mercato ✅, transazione 🧪, sicurezza ✅.

### E. Qualità dell'esecuzione e Jito
- **Gratis e realistico**: fee di priorità recenti, minimo delle tip Jito, **latenza dei nostri dati** (l'ora del blocco confrontata con l'ora in cui riceviamo l'evento) e commissioni reali per programma.
- **Non misurabile senza transazioni reali**: probabilità di arrivo a destinazione, fallimenti per congestione, slittamento tra il momento della quota e quello dell'esecuzione.

  In DEMO vanno **modellati con ipotesi esplicite**, eseguendo i risultati in 3 scenari (ottimista, base, conservativo) e mostrando quanto cambiano.

**Verdetto: 🧪 modello simulato con dati reali sui costi.** La parte di arrivo delle transazioni resta un'ipotesi dichiarata.

---

## 7. Architettura consigliata

**Principio guida: imbuto a livelli.** L'analisi costosa si fa solo su chi supera i livelli economici. Ogni livello è un modulo indipendente, testabile e sostituibile.

```
L0 SCOPERTA (tutti i lanci, gratis, tempo reale)
   PumpPortal subscribeNewToken + DexScreener/Gecko per i token non pump.fun
   ↓ registra: deployer, acquisto iniziale, riserve curva, ora    [nuovo: persistenza eventi]
L1 RACCOLTA RAPIDA (centinaia/ora, 1–3 chiamate RPC)
   account del mint (authority, Token-2022), metadati, DexScreener, RugCheck, cache
   ↓ esclusioni obbligatorie (honeypot, authority, estensioni pericolose…)
L2 CURVA E ACQUIRENTI (decine/ora, dati quasi tutti già gratuiti)
   scambi PumpPortal persistiti, finestre 1/5/15 min, primi N acquirenti, slot, tip Jito
L3 WALLET INTELLIGENCE (decine/ora, 60–80 chiamate/token, con budget)
   finanziatori a profondità 1–2, rilevamento hub, cluster con confidenza, storico deployer
L4 SIMULAZIONE
   mercato (Jupiter) · transazione (simulateTransaction) · costi di esecuzione (fee, tip, latenza)
L5 PUNTEGGI
   Rischio (esclusioni + modello) │ Opportunità (modello) → spiegazioni per caratteristica
L6 DECISIONE → PAPER TRADING (principale + Laboratorio + configurazioni sperimentali in ombra)
L7 MONITORAGGIO → ESITI → FEATURE STORE (point-in-time) → VALIDAZIONE (walk-forward, fuori campione)
```

**Nuovi moduli proposti** (affiancano quelli esistenti, senza sostituirli):
- `data_quality/`: unità, dati vecchi, divergenze tra fonti, latenza per fonte.
- `chain/rpc_pool.py`: più fornitori RPC con budget per metodo, cache e passaggio automatico a un altro fornitore in caso di errore.
- `security/onchain.py`: controlli propri, confrontati con RugCheck.
- `wallet_intel/`: primi acquirenti, grafo dei finanziamenti, hub, cluster, deployer.
- `curve_analysis/`: caratteristiche della curva e degli acquirenti indipendenti.
- `simulation/`: transazione, mercato, esecuzione con scenari.
- `scoring/risk.py` e `scoring/opportunity.py`: il punteggio attuale resta come «euristico» fino alla calibrazione.
- `research/`: feature store, etichette, valutazione walk-forward, registro esperimenti, regola di promozione.

**Nuove tabelle** (con conservazione a livelli: dettagli 30–60 giorni, aggregati per sempre):
- `wallets`
- `wallet_links`, con tipo di collegamento e confidenza
- `funding_edges`
- `token_trades`, con gli scambi iniziali
- `deployers`
- `clusters`
- `simulations`
- `feature_snapshots`
- `experiments`

**Spazio su disco:** da stimare dopo una settimana di raccolta. Oggi l'intero sistema usa 3,3 GB su 38.

---

## 8. Gap analysis

| Modulo | Stato attuale | Problema | Soluzione proposta | Costo | Priorità | Difficoltà | Test necessari |
|---|---|---|---|---|---|---|---|
| Stabilità e dati | buona | P6, P7, P10, P11 | validazione dati, test di contratto, backup fuori dalla VPS, pool RPC | 0 € | 1 | M | test sulle API con dati reali registrati, test di ripristino |
| Discovery | buona | eventi persi ai riavvii | persistenza eventi PumpPortal, contatore lanci/ora | 0 € | 2 | S | test di riconnessione e ripresa |
| Raccolta e storico | buona | conservazione 14 giorni, niente feature point-in-time | feature store + conservazione a livelli | 0 € | 2 | M | test anti-leakage (nessun dato «dal futuro») |
| Sicurezza on-chain | parziale | dipende da RugCheck | controlli propri + confronto con RugCheck | 0 € | 3 | M | dati di token reali noti (estensioni, authority) |
| Deployer intelligence | assente | — | storico deployer (eventi + RPC) | 0 € | 4 | M | casi noti con molti lanci |
| Wallet clustering | assente | — | primi finanziatori, hub, cluster con confidenza | 0 € (+ Helius free opzionale) | 4 | L | grafi sintetici con risposta nota + casi reali etichettati a mano |
| Bonding curve | minimo | dati non usati (P1, P8) | caratteristiche per finestre temporali | 0 € | 5 | M | eventi registrati riprodotti |
| Acquirenti organici | assente | — | acquirenti indipendenti stimati, quota cluster | 0 € | 5 | M | come sopra |
| Simulazione di transazione | assente | — | Jupiter + `simulateTransaction` dal wallet di un holder | 0 € | 6 | M | token con transfer hook o congelati (casi noti) |
| Esecuzione simulata | semplificata | P9 | fee e tip reali, latenza misurata, 3 scenari | 0 € | 6 | M | sensibilità dei risultati agli scenari |
| Punteggio Rischio | misto | P4, P5 | esclusioni + modello calibrato | 0 € | 7 | M | calibrazione (curva di affidabilità), test fuori campione |
| Punteggio Opportunità | misto | P4 | modello con spiegazioni per caratteristica | 0 € | 7 | M | walk-forward |
| Paper trading | buono | — | configurazioni in ombra in parallelo | 0 € | 8 | S | isolamento tra portafogli |
| Dashboard | buona | non mostra wallet e cluster | pagine Wallet/Cluster, Rischio/Opportunità, Esperimenti | 0 € | 9 | M | test di build + screenshot |
| Validazione e autonomia | motore pronto, mancano dati | campione piccolo | registro esperimenti, regola di promozione | 0 € | 10 | M | test della regola con dati sintetici |

S/M/L = difficoltà piccola, media, grande.

---

## 9. Roadmap

Ogni fase si chiude solo quando ha superato i suoi **criteri di uscita**.

1. **Fase 0 — Stabilità**
   - Cosa: validazione dati; test di contratto sulle API; backup automatico fuori dalla VPS, per esempio copiato su GitHub in un ramo privato, oppure da scaricare; pool RPC con budget; contatore dei lanci all'ora; persistenza degli eventi PumpPortal; collegare o rimuovere il codice morto (P1, P2).
   - *Uscita:* 7 giorni senza perdita di dati né blocchi prolungati; il backup si ripristina.
2. **Fase 1 — Raccolta dati per la ricerca**
   - Cosa: feature store point-in-time; conservazione a livelli; scambi iniziali dei token pump.fun salvati per tutti i token che passano il livello L1.
   - *Uscita:* almeno **2.000 token** con caratteristiche ed esiti a 24 ore.
3. **Fase 2 — Sicurezza on-chain propria**
   - *Uscita:* accordo misurato con RugCheck sui casi comuni; spiegazione per ogni caso in cui i due giudizi divergono.
4. **Fase 3 — Wallet intelligence**
   - Cosa: primi acquirenti, finanziatori, hub, cluster con confidenza, storico deployer.
   - *Uscita:* precisione dei cluster misurata su casi etichettati a mano (almeno 50) e su grafi sintetici.
5. **Fase 4 — Curva e acquirenti organici**
   - *Uscita:* report che dice, con intervalli di confidenza, quali caratteristiche separano davvero gli esiti, su dati fuori campione.
6. **Fase 5 — Simulazione** (transazione + esecuzione con 3 scenari)
   - *Uscita:* risultati del portafoglio presentati in tutti e 3 gli scenari.
7. **Fase 6 — Punteggi Rischio e Opportunità calibrati**
   - *Uscita:* sui dati di test i punteggi sono calibrati e migliori dell'euristica attuale.
8. **Fase 7 — Paper trading con configurazioni in ombra**, e **Fase 8 — dashboard** delle nuove viste.
9. **Fase 9 — Ottimizzazione e autonomia controllata**
   - Cosa: registro degli esperimenti, report automatici e **regola di promozione**.
   - La regola: almeno **N operazioni fuori campione**, rendimento netto medio con intervallo di confidenza al 95% sopra zero dopo i costi, drawdown entro il limite e risultati stabili in più periodi.
   - **Nessuna promozione automatica**: la decisione finale resta tua.

---

## 10. Stima dei costi (obiettivo zero euro)

| Voce | Costo | Obbligatoria? |
|---|---|---|
| VPS Hetzner CX23 | **7,31 €/mese** | sì, per il funzionamento 24/7. Le alternative a 0 € sono Oracle Free (che hai escluso), il PC sempre acceso o GitHub Actions (turni inaffidabili) |
| RPC pubblico, PumpPortal, DexScreener, GeckoTerminal, Jupiter (chiave gratuita), RugCheck, Raydium API, Jito tip floor | 0 € | sì |
| Helius Free | 0 € (registrazione) | **consigliata** per la capacità RPC della wallet intelligence |
| Moralis Free, CoinGecko Demo, GoPlus Free | 0 € (registrazione) | facoltative, solo come riserva |
| Librerie (networkx, python-louvain, scikit-learn, LightGBM, SHAP) | 0 € | sì, quando servono |
| LLM a pagamento | — | **escluso** |
| Birdeye, Bitquery, QuickNode, Yellowstone gRPC, Dune a pagamento | — | **non necessari** |
| **Totale** | **7,31 €/mese** | |

---

## 11. Principali rischi tecnici

| Rischio | Probabilità | Impatto | Mitigazione |
|---|---|---|---|
| Limiti RPC pubblici più bassi del previsto o variabili | alta | alto | imbuto, budget per metodo, cache, Helius free come seconda fonte, misura continua |
| API non ufficiali che cambiano o spariscono (PumpPortal, RugCheck, endpoint di pump.fun) | media | alto | test di contratto, controlli propri on-chain, più fonti |
| Falsi collegamenti tra wallet (hub, exchange) | alta | medio | rilevamento degli hub, confidenza, validazione su casi etichettati |
| Evasione (finanziamento da exchange, wallet «puliti») | alta | medio | indizi di comportamento (slot, tempistica, importi), mai una regola sola |
| Overfitting e data snooping con un campione piccolo | alta | alto | feature store point-in-time, walk-forward, regola di promozione, niente ottimizzazione sui dati già visti |
| Simulazione troppo ottimistica | media | alto | 3 scenari, scenario conservativo come riferimento |
| Risorse della VPS (CPU per grafi e ML) | bassa | medio | elaborazione incrementale; addestramento offline |
| Disco pieno con gli scambi registrati | media | medio | conservazione a livelli, aggregazione, monitoraggio dello spazio |
| Termini d'uso dei servizi gratuiti (uso commerciale) | media | basso (uso personale e demo) | verificare i termini prima di qualsiasi uso commerciale |

---

## 12. Priorità di implementazione

1. **Fase 0**: validazione dati, persistenza eventi, backup fuori dalla VPS, test di contratto, pool RPC. È poco visibile, ma ogni altra cosa dipende da questo.
2. **Feature store + raccolta degli scambi della curva** (Fase 1). I dati servono settimane per accumularsi: prima si parte, meglio è.
3. **Sicurezza on-chain propria** (Fase 2): costo basso, riduce la dipendenza da RugCheck.
4. **Curva e acquirenti organici** (Fase 4). Insieme alla raccolta del punto 2, ha il miglior rapporto valore/costo.
5. **Wallet intelligence a imbuto** (Fase 3), con Helius free se vuoi più capacità.
6. Simulazione, punteggi calibrati e validazione, **solo quando ci saranno almeno qualche migliaio di token etichettati**.

## 13. Cosa sconsiglio, in modo critico

- **Usare i punteggi come probabilità** prima di calibrarli.
- **Inseguire Yellowstone gRPC o fornitori a pagamento**: PumpPortal più RPC bastano per una demo.
- **Mettere un LLM nel ciclo decisionale**: non aggiunge capacità predittiva misurabile, e sulla VPS non c'è spazio.
- **Scartare automaticamente ogni bundle o ogni tip Jito**: produrrebbe molti falsi positivi.
- **Dichiarare un vantaggio prima di circa 150–200 operazioni chiuse fuori campione**, a meno che il vantaggio vero non sia molto grande.
