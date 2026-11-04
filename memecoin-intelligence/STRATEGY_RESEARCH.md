# STRATEGY_RESEARCH.md — Metodo del laboratorio di ricerca sulle strategie memecoin

Questo documento descrive **come** cerchiamo un vantaggio statistico, prima di qualsiasi risultato. I risultati
sono in `PROFITABILITY_RESEARCH_REPORT.md`, la classifica in `STRATEGY_COMPARISON.md` / `STRATEGY_RANKING.csv`,
lo stato del progetto in `PROJECT_AUDIT.md`, la cronologia completa degli studi in `docs/RICERCA_MERCATO_MEMECOIN.md`.

## 1. Principi

1. **Si parte dai dati, non dalla strategia.** Ogni ipotesi è scritta nel codice (docstring "PRE-REGISTERED") prima
   di eseguire lo studio, con dati, regole, costi e criterio di verdetto. Le regole non si cambiano dopo aver visto
   i risultati; un errore di calcolo si corregge dichiarandolo e rieseguendo le stesse regole.
2. **Tre insiemi di giorni separati**: scoperta (si cercano le ipotesi), validazione (si conferma con correzione per
   test multipli), test (letto una sola volta, solo per ciò che ha passato la validazione). Quando esiste, un
   secondo dataset di un altro periodo fa da verifica esterna.
3. **Nessuna informazione futura**: le caratteristiche usano solo operazioni fino al momento della decisione; il
   record dei wallet usa solo posizioni chiuse **nei giorni precedenti**; le soglie delle regole sono calcolate
   solo sui giorni di scoperta; i campi che il dataset segnala come "proxy dell'etichetta" sono esclusi.
4. **Niente bias di sopravvivenza**: sono inclusi i token morti dopo pochi secondi, quelli rimossi, i pool svuotati,
   i contratti delistati; un token che smette di essere scambiato vale il suo ultimo prezzo (sulla curva il prezzo
   non cambia senza scambi) o, quando non è osservabile, è riportata anche la lettura pessimistica.
