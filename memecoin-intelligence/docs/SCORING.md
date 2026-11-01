# Scoring e filtri di esclusione

Implementazione: `backend/mci/scoring/filters.py`, `backend/mci/scoring/scorer.py`.

## 1. Filtri di esclusione immediata (prima dello score)

Un token escluso **non viene mai acquistato**, qualunque sia lo score.

| Codice | Condizione (default) | Motivazione |
|---|---|---|
| `RUGGED` | segnalato come già ruggato | — |
| `MINT_AUTHORITY_ACTIVE` | mint authority non revocata | il creatore può stampare token |
| `FREEZE_AUTHORITY_ACTIVE` | freeze authority non revocata | honeypot: il tuo account può essere congelato |
| `DANGEROUS_EXTENSION` | Token-2022: transfer fee/hook, permanent delegate, default frozen, non-transferable, pausable | vendita bloccabile o tassabile |
| `RUGCHECK_DANGER` / `RUGCHECK_SCORE` | rischi di livello `danger` / punteggio normalizzato > 70 | |
| `HONEYPOT_NO_SELL_ROUTE` | nessuna rotta di vendita su Jupiter | caso SQUID |
| `SELL_IMPACT` | impatto di vendita > 5% per 0,1 SOL | uscita impossibile senza perdite |
| `LOW_LIQUIDITY` | liquidità < 15.000 $ | |
| `LP_UNLOCKED` | pool non da launchpad con LP bloccata/bruciata < 80% | rug classico |
| `TOP10_CONCENTRATION` / `TOP1_CONCENTRATION` | top 10 > 50% / singolo > 20% (pool esclusi) | LIBRA, HAWK, MELANIA |
| `DEV_HOLDING` | deployer > 10% | |
| `INSIDER_CLUSTER` / `EARLY_CLUSTER` | insider o sniper/bundle iniziali > 30% | |
| `WASH_TRADING` | wash score ≥ 0,75 | manipolazione evidente |
| `PRICE_ANOMALY` | prezzo DexScreener vs Jupiter divergente > 15% | dato inaffidabile |
| `TOO_YOUNG` | < 5 minuti di vita | non competiamo con gli sniper |
| `INSUFFICIENT_DATA` | (solo per operare) manca uno tra: authority, rotta di vendita, liquidità, holder, prezzo, età, lock LP; oppure copertura < 50% nelle categorie liquidità o sicurezza | **un dato mancante non è mai un segnale positivo** |

## 2. Punteggio 0–100

Pesi rivisti rispetto alla proposta iniziale, sulla base della ricerca:

| Categoria | Proposta | Adottato | Perché |
|---|---|---|---|
| Momentum e price action | 20 | **15** | il momentum è più debole sulle small cap (Liu-Tsyvinski-Wu); molti pump sono costruiti |
| Volume e attività | 15 | **15** | volume scontato per il wash score |
| Liquidità e possibilità di uscita | 15 | **20** | senza uscita non c'è profitto; i rug si concentrano sulla liquidità |
| On-chain e wallet | 20 | **20** | la concentrazione per cluster è il segnale di rischio più robusto |
| Community e sentiment | 15 | **10** | dati social gratuiti scarsi nel 2026 (X a pagamento): peso ridotto finché la copertura è bassa |
| Età e progetto | 5 | **5** | |
| Sicurezza contratto | 10 | **15** | condizione necessaria (tutti i grandi successi avevano supply non controllata dal team) |

Ogni categoria è composta da feature con punteggio a fasce (vedi codice). Regole:

* feature con input mancante → **0 punti** e nota "dato non disponibile";
* `coverage` = quota dei 100 punti i cui dati erano disponibili (mostrata in dashboard e Telegram);
* estensioni estreme (> +300% in 1h) danno 0 punti momentum e un rischio esplicito ("non si insegue il pump");
* un rapporto buy/sell > 0,85 è trattato come sospetto, non come forza;
* boost/profili DexScreener (a pagamento) valgono poco e solo se manca una base di compratori ampia.

Etichette: ≥ 80 **ALTO POTENZIALE**, ≥ 70 **INTERESSANTE**, ≥ 55 **OSSERVARE**, altrimenti **DEBOLE**;
**SCARTATO** se un filtro esclude il token.

## 3. Spiegazione

`ScoreResult.explanations` riporta per ogni categoria i punti, le due feature che hanno contribuito di più e
l'elenco delle feature non disponibili; `risks` elenca i rischi individuati. Entrambi compaiono nella scheda
token della dashboard, nei segnali registrati e nelle notifiche Telegram.

## 4. Calibrazione

I pesi e le soglie sono **priori**. La calibrazione avviene sul dataset point-in-time registrato:
`signals` conserva score, feature e prezzi a 15m/1h/4h/24h; la sezione Performance → "Qualità dei segnali"
mostra il rendimento medio dopo i segnali per strategia. Le modifiche vanno validate su un periodo
indipendente (walk-forward) prima di essere adottate: il sistema **non** si auto-modifica.
