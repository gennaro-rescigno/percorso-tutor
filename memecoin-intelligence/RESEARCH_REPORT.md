# RESEARCH_REPORT — Memecoin Intelligence & Trading System

**Data della ricerca:** 1 novembre 2026
**Ambito:** memecoin su Solana (con estendibilità a Ethereum/Base), capitale di riferimento 2 SOL.
**Stato:** ricerca preliminare allo sviluppo (Fase 1 + Fase 3 dell'ordine di esecuzione).

---

## 0. Sintesi esecutiva (da leggere prima di tutto)

1. **Il tasso base è brutale.** Su ~7 milioni di token lanciati su Pump.fun tra gen-2024 e mar-2025, Solidus Labs
   ha classificato il **98,6%** come rug pull o pump-and-dump, e solo **~97.000 token (1,4%)** mantenevano più di
   1.000 $ di liquidità [S1]. Il tasso di "graduation" (token che completano la bonding curve) è stato per lunghi
   periodi **sotto l'1–2,5%**, salito a **4,7–6,7%** a fine luglio 2026 dopo il meccanismo BOOST [S2][S3].
   → Il sistema deve essere prima di tutto un **filtro di esclusione**: rifiuterà >99% dei token. Questo è il
   comportamento corretto, non un difetto.

2. **La maggior parte dei trader perde.** Solo lo **0,4%** dei ~13,4 milioni di wallet Pump.fun aveva realizzato
   più di 10.000 $ di profitto (Dune, gen-2025) [S4]; nello studio CoinGecko la quota di wallet in profitto mensile
   raramente supera il 50% e tocca il **30,1%** a giugno 2025 [S5]. Chi guadagna in modo sistematico sono le
   infrastrutture (launchpad, DEX, bot) [S6] e chi ha vantaggi informativi/di latenza (insider, sniper, bundler).

3. **La manipolazione è misurabile.** Wash trading ≥ **17% delle transazioni** in uno studio accademico su larga
   scala [S7]; deployer che finanziano sniper nello stesso blocco del lancio (~1,75% dei lanci, >15.000 SOL di
   profitto in un mese) [S8]; coorti coordinate di sniper persistenti [S9]; cinque classi di manipolazione su
   15 milioni di coin (wash trading, offuscamento del creatore, vendita coordinata, copycat, manipolazione social)
   [S10]. → Volume, numero di transazioni e menzioni **non vanno mai presi al valore nominale**.

4. **I casi famosi condividono condizioni necessarie, non sufficienti.** PEPE (LP bruciata, contratto rinunciato,
   93% della supply in LP, nessuna presale) [S11], BONK (50% della supply distribuita via airdrop a una
   community ampia) [S12], WIF (lancio fair su DEX a nov-2023, crescita su 3–5 mesi) [S13]: distribuzione ampia,
   assenza di controllo del team sulla supply, liquidità permanente. Ma **la quasi totalità dei token falliti su
   Pump.fun ha le stesse caratteristiche contrattuali** (mint authority revocata di default). Queste
   caratteristiche servono come **filtri di sicurezza**, non come fonte di alpha.

5. **I disastri condividono una firma molto chiara: concentrazione.** LIBRA: ~82% della supply in un unico
   cluster di wallet, 87–107 M$ estratti tramite pool unilaterali [S14]; HAWK: 80–96% in mano a insider/sniper,
   −90% in 20 minuti [S15][S16]; MELANIA: ~90–92% in wallet del team [S17]; TRUMP+MELANIA: 94% della supply ai
   whale [S18]. → La **concentrazione per cluster di wallet** (non per singolo wallet) è il segnale di rischio
   più solido trovato in letteratura e nei casi studio.

6. **Il momentum esiste ma è più debole sulle small cap.** Nella letteratura accademica sulle crypto, momentum e
   attenzione degli investitori spiegano i rendimenti cross-section [S19][S20], ma il momentum è
   **molto più forte sulle large cap che sulle small cap** [S19]. Sulle memecoin micro-cap non si può assumere
   la persistenza del trend: va dimostrata con backtest out-of-sample.

7. **I dati storici gratuiti non bastano per un backtest completo "senza bias".** OHLCV storico esiste
   (GeckoTerminal, 6 mesi sul piano gratuito) [S21], ma **holder, distribuzione, wallet, social e liquidità
   point-in-time non sono disponibili storicamente gratis**. La soluzione adottata: il sistema registra da subito
   **ogni token scoperto con snapshot point-in-time**, inclusi quelli che moriranno, costruendo un dataset
   privo di survivorship bias. Il backtest "completo" diventa possibile dopo alcune settimane di raccolta.

8. **Il social gratuito nel 2026 è quasi sparito.** X API: dal 6 feb 2026 pay-per-use (≈0,005 $ per post letto),
   nessun piano gratuito per nuovi sviluppatori [S22]. Reddit: 100 query/min con OAuth, solo uso non commerciale,
   con politiche in evoluzione [S23]. → Il punteggio social è **a bassa copertura** e non può pesare quanto
   ipotizzato inizialmente; quando manca, il sistema lo dichiara e **non lo trasforma in un segnale positivo**.

9. **Vincolo di questo ambiente di sviluppo:** la policy di rete del container cloud in cui è stato sviluppato il
   progetto **blocca** api.dexscreener.com, api.geckoterminal.com, lite-api.jup.ag, api.rugcheck.xyz, pump.fun,
   RPC Solana e anche il fetch diretto di arxiv.org. La ricerca è stata condotta tramite motore di ricerca
   (riassunti di risultati), quindi i numeri riportati provengono da sintesi di fonti, non da lettura integrale
   dei documenti originali. Dove le fonti divergono, lo indico.

---

## 1. Metodologia

- **Strumenti:** ricerca web (risultati sintetizzati). Il download diretto di pagine (WebFetch) e delle API è
  stato bloccato dall'ambiente; nessun dato di mercato è stato scaricato o simulato come se fosse reale.
- **Classi di affidabilità usate nel registro fonti (§12):**
  - **A** — fonte primaria: paper peer-reviewed o preprint accademico, documentazione ufficiale.
  - **B** — società di ricerca/analytics o testata affidabile che cita dati propri (Chainalysis, Solidus,
    Bubblemaps, The Block, Decrypt, CoinGecko Research).
  - **C** — blog secondari, guide di vendor, aggregatori; utili ma da verificare.
  - **D** — aneddotico o conoscenza pregressa non riverificata in questa sessione.
- **Regola:** ogni "pattern" diventa un'**ipotesi testabile** (§5) con una definizione numerica e una procedura
  di verifica. Nessuna soglia è considerata vera finché il backtest out-of-sample non la conferma.
- **Bias della ricerca stessa:** i casi studio famosi sono, per costruzione, sopravvissuti. Li uso per estrarre
  *condizioni necessarie e segnali di rischio*, mai come prova che una caratteristica "predice" un 100x.

---

## 2. Struttura del mercato memecoin su Solana (2024–2026)

### 2.1 Launchpad e ciclo di vita di un token

1. **Creazione su launchpad** (Pump.fun, LetsBonk, altri). Il token nasce su una **bonding curve**:
   un AMM a riserve virtuali in cui il prezzo sale con gli acquisti. Mint authority e freeze authority sono
   gestite dal programma del launchpad (revocate per i token standard).
2. **Graduation / migrazione:** al completamento della curva (≈85 SOL raccolti secondo una fonte secondaria [S3])
   la liquidità migra su un DEX. Da marzo 2025 Pump.fun migra sul proprio DEX **PumpSwap** [S24].
   A luglio 2026 il meccanismo **BOOST** ha reindirizzato ~20% della liquidità di migrazione in acquisti
   automatici nei primi 5 minuti dopo la graduation, con burn dei token acquistati [S2].
3. **Fase DEX:** trading su PumpSwap/Raydium/Meteora/Orca, aggregato da Jupiter.
4. **Destino tipico:** morte entro ore/giorni (la stragrande maggioranza); una minoranza sopravvive; una
   frazione minuscola diventa una memecoin "affermata".

**Quota di mercato dei launchpad:** molto instabile. LetsBonk ha superato Pump.fun a metà 2025 (fino a ~64–70%
dei token graduati), poi Pump.fun ha ripreso il primo posto (quota passata dal 5% al 90% in due settimane ad
agosto 2025) [S25]. → L'architettura deve essere **multi-launchpad**; dipendere da un solo launchpad è un
rischio operativo.

### 2.2 Commissioni (impatto diretto sul backtest)

| Voce | Valore trovato | Affidabilità | Nota |
|---|---|---|---|
| Fee base Solana | 5.000 lamport per firma (0,000005 SOL) | B/C [S26] | Fissa da protocollo |
| Priority fee | variabile (CU price × CU) | C [S26] | Esempio di lancio "caldo": ~0,00005 SOL |
| Jito tip | opzionale, esempio ~0,005 SOL in lanci affollati | C [S26] | Non addebitato se la tx fallisce |
| Bonding curve Pump.fun | 1,25% totale (0,30% creator + 0,95% protocollo) dal 13/05/2025 secondo una fonte; ~1% secondo un'altra | C [S27] | **Fonti in conflitto** → nel modello uso 1,25% (conservativo) |
| PumpSwap | da 1,25% subito dopo la graduation fino a un minimo di 0,30% (25 scaglioni per market cap) secondo una fonte; 0,25% flat secondo un'altra | C [S27] | **Fonti in conflitto** → default 1,0% per token giovani, 0,30% per >$20M |
| Raydium AMM v4 | 0,25% | D | Conoscenza pregressa |
| Affitto account token (ATA) | ~0,002 SOL per nuovo token account, recuperabile chiudendo l'account | D | Perso se il token diventa invendibile |

**Conseguenza quantitativa:** con fee DEX dell'1% per lato + slippage, un round-trip su un token giovane costa
facilmente **3–6%**. Una strategia con take-profit medio del +15% perde un terzo del guadagno in costi.
Il backtest **deve** modellare costi realistici; un backtest senza costi su memecoin è privo di significato.

---

## 3. Tassi base (base rates) — cosa succede a un token "medio"

| Metrica | Valore | Fonte | Affidabilità | Limiti |
|---|---|---|---|---|
| Token Pump.fun con segni di frode/rug/P&D | 98,6% (Solidus su X: 98,7%) | [S1] | B | Definizione ampia (include P&D); report letto tramite stampa |
| Token con liquidità > 1.000 $ | ~97.000 su >7 M (≈1,4%) | [S1] | B | Periodo gen-2024 → mar-2025 |
| Pool Raydium con "soft rug" | 93% di 361.000 pool | [S1] | B | Rug mediano ~2.832 $ |
| Token ancora scambiati dopo 30 giorni | 1,7% | [S28] | B | Cifra Chainalysis riportata dalla stampa |
| Pump-and-dump sul totale dell'attività | 4,52% nel 2024 (3,59% nel 2023) | [S28] | B | **Fonti in conflitto** sull'attribuzione del 3,59% |
| Tasso di graduation | ~0,8% medio; <1% per gran parte del periodo da metà 2025; 2,5% → 4,7–6,7% a fine lug-2026 | [S2][S3] | B/C | Molto dipendente dal regime e dalle regole del launchpad |
| Wallet con profitto realizzato > 10.000 $ | 55.012 su 13,4 M (0,4%) | [S4] | B | Solo profitti realizzati; include bot (contestato dal fondatore) |
| Wallet in profitto mensile | raramente >50%, minimo 30,1% (giu-2025) | [S5] | B | Esclude chi non ha mai venduto (bagholder) |
| Transazioni di wash trading | ≥17% (lower bound, ~4 M tx) | [S7] | A/C | Studio letto tramite sintesi; quota sul volume in SOL più bassa |
| Rug pull identificati su Solana 2021–2024 | 22.195 token | [S29] | A | Dataset SolRPDS, regime pre-2025 |

**Implicazione per il modello:** la probabilità a priori che un token nuovo casuale sia un buon trade è
nell'ordine di pochi punti per mille. Anche un filtro con il 90% di accuratezza sui token "cattivi" lascerebbe
passare molti falsi positivi. Per questo il sistema:
- applica **filtri di esclusione rigidi prima** dello scoring;
- richiede **più conferme indipendenti** (mercato + on-chain + liquidità);
- dimensiona le posizioni assumendo che **una parte dei trade finirà a −100%** (rug non evitabili).

---

## 4. Casi studio

> Lo scopo non è raccontare perché un token è salito (spiegazione a posteriori), ma isolare **che cosa era
> osservabile prima** della crescita e **che cosa lo distingueva dai token falliti**.

### 4.1 Memecoin esplosive

| Token | Chain / lancio | Caratteristiche osservabili PRIMA della crescita | Tempo di crescita | Fonte (affid.) |
|---|---|---|---|---|
| **DOGE** | Dogecoin, 2013 | Fork di Litecoin, community di lungo periodo; picchi legati a catalizzatori esterni (personaggi pubblici, 2021) | anni | D |
| **SHIB** | Ethereum, ago-2020 | Supply gigantesca, 50% inviata a un indirizzo terzo (Vitalik Buterin), community "ShibArmy"; listing su exchange centralizzati nel 2021 | ~1 anno | D |
| **PEPE** | Ethereum, 17 apr 2023 (alcune fonti 14 apr) | Stealth launch senza presale, **93,1% della supply in LP su Uniswap con LP token bruciati**, ownership rinunciata (una funzione blacklist usata una volta prima della rinuncia) | da 0 a ~1,6 mld $ in "settimane"; >1 mld a maggio 2023 | [S11] C (pagine exchange incoerenti) |
| **BONK** | Solana, annuncio 10 dic 2022, trading dal 30 dic 2022 | **50% della supply in airdrop** a utenti Solana (trader OpenBook, collezionisti NFT, sviluppatori): distribuzione larghissima; contesto: rimbalzo dell'ecosistema Solana dopo FTX | +~11.000% in meno di un anno (2023) | [S12] B/C |
| **WIF** | Solana, 20 nov 2023 su DEX | Lancio fair, meme semplice e culturale; un trader riporta ingresso a market cap < 200.000 $ (aneddoto); crescita progressiva | >2 mld $ dopo ~3 mesi; picco ~4,7 mld $ il 31 mar 2024 (~5 mesi); listing Binance 5 mar 2024 (+50% dopo il listing) | [S13] B/C |
| **FLOKI** | Ethereum/BSC, 2021 | Narrativa legata a un personaggio pubblico, marketing aggressivo | mesi | D |
| **BRETT** | Base, 2024 | Token "bandiera" dell'ecosistema Base, narrativa di ecosistema | mesi | D |
| **POPCAT** | Solana, fine 2023 | Meme virale preesistente; crescita lenta e graduale nel 2024 | ~1 anno | D (non verificato in sessione) |
| **PNUT** | Solana, nov 2024 | Catalizzatore di cronaca virale; **+1300% dopo l'annuncio del listing Binance**, 1,74 mld $ di MC in 24h | giorni | [S30] C |
| **FARTCOIN** | Solana (Pump.fun), ott 2024 | Lanciato su Pump.fun; >1 mld $ in ~2 mesi; ~148–160k holder; picco 2,48 $ (gen-2025, MC ~2,15–2,5 mld $), poi minimo ~217 M$ a marzo 2025 | ~2–3 mesi | [S31] B |

**Pattern comuni osservabili ex-ante:**
1. **Distribuzione larga e nessun controllo del team sulla supply** (PEPE: LP bruciata; BONK: airdrop 50%;
   WIF/FARTCOIN: lancio fair). Nessuno dei grandi successi aveva un cluster con >50% della supply.
2. **Liquidità permanente / non ritirabile** (LP bruciata o bonding curve → pool migrata).
3. **Meme culturale semplice e riconoscibile** — non quantificabile in modo affidabile con dati gratuiti.
4. **La crescita più forte è avvenuta su settimane/mesi**, non su minuti: WIF ~3–5 mesi, FARTCOIN ~2–3 mesi,
   BONK ~1 anno. Questo è il motivo per cui le strategie **Momentum, Pullback e Accumulazione** su token già
   avviati sono altrettanto importanti della strategia Early Entry.
5. **Catalizzatori esterni (listing CEX)** amplificano movimenti già in corso (WIF, PNUT), ma non sono
   prevedibili in modo affidabile e il listing arriva tipicamente *dopo* una crescita già forte.

**Attenzione al bias:** questi stessi tratti contrattuali sono presenti anche nella maggior parte dei token
morti. Sono condizioni **necessarie per non perdere tutto**, non condizioni sufficienti per guadagnare.

### 4.2 Memecoin fallite, rug pull e pump artificiali

| Caso | Meccanismo | Segnale osservabile prima del crollo | Fonte (affid.) |
|---|---|---|---|
| **SQUID** (BSC, 2021) | Honeypot: i compratori non potevano vendere; crollo ~99,99% in minuti | Impossibilità di vendere (simulazione di vendita fallita), contratto non verificato/funzioni anti-vendita | D (conoscenza pregressa) |
| **HAWK** (Solana, dic 2024) | 80–96% della supply a insider/presale/sniper; un wallet ha comprato il 17,5% in pochi secondi; −90% in ~20 minuti da ~500 M$ a ~60 M$; fee di trading del 15% | **Concentrazione estrema per cluster**, sniper nei primi secondi, fee anomale | [S15][S16] B |
| **LIBRA** (Solana, feb 2025) | Pool **unilaterali** su Meteora contenenti solo LIBRA; ~82% della supply in un cluster; 87–107 M$ estratti; 86% dei grandi wallet ha venduto in perdita | Concentrazione per cluster; struttura di liquidità anomala (pool single-sided); token aggiunti al pool 20 minuti prima dell'annuncio | [S14] B |
| **MELANIA** (Solana, gen 2025) | ~90–92% della supply in wallet del team; 30 M$ di token "community" venduti silenziosamente | Concentrazione; distribuzione reale diversa da quella dichiarata | [S17] B |
| **TRUMP** (Solana, gen 2025) | 94% della supply TRUMP+MELANIA ai whale; −50% in minuti per una vendita di un grande holder | Concentrazione; dipendenza da pochi holder | [S18] B |
| **Rug "tipico" Pump.fun/Raydium** | Soft rug (dev vende la propria quota), rug mediano ~2.800 $ | Deployer con quota rilevante, wallet collegati al deployer, volume artificiale | [S1] B |
| **Bundle / sniper finanziati dal deployer** | Wallet finanziati dal deployer comprano nello stesso blocco del lancio e vendono ai compratori successivi | Acquisti nello stesso slot del create; wallet freschi finanziati dalla stessa fonte | [S8][S9] A/C |

**Pattern comuni dei fallimenti:**
1. **Concentrazione della supply per cluster** (non per singolo wallet: gli insider frazionano su decine o
   centinaia di wallet — HAWK 285 wallet di presale [S16], LIBRA 2.101 wallet collegati [S14]).
2. **Acquisti coordinati nei primissimi secondi/blocchi** (sniper/bundle).
3. **Struttura di liquidità anomala** (pool unilaterali, LP non bloccata, liquidità piccola rispetto alla MC).
4. **Fee o meccaniche di trasferimento anomale** (fee del 15% su HAWK; su Solana: estensioni Token-2022
   come transfer fee, transfer hook, permanent delegate, stato di default "frozen").
5. **Velocità del crollo**: minuti. Uno stop loss non protegge da un rug: il prezzo "salta" lo stop.
   → Nel backtest gli stop vengono eseguiti al prezzo realmente raggiungibile (gap), non al livello teorico.

---

## 5. Pattern quantitativi da verificare (ipotesi testabili)

Ogni ipotesi ha: definizione operativa, direzione attesa, fonte che la motiva, soglia iniziale (prior) e test.
Le soglie sono **punti di partenza per il backtest**, non verità.

| ID | Ipotesi | Feature (definizione) | Prior iniziale | Motivazione | Test |
|---|---|---|---|---|---|
| H1 | Concentrazione → crollo | `top10_pct` = % supply nei 10 maggiori holder **esclusi** pool/bonding curve/burn | >30% rischio alto; >50% esclusione | LIBRA, HAWK, MELANIA, TRUMP [S14–S18] | Tasso di drawdown >80% entro 24h per decile di `top10_pct` |
| H2 | Insider/bundle → distribuzione ostile | `early_buyer_cluster_pct` = % supply acquistata nei primi N secondi da wallet con stesso finanziatore | >15% rischio alto | [S8][S9][S10] | Confronto rendimento 1h/24h tra token con/senza cluster |
| H3 | Wash trading gonfia il volume | `trades_per_trader` = tx / trader unici; `two_sided_ratio` = % wallet che comprano e vendono nella stessa finestra | tx/trader > 6 o two-sided > 40% → volume scontato | [S7][S32] | Correlazione tra volume "scontato" e rendimenti futuri vs volume grezzo |
| H4 | Attenzione organica → momentum breve | Accelerazione del volume (`vol_5m×12 / vol_1h`), crescita **compratori unici**, buy/sell 0,55–0,75 | accel > 1,5 con compratori unici in crescita | Attenzione/momentum [S19][S20] | Rendimento a 15m/1h/4h dopo il segnale, out-of-sample |
| H5 | Estensione eccessiva → inversione | `price_change_1h` molto alto | >+300% in 1h → niente ingresso Early/Momentum | [S33] fase pump/dump; regola anti-FOMO | Distribuzione dei rendimenti dopo spike estremi |
| H6 | Liquidità insufficiente → uscita impossibile | `liquidity_usd`, `liq_to_mcap`, impatto di prezzo stimato per lo stake | liquidità < 15.000 $ o impatto > 3% → esclusione | Meccanica AMM, rug Raydium [S1] | Slippage realizzato in paper trading vs stimato |
| H7 | Volatilità post-graduation | Minuti dalla migrazione | evitare i primi 5–10 min | Prime fasi più volatili, vendite dei compratori della curva [S34]; BOOST [S2] | Rendimento per bucket di minuti post-migrazione |
| H8 | Promozione a pagamento ≠ interesse organico | Boost/profili DexScreener attivi | neutro; negativo se senza conferma organica | Boost acquistabili da chiunque, nessuna garanzia [S35] | Rendimento dei token boostati vs non boostati a parità di score |
| H9 | Menzioni senza ampiezza → manipolazione | Menzioni / autori unici; età account | spike di menzioni con pochi autori → negativo | [S10] manipolazione social | Solo dove i dati social sono disponibili |
| H10 | Revival richiede base esistente | Token >7 giorni, volume 24h / media 7g, liquidità in recupero | volume ×3 dopo dormienza + liquidità ≥ precedente | Casi di crescita su mesi (WIF, POPCAT) | Rendimento 24h/72h dopo il segnale |
| H11 | Deployer seriali/copycat → negativo | Numero di token creati dal deployer, ticker duplicati | >3 token in 7 giorni → rischio alto | Coin factory, copycat [S10] | Tasso di rug per storico deployer |
| H12 | Vendite coordinate → uscita | Più top holder che vendono nella stessa finestra | ≥3 top holder in vendita in 10 min → exit | Coordinated selling [S10] | Drawdown successivo all'evento |
| H13 | Il momentum è più debole sulle small cap | Rendimento del breakout per fascia di MC | atteso: continuazione migliore sopra 5–10 M$ di MC | [S19] | Breakout per bucket di MC |
| H14 | Pump guidati da bot: pump lungo, dump breve | Durata delle fasi | uscita rapida al primo cedimento di volume | [S33] | Confronto tra regole di uscita |

---

## 6. Rilevazione di rug pull, honeypot e contratti pericolosi (Solana)

| Controllo | Come si verifica | Esito |
|---|---|---|
| **Mint authority** attiva | `getAccountInfo` (jsonParsed) del mint o report RugCheck | Esclusione (il creatore può stampare token) |
| **Freeze authority** attiva | idem | Esclusione (il creatore può congelare il tuo account → honeypot) |
| **Token-2022 con estensioni pericolose** | transfer fee, transfer hook, permanent delegate, default account state frozen, non-transferable | Esclusione / rischio alto |
| **Impossibilità di vendere** | Simulazione di **quote di vendita** su Jupiter per l'importo che si comprerebbe; impatto e rotta | Esclusione se manca la rotta o l'impatto è eccessivo |
| **LP non bloccata/bruciata** (pool non da launchpad) | RugCheck `lpLockedPct` / markets | Rischio alto se < 90% |
| **Pool unilaterali / struttura anomala** | Riserve del pool (lato SOL/USDC trascurabile) | Rischio alto (caso LIBRA) |
| **Concentrazione per cluster** | Top holder, esclusi pool/bonding curve; collegamenti di finanziamento | Rischio alto / esclusione |
| **Deployer** | Quota del creatore, numero di token creati, vendite del creatore | Rischio alto / esclusione |
| **Rischi RugCheck** | `risks[]` con livello `danger` | Esclusione |
| **Prezzo anomalo** | Divergenza tra fonti (DexScreener vs Jupiter) > soglia | Dato non affidabile → nessun segnale |

---

## 7. Ingresso, gestione della posizione, uscita

### 7.1 Che cosa dice la ricerca (e che cosa non dice)

- Non ho trovato studi indipendenti e peer-reviewed che misurino in modo rigoroso il rendimento di specifiche
  regole di uscita (trailing, TP parziali, break-even) sulle memecoin Solana. Le guide di vendor (GMGN,
  copy-trading, Nansen) sono promozionali [S36]. → **Tutte le regole di uscita sono ipotesi da testare.**
- Dati certi: (a) i crolli avvengono in minuti (HAWK −90% in ~20 min); (b) i costi di round-trip sono
  alti (§2.2); (c) i pump guidati da bot hanno pump lunghi e dump brevi [S33].

### 7.2 Principi adottati (da validare con il backtest)

1. **Niente stop "teorici":** nel backtest uno stop toccato con gap viene eseguito all'apertura successiva
   e con impatto di prezzo sulle riserve stimate in quel momento.
2. **Il break-even non è automatico.** Si sposta lo stop a BE (+ costi) solo dopo un movimento favorevole
   > *k* × ATR **e** maggiore del costo di round-trip; altrimenti il normale rumore chiude in pari trade che
   sarebbero stati vincenti. Il backtest confronta: mai BE, BE a +1R, BE a +2R, BE dopo il primo TP.
3. **Take profit a scala** (es. 1° parziale, 2° parziale, residuo in trailing) confrontato con: uscita
   unica, solo trailing, uscita su perdita di momentum.
4. **Uscite "di regime":** calo del volume rispetto all'ingresso, calo della liquidità, vendite coordinate dei
   top holder, nuovi rischi RugCheck → uscita indipendente dal prezzo.
5. **Stop temporale:** un trade che non si muove entro N minuti libera capitale.

### 7.3 Dimensionamento

- Rischio per trade sul capitale **aggiornato** (compounding con riduzione automatica dopo le perdite —
  anti-martingala).
- La dimensione è il minimo tra: (a) rischio / distanza effettiva dallo stop (che include costi e un
  cuscinetto per il gap), (b) cap per posizione, (c) dimensione che mantiene l'impatto di prezzo sotto
  soglia, (d) quota massima della riserva del pool.
- Con 2 SOL, rischio 1–2% = 0,02–0,04 SOL a trade. Con stop effettivi del 20–30% la posizione tipica sarà
  **0,07–0,20 SOL**. A queste dimensioni le fee fisse di rete sono trascurabili, l'affitto ATA (~0,002 SOL)
  no: viene modellato.

---

## 8. Analisi social e community: che cosa è realisticamente possibile gratis

| Fonte | Stato 2026 | Uso nel sistema |
|---|---|---|
| **X (Twitter) API** | Pay-per-use dal 6 feb 2026; ~0,005 $ per post letto; free tier non più disponibile per i nuovi iscritti [S22] | **Non usata** (costo). Interfaccia predisposta, disattivata |
| **Reddit API** | 100 QPM per client OAuth, uso non commerciale; possibili cambiamenti di policy [S23] | Opzionale (richiede app Reddit gratuita dell'utente) |
| **Telegram** | Pagine pubbliche `t.me/s/<canale>` leggibili; nessuna API ufficiale per statistiche altrui | Opzionale: numero iscritti dei canali pubblici linkati (fragile) |
| **Link nei profili DexScreener** | Gratis (sito, X, Telegram dichiarati dal team) | Presenza/assenza di social, coerenza dei link |
| **Boost DexScreener** | Gratis da leggere | Indicatore di **marketing a pagamento** (H8), non di interesse organico |

**Autenticità:** con dati gratuiti limitati, l'autenticità della community si stima principalmente
**on-chain** (compratori unici, distribuzione, rapporto tx/trader, wallet freschi) più che dai social.
Il sistema distingue: *interesse organico* (molti compratori unici, distribuzione in miglioramento),
*marketing aggressivo* (boost/profili a pagamento senza ampliamento della base), *community artificiale*
(volume con pochi trader, wash trading), *coordinamento di pump* (cluster di acquisti simultanei),
*attività sospetta* (vendite coordinate, wallet del deployer attivi).

---

## 9. Fonti dati e API (valutazione)

> **Stato di verifica:** le API seguenti NON hanno potuto essere interrogate da questo ambiente di sviluppo
> (rete bloccata). Gli endpoint sono implementati secondo la documentazione pubblica e il codice è difensivo
> (campi mancanti → "non disponibile"). La verifica live avviene al primo avvio sul server con il comando
> `mci check-sources`.

| Fonte | Gratis | Chiave | Limiti (dichiarati) | Dati utili | Affid. | Ruolo |
|---|---|---|---|---|---|---|
| **DexScreener API** | Sì | No | 60 rpm (profili/boost), 300 rpm (pair) [S37] | prezzo, MC, FDV, liquidità, volume e tx 5m/1h/6h/24h, data creazione, link social, boost | C (doc non letta direttamente) | Scanner principale + prezzi posizioni |
| **GeckoTerminal API** | Sì | No | 30 chiamate/min; OHLCV: 6 mesi di storico sul piano gratuito [S21] | new/trending pools, compratori/venditori unici per finestra (5m/15m/30m/1h…), **OHLCV storico**, ultime trade del pool, info token | A (doc ufficiale) | Feature 15m, compratori unici, OHLCV per backtest |
| **Jupiter (Swap/Price API)** | Sì (keyless 0,5 RPS; chiave gratuita 1 RPS) | Opzionale | lite-api in dismissione progressiva, data TBA; stesso path su api.jup.ag [S38] | **Quote eseguibili reali** (impatto di prezzo per l'importo esatto), prezzo, transazioni di swap | A | Paper trading realistico, test di vendibilità, esecuzione reale |
| **RugCheck API** | Sì (lettura) | No | limiti non pubblicati (rispettare 429) [S39] | rischi, mint/freeze authority, top holder, LP bloccata, insider | C | Sicurezza contratto |
| **PumpPortal Data API (WebSocket)** | Sì | No | rate limit non dettagliati; API **non ufficiale** [S40] | nuovi token, trade per token, migrazioni in tempo reale | C | Scoperta in tempo reale dei lanci |
| **Solana RPC pubblico** | Sì | No | molto limitato | account del mint, largest accounts, supply, conferme | A | Verifiche on-chain di base |
| **Helius (free)** | Sì | Sì (account gratuito) | 1 M crediti/mese, 10 RPS, 2 RPS DAS/Enhanced [S41] | RPC affidabile, websocket, storico transazioni | A | RPC consigliato (richiede account) |
| **Birdeye (Standard)** | Sì | Sì | 30.000 CU, 1 RPS, "accesso dati limitato" [S42] | OHLCV, sicurezza token | A | Opzionale/futuro |
| **CoinGecko simple price** | Sì | No | basso rate limit | prezzo SOL in EUR/USD | D | Controvalore EUR dinamico |
| **Kraken public ticker** | Sì | No | — | SOL/EUR | D | Fallback EUR |
| **Telegram Bot API** | Sì | Token BotFather | — | notifiche e comandi | A | Bot |
| **Dune / Bitquery / Flipside** | Piani free con account | Sì | crediti limitati | **universo storico completo dei lanci** (anche token morti) | B | Opzionale per backtest storico senza survivorship bias |
| **SolRPDS (HuggingFace/GitHub)** | Sì | No | dataset statico 2021–2024 [S29] | etichette rug pull | A | Calibrazione del rilevatore di rug (regime vecchio) |

---

## 10. Limiti dei dati storici (dichiarati in modo esplicito)

1. **Survivorship bias negli elenchi:** gli endpoint "top/trending pools" restituiscono i sopravvissuti. Un
   universo storico corretto richiede l'elenco di **tutti** i token lanciati in un periodo. Gratis senza
   account: **non disponibile**. Con account gratuito Dune/Bitquery: possibile (query sui create di Pump.fun).
2. **Feature point-in-time non storicizzate:** holder, distribuzione, rischi RugCheck, social, liquidità del
   pool **nel momento del segnale** non sono recuperabili a posteriori gratis. → Il backtest "OHLCV-only"
   può testare solo le componenti prezzo/volume; le componenti on-chain/social restano "non disponibili"
   (con punteggio 0, mai neutro-positivo).
3. **La liquidità storica non è nell'OHLCV.** Il sistema la stima con la legge del prodotto costante
   (riserva SOL ∝ √prezzo in assenza di aggiunte/rimozioni di LP) a partire dall'ultima liquidità osservata;
   le rimozioni di LP (rug) non sono osservabili dall'OHLCV → modellate come evento di gap con recupero
   parziale/nullo.
4. **Finestra storica gratuita:** 6 mesi per richiesta su GeckoTerminal; accesso oltre i 6 mesi solo a
   pagamento [S21].
5. **Regime change:** le regole dei launchpad cambiano (fee dinamiche set-2025, BOOST lug-2026, guerra dei
   launchpad). Dati 2024 possono non rappresentare il 2026 → walk-forward con finestre recenti.
6. **Precisione temporale:** candele a 1 minuto; i bot reali operano a livello di blocco (~400 ms). Il
   backtest **non può** simulare la competizione con gli sniper: la strategia Early Entry nei primi secondi
   è esclusa per costruzione (entriamo solo dopo conferme su più minuti).

**Conclusione operativa:** fino a quando il dataset point-in-time registrato dal sistema non avrà almeno
alcune settimane di dati e un numero sufficiente di trade (soglia: ≥100 trade OOS per strategia), **nessun
risultato di backtest sarà dichiarato robusto** e il trading reale resterà bloccato.

---

## 11. Decisioni di progetto derivate dalla ricerca

1. **Filtro prima dello score:** esclusioni rigide (mint/freeze authority, invendibilità, liquidità minima,
   concentrazione, rischi `danger`, dati insufficienti, impatto di prezzo eccessivo).
2. **Pesi iniziali rivisti** rispetto alla proposta (vedi `docs/SCORING.md`): sicurezza e on-chain pesano di
   più, social di meno finché la copertura dei dati social resta bassa.
3. **Dati mancanti = punteggio 0** sulla feature e penalità di copertura; sotto una copertura minima delle
   categorie critiche → esclusione "dati insufficienti".
4. **Volume "scontato"** dalla stima di wash trading prima di usarlo nello score.
5. **Nessun ingresso nei primi minuti di vita** (non possiamo competere con gli sniper) e niente ingressi dopo
   estensioni estreme (H5).
6. **Costi realistici ovunque** (fee DEX per venue, rete, ATA, impatto AMM, latenza, transazioni fallite).
7. **Registrazione point-in-time di ogni token visto** (anche se scartato) per costruire il dataset di backtest
   senza survivorship bias; tracciamento dell'esito successivo di ogni segnale (Fase 14).
8. **Paper trading con quote Jupiter reali** per lo stake effettivo; ripiego sul modello AMM solo se la quote
   non è disponibile, con etichetta della fonte del prezzo.
9. **Trading reale disattivato** e protetto da più cancelli (flag + frase di conferma + kill switch + limiti +
   backtest/paper validati).

---

## 12. Registro delle fonti

| ID | Fonte | URL | Data | Affid. | Limitazioni | Utilità per il modello |
|---|---|---|---|---|---|---|
| S1 | Solidus Labs, "2025 Rug Pull Report" (via stampa) | https://beincrypto.com/pump-fun-tokens-scams-solidus-labs-report/ ; https://thedefiant.io/news/defi/alarming-99-of-memecoin-launches-on-pumpfun-are-pump-and-dumps-or-rug-pulls-report | mag-2025 | B | Report letto tramite stampa; definizione ampia di frode | Tasso base; filtri di liquidità |
| S2 | The Block, "Pump.fun token graduation rate jumps after BOOST" | https://theblock.co/post/409815/pump-fun-token-graduation-rate-jumps-boost-changes-launch-incentives | 29 lug 2026 | B | Finestra di pochi giorni | Regime attuale; dinamica post-migrazione |
| S3 | 99Bitcoins / Crypto-Economy su graduation rate | https://99bitcoins.com/news/presales/pump-crypto-graduation-rate-price-analysis/ | 2025–2026 | C | Periodo di misura non chiaro | Ordine di grandezza della graduation |
| S4 | Decrypt, analisi Dune: 0,4% dei wallet > 10k $ | https://decrypt.co/300403/pump-fun-traders-millionaires | gen-2025 | B | Solo profitti realizzati; bot inclusi | Aspettative realistiche |
| S5 | CoinGecko Research, profittabilità trader Pump.fun | https://www.coingecko.com/research/publications/pump-fun-traders-are-making-a-comeback | 2025 | B | Esclude i bagholder | Aspettative realistiche |
| S6 | Cointelegraph: "memecoins attract users, platforms reap profits" | https://cointelegraph.com/news/memecoins-attract-users-platforms-reap-profits-report | 2025 | B | Sintesi giornalistica | Contesto |
| S7 | Studio accademico su wash trading memecoin (≥17% tx) — citato in sintesi | https://www.emergentmind.com/papers/2609.10246 | 2026 | A/C | Letto solo tramite sintesi | Sconto del volume (H3) |
| S8 | Pine Analytics, "Exit Liquidity Machines" | https://pineanalytics.substack.com/p/exit-liquidity-machines | 2025–2026 | C | Analisi indipendente non peer-reviewed | Rilevazione sniper finanziati dal deployer (H2) |
| S9 | "Coordinated Sniper Cohorts on Pump.fun", arXiv:2607.02795 | https://arxiv.org/abs/2607.02795 | lug-2026 | A | Preprint; ~166.000 lanci di giugno 2026; avverte sui limiti dell'inferenza causale | H2 |
| S10 | "Meme Coin Factories: Uncovering Large-Scale Manipulations on pump.fun", arXiv:2609.10246 | https://www.emergentmind.com/papers/2609.10246 | set-2026 | A/C | Letto solo tramite abstract/sintesi | Tassonomia della manipolazione (H9, H11, H12) |
| S11 | Pagine tokenomics PEPE (MEXC, CoinDesk) | https://www.mexc.com/price/PEPE/tokenomics ; https://hotfix.coindesk.com/price/pepe | 2023–2026 | C | Dettagli incoerenti tra pagine | Caso studio |
| S12 | Decrypt/Benzinga su BONK; TradingView | https://www.benzinga.com/markets/cryptocurrency/23/12/36255279/bonk-mania-how-a-300-christmas-gift-to-solana-developers-snowballed-into-500k | dic-2023 | B/C | Allocazioni riportate in modo diverso | Caso studio distribuzione |
| S13 | Know Your Meme; The Block (listing Binance WIF) | https://knowyourmeme.com/memes/dogwifhat-meme-coin ; https://www.theblock.co/post/280799/dogwifhat-all-time-high-binance-listing | mar-2024 | B/C | Market cap di lancio solo aneddotica | Caso studio tempi di crescita |
| S14 | Bubblemaps, "The $LIBRA Playbook"; Decrypt | https://blog.bubblemaps.io/the-libra-playbook-how-one-cluster-drained-87-million-in-a-single-hour/ ; https://decrypt.co/306987/what-is-libra-the-solana-meme-coin-that-sparked-a-political-scandal | feb-2025 | B | Accuse non giudicate; cifre divergenti (87 vs 107 M$) | H1, pool unilaterali |
| S15 | Halborn, "Explained: the Hawk Tuah rug pull" | https://www.halborn.com/blog/post/explained-the-hawk-tuah-rug-pull-december-2024 | dic-2024 | B | Cifre di concentrazione diverse tra fonti | H1, H2 |
| S16 | Bubblemaps, "How Hailey Welch's $HAWK token became a $500M disaster" | https://blog.bubblemaps.io/how-hailey-welchs-hawk-token-became-a-500m-disaster/ | dic-2024 | B | Accuse contestate dal team | H1, H2 |
| S17 | Cointelegraph/Decrypt su MELANIA (Bubblemaps) | https://cointelegraph.com/news/melania-trump-memecoin-team-sold-30-million-bubblemaps | apr-2025 | B | — | H1, H12 |
| S18 | Chainalysis via Cointelegraph: whale 94% TRUMP/MELANIA | https://cointelegraph.com/news/crypto-whales-dominate-holdings-trump-tokens-chainalysis | gen-2025 | B | — | H1 |
| S19 | Liu, Tsyvinski, Wu, "Common Risk Factors in Cryptocurrency", Journal of Finance 2022 | https://www.nber.org/papers/w25882.pdf | 2022 | A | Campione 2014–2018, non memecoin; rischio di data snooping | Momentum più debole sulle small cap (H13) |
| S20 | Liu, Tsyvinski, "Risks and Returns of Cryptocurrency" (NBER 2018) | https://www.nber.org/system/files/working_papers/w24877/w24877.pdf | 2018/2021 | A | Non memecoin | Attenzione e momentum (H4) |
| S21 | Docs CoinGecko/GeckoTerminal: rate limit 30/min, storico OHLCV | https://apiguide.geckoterminal.com/faq ; https://docs.coingecko.com/changelog/extended-historical-data-for-onchain-ohlcv-endpoint | 2025–2026 | A | Limite per richiesta non verificato | Dati per backtest |
| S22 | Guide prezzi X API 2026 (pay-per-use) | https://opentermsarchive.org/en/memos/x-replaces-its-dollar200-entry-level-api-plan-with-a-pay-per-use-model/ ; https://www.postproxy.dev/blog/x-api-pricing-2026/ | feb–ago 2026 | C | Prezzi cambiati più volte | Esclusione X dal free tier |
| S23 | Guide Reddit API 2026 | https://www.socialcrawl.dev/blog/reddit-api-key-limits-alternatives-2026 | 2026 | C | Policy in evoluzione; data 31/10/2026 non verificata | Social opzionale |
| S24 | The Block, lancio PumpSwap | https://www.theblock.co/post/347360/pump-fun-launches-dex-called-pumpswap-to-instantly-migrate-graduated-tokens | mar-2025 | B | — | Venue di esecuzione |
| S25 | The Block su LetsBonk vs Pump.fun | https://www.theblock.co/post/363647/letsbonks-market-share-of-solana-meme-token-launchpad-grows-to-64 ; https://www.theblock.co/post/367266/solana-memecoin-launchpad-war-flips-again-as-pump-takes-top-spot-amid-letsbonk-collapse | 2025 | B | Snapshot datati | Architettura multi-launchpad |
| S26 | RPC Fast / Chainstack / MadeOnSol su fee Solana | https://rpcfast.com/blog/solana-transaction-fees-explained | 2026 | C | Nessuna mediana verificata | Modello dei costi |
| S27 | Coinpaprika (fee launchpad), Datawallet, Blockworks (fee dinamiche) | https://coinpaprika.com/education/launchpad-fees/ ; https://blockworks.co/news/pumpdotfun-fee-model | 2025–2026 | C | **Fonti in conflitto** | Modello dei costi (valori conservativi) |
| S28 | Chainalysis 2025 Crypto Crime Report (via stampa) | https://cryptonews.com/news/chainalysis-market-manipulation-billions-trades/ | feb-2025 | B | Conflitto sull'attribuzione 3,59% | Tassi base |
| S29 | Alhaidari et al., "SolRPDS", ACM CODASPY 2025, arXiv:2504.07132 | https://www.arxiv.org/pdf/2504.07132 ; https://huggingface.co/datasets/DeFiLab/SolRPDS | giu-2025 | A | Copre 2021–2024 (regime pre-PumpSwap) | Etichette di rug per calibrazione |
| S30 | The Coin Republic su PNUT/Binance | https://www.thecoinrepublic.com/2024/11/14/pnut-flips-popcat-after-binance-listing-is-10b-possible/ | nov-2024 | C | — | Catalizzatori CEX |
| S31 | Fortune, The Defiant, The Block, Yahoo su FARTCOIN | https://www.fortune.com/crypto/2024/12/19/fartcoin-1-billion-market-cap-memecoin-market-explodes ; https://www.theblock.co/price/fartcoin | dic-2024 / mar-2025 | B | Holder variabili per snapshot | Caso studio Pump.fun → large cap |
| S32 | Bitquery, "Solana volume numbers are a lie" e detector wash trading | https://bitquery.io/blog/solana-volume-numbers-are-a-lie ; https://docs.bitquery.io/docs/usecases/wash-trading-detector/overview/ | 2025–2026 | C | Vendor | Euristiche wash trading (H3) |
| S33 | "Decompose Market Manipulation Strategies: Evidence from On-chain Meme Coin Market" (SBFC 2025 / SSRN 5953738) | https://papers.ssrn.com/abstract=5953738 | 2025 | A | Letto tramite sintesi; 6.000 progetti | Pump lunghi/dump brevi (H5, H14) |
| S34 | Guide su graduation/migrazione | https://madeonsol.com/learn/graduated-pump-fun | 2026 | C | Qualitativo | H7 |
| S35 | Documentazione DexScreener (boost) | https://docs.dexscreener.com/llms-full.txt | 2026 | A | — | H8 |
| S36 | Guide copy trading (Nansen, MadeOnSol) | https://nansen.ai/post/how-to-use-nansen-to-find-profitable-solana-wallet-addresses | 2026 | C | Promozionali | Scetticismo sul copy trading |
| S37 | Documentazione di terze parti dell'API DexScreener | https://github.com/opensvm/dexscreener-mcp-server | 2025–2026 | C | Non è la doc ufficiale | Rate limit scanner |
| S38 | Jupiter Developer Platform: rate limit, migrazione lite-api | https://developers.jup.ag/docs/portal/rate-limit.md ; https://developers.jup.ag/docs/portal/migration | 2026 | A | Data di dismissione lite-api TBA | Esecuzione e paper trading |
| S39 | Guide/wrapper RugCheck API | https://pypi.org/project/rugcheck/ | 2025–2026 | C | Nessuna doc ufficiale trovata | Sicurezza |
| S40 | PumpPortal docs (mirror) | https://github.com/TrustPump/Pump-Fun-API | 2025–2026 | C | API non ufficiale | Scoperta lanci |
| S41 | Helius pricing/billing docs | https://helius.dev/pricing | apr-2026 | A | Conflitti minori nella doc | RPC |
| S42 | Birdeye pricing/rate limiting | https://docs.birdeye.so/docs/pricing | 2026 | A | Costo in CU per endpoint non letto | Fonte opzionale |
| S43 | Oracle Always Free (doc + InfoQ lug-2026) | https://docs.oracle.com/en-us/iaas/Content/FreeTier/resourceref.htm ; https://infoq.com/news/2026/07/oracle-cloud-free-tier-limits/ | lug-2026 | A/B | Data effettiva del taglio in conflitto (15 giu vs 18 ago 2026) | Infrastruttura |
| S44 | Render free tier docs | https://render.com/docs/free | 2026 | A | — | Infrastruttura |
| S45 | Confronti Supabase/Neon free plan | https://neon.com/guides/neon-vs-supabase-free-plan | 2026 | B/C | Verificare sulle pagine prezzi | Database |
| S46 | Mongardini et al., "A Midsummer Meme's Dream", arXiv:2507.01963 (USENIX Security 2026) | https://arxiv.org/html/2507.01963v2 | 2025–2026 | A | 34.988 token cross-chain; letto via sintesi | Tassonomia P&D/rug |

**Fonti marcate D (conoscenza pregressa, non riverificata in sessione):** storia di DOGE, SHIB, FLOKI, BRETT,
POPCAT (parziale), SQUID, fee Raydium AMM v4, affitto ATA, endpoint CoinGecko/Kraken. Sono usate solo come
contesto qualitativo o come default configurabili, mai come prova.