5. **Esecuzione realistica**: commissioni reali della piattaforma, impatto del proprio ordine sulla riserva,
   commissioni di rete misurate sul server, **ritardo dei dati** (0 s teorico, 3 s, 30 s = mediana misurata dello
   stream gratuito), ordini non eseguibili (curva chiusa prima che l'ordine arrivi), stress con costi raddoppiati.
6. **Il modello complesso deve battere quello semplice**: il modello a gradient boosting entra come una delle
   ipotesi e viene giudicato con le stesse regole delle soglie semplici.
7. **Si dichiara quando non c'è niente**: un verdetto negativo è un risultato.

## 2. Dati usati (tutti gratuiti, tutti reali)

| Dataset | Periodo | Contenuto | Uso | Licenza |
|---|---|---|---|---|
| jocry/Pumpfun_Memecoin_Corpus | 5 giugno – 14 luglio 2026 | 798.430 token, 33,6 milioni di operazioni con wallet, 5.669 diplomi con istantanee PumpSwap | nuovi lanci, wallet, dopo il diploma | MIT |
| loopholetape/pumpfun-launches | 31 agosto – 27 ottobre 2026 | 1,36 milioni di lanci, percorsi minuto per minuto | nuovi lanci (altro periodo) | CC BY |
| bryceweiner/fly-trader-seed | 14 – 21 settembre 2026 | 1,03 milioni di candele da 1 minuto di 28.721 token PumpSwap | memecoin quotate | MIT |
| pumpdatafun/pump-fun-trades-sample | 15 ottobre 2026 | 42 milioni di righe: ogni operazione su curva e PumpSwap, **comprese quelle fallite**, con slot, wallet e commissioni | esecuzione reale, giorno di verifica | CC BY 4.0 |
| hussxamg04/trenches-pumpfun-forward-2026-08 | 6 – 13 agosto 2026 | 85.442 token con dati social da X e un timestamp di disponibilità per ogni campo | hype e social (solo ricerca) | PolyForm Noncommercial |
| AratiKamat/red-pump-2026 | 8 maggio – 10 giugno 2026 | 860.213 lanci con link social ed esito a 24 ore | metadati dei progetti | CC BY 4.0 |
| data.binance.vision | 2018 – ottobre 2026 | candele e funding di tutte le coppie spot e dei perpetui, delistati compresi | memecoin quotate su CEX, short, funding, trend | pubblico |
| Stream del bot (VPS) | dal 1° novembre 2026 | lanci, operazioni, eventi, segnali e paper trading dal vivo | verifica dal vivo | nostro |

Esaminati e scartati: `launchtape/solana-launch-tape` (solo 2 ore di campione), `cryptodata/pumpfun-dataset-light`
(accesso negato, HTTP 401: non è pubblico). Birdeye, Helius e altri fornitori a pagamento non sono usati.

## 3. Il motore di scoperta per i nuovi lanci (`research/historical/discovery_launch.py`)

- **Momenti di decisione**: 10 s, 30 s, 1, 3, 5, 15, 60 minuti dal lancio.
- **27 segnali** calcolati solo con le operazioni fino al momento: flusso (operazioni, acquisti, vendite, acquirenti e
  venditori unici, SOL comprati, rapporto venduto/comprato, SOL netti, acquisto medio, operazioni per wallet),
  prezzo (rendimento dal primo scambio, distanza dal massimo, inattività, accelerazione degli acquisti), curva (SOL
  reali), struttura degli acquirenti (sniper nei primi 2 s, wallet nello stesso secondo, quota del primo e dei primi
  5 acquirenti, wallet nuovi), qualità dei wallet **nel passato** (wallet con almeno 8 posizioni chiuse nei giorni
  precedenti, il 50% vincenti e almeno +1 SOL), creatore (acquisto iniziale, token e rug precedenti), mayhem.
- **Ipotesi generate automaticamente**: ogni segnale nel suo 20% più alto e più basso, le coppie dei migliori 8, un
  modello a gradient boosting (10% migliore delle sue previsioni), e "tutti i candidati" come riferimento.
- **Entrate**: immediata; dopo una conferma (+15% entro 2 minuti); dopo un ritracciamento (−25% dal massimo entro 5
  minuti); dopo un consolidamento (60 s con almeno 3 scambi e oscillazione ≤ 15%).
- **Uscite**: a tempo (5 e 30 minuti); stop −30% / obiettivo +100%; trailing stop 35%; metà a +100% e il resto con
  trailing; perdita di slancio (60 s senza acquisti o più vendite che acquisti in un minuto); tenuta fino al diploma;
  massimo 60 minuti; il diploma durante la tenuta segue il token su PumpSwap.
- **Selezione**: t ≥ 3 sui giorni di scoperta con almeno 100 operazioni; le 60 migliori (più le 20 migliori con 30 s
  di ritardo) vanno in validazione con Benjamini-Hochberg; le sopravvissute si leggono sui giorni di test. Verdetto
  "vantaggio" solo con intervallo di confidenza sopra zero, risultato positivo con i costi raddoppiati e con il
  ritardo di 30 s.
- **Controllo del motore**: su dati sintetici con un vantaggio vero lo trova; su dati sintetici senza vantaggio
  (martingala) non seleziona nessuna strategia neppure nella fase di scoperta (0 su 44.520).
- **Uscite descrittive**: quando ogni segnale diventa informativo (AUC per momento), quanto rialzo resta, pump
  organico o artificiale, confronto di entrate e uscite su tutti i candidati, sopravvivenza dei token, ordini non
  eseguibili.

## 4. Memecoin già quotate

Coperte da studi dedicati con le stesse regole di metodo: regole su PumpSwap (slancio, ritracciamento,
sopravvissuti, accumulo; `fly_rules`), modello portabile 1-4 ore (`dex_model`), fornire liquidità (`dex_lp`),
memecoin dei CEX con hype, rotture, pullback, forza e modello (`crypto_daily`, `crypto_daily2`), trend
giornaliero e a 4 ore su 60 memecoin (`meme_trend`). Il motore di scoperta per le memecoin quotate (stessa struttura,
sulle istantanee PumpSwap di jocry e sulle candele di fly) è il prossimo esperimento.

## 5. Short (modulo separato)

`crypto_short` sui perpetui Binance: disponibilità del contratto, liquidità (le 100 più scambiate), funding reale,
stop sul massimo del giorno con i gap, garanzia 1x (nessuna liquidazione oltre la garanzia). Non è integrato nel
trading: nessuna regola ha passato le verifiche.

## 6. Classifica

`research/ranking/ranking.py` assegna a ogni strategia un punteggio 0-100 con pesi fissati prima: significatività
25%, robustezza 20%, stabilità 15%, rendimento 15%, drawdown 15%, numero di osservazioni 10%; metà punteggio a ciò
che non è eseguibile con strumenti gratuiti; "scartata" ogni strategia con media fuori campione non positiva. Il
ROI più alto non vince da solo.

## 7. Dalla ricerca al bot

Una strategia entra nel sistema principale solo se: (1) ha il verdetto "robusta" nella classifica; (2) regge con il
ritardo reale dei dati; (3) supera un periodo di paper trading dal vivo con il cancello statistico già presente nel
bot (`mci/research/promotion.py`); (4) tu dai il consenso. Il trading reale resta disattivato.
