# Infrastruttura gratuita: confronto e raccomandazione

Ricerca del 1 nov 2026 (fonti in RESEARCH_REPORT, S43–S45 e ricerche dedicate). I piani gratuiti cambiano
spesso: **verificare sulla pagina ufficiale prima di registrarsi.**

## Requisiti del sistema

* processo **sempre attivo** (WebSocket PumpPortal, monitor posizioni ogni 20 s, Telegram long polling);
* database persistente (stima: ~35 MB/giorno di snapshot prima della compattazione; dopo 14 giorni lo
  storico viene ridotto a 1 snapshot/ora per token);
* ~600 MB–1,5 GB di RAM per worker + API + PostgreSQL;
* HTTPS pubblico per la dashboard.

## Confronto

| Servizio | Costo | Processo 24/7 | Database | Limiti rilevanti | Carta richiesta | Adatto? |
|---|---|---|---|---|---|---|
| **Oracle Cloud Always Free** | 0 € entro i limiti | **sì** (VM vera) | PostgreSQL sulla VM (fino a 200 GB di disco) | Ampere A1 ridotto a **2 OCPU / 12 GB** nel 2026 (prima 4/24); anche 2 VM AMD micro da 1 GB; disponibilità A1 spesso "out of capacity"; le istanze **inattive** (CPU p95 < ~20% su 7 giorni) possono essere recuperate da Oracle | sì, per verifica identità (nessun addebito restando nei limiti Always Free) | **Sì – raccomandato** |
| Google Cloud e2-micro | 0 € (solo us-west1/us-central1/us-east1) | sì | sulla VM (30 GB) | 1 GB RAM, 1 GB di traffico in uscita/mese, IP esterno non sempre gratuito; account di fatturazione obbligatorio | sì | Possibile ma stretto (RAM e traffico) |
| Render free | 0 € | **no**: il web service si sospende dopo 15 min senza traffico; i background worker non sono gratuiti | Postgres free **scade dopo 30 giorni** | 750 h/mese, filesystem effimero | no | No |
| Railway | trial con credito (~5 $), poi a pagamento | sì finché c'è credito | sì | non è un piano gratuito permanente | no/sì | No |
| Fly.io | nessun piano gratuito per le nuove organizzazioni (trial) | — | — | | sì | No |
| Koyeb | 1 istanza piccola gratuita (dettagli su sospensione non verificati) | incerto | no | | — | Non verificato |
| Supabase free | 0 € | — (solo DB) | 500 MB, **pausa dopo 7 giorni di inattività**, nessun backup | | no | Solo come DB di riserva |
| Neon free | 0 € | — (solo DB) | 0,5 GB per progetto, compute che si sospende e riparte | spazio ridotto per lo storico | no | DB alternativo (con retention aggressiva) |
| GitHub Actions | gratis (repo pubblici) / 2.000 min/mese (privati) | **no**: cron minimo 5 min, ritardi frequenti, job max 6 h | — | non adatto a monitor ogni 20 s | no | Solo CI (già configurata) |
| Vercel Hobby | 0 € | no (funzioni serverless) | — | uso non commerciale | no | Non necessario: la dashboard è servita dalla VM |

## Raccomandazione

**Una sola VM Oracle Cloud Always Free** con `docker compose`: PostgreSQL + worker + API/dashboard + Caddy
(HTTPS automatico) + backup giornaliero. Costo: **0 €** restando nelle risorse Always Free.

Dimensionamento: una VM Ampere A1 con 1 OCPU / 4 GB è più che sufficiente (resta metà della quota per
altro). In alternativa, se l'A1 non è disponibile nella regione, una VM AMD E2.1.Micro (1 GB) funziona
con lo swap da 2 GB creato da `deploy/oracle-setup.sh`.

Dominio gratuito: un sottodominio **DuckDNS** (`<nome>.duckdns.org`, login con GitHub/Google), puntato
all'IP della VM; Caddy ottiene da solo il certificato HTTPS Let's Encrypt.

## Compromessi da conoscere (onestamente)

1. **Carta di credito per la verifica** su Oracle: richiesta anche per il piano gratuito.
2. **Recupero delle istanze inattive:** il bot usa poca CPU, quindi Oracle potrebbe classificare la VM
   come inattiva. Mitigazioni: (a) passare l'account a *Pay As You Go* (le risorse Always Free restano
   gratuite, ma **da quel momento eventuali risorse extra create per errore verrebbero addebitate**: è una
   scelta tua, non la attivo io); (b) monitorare l'email di Oracle e ricreare la VM (i dati sono nei backup).
3. **Capacità A1:** può servire riprovare in un altro momento o in un'altra availability domain.
4. **Un solo server = singolo punto di guasto:** `restart: unless-stopped` riavvia i container dopo crash e
   reboot; i backup giornalieri restano sulla VM (consigliato copiarli periodicamente altrove).
5. **API dati gratuite con limiti:** lo scanner arricchisce ~30 candidati a rotazione; con una chiave
   gratuita Helius/Jupiter i limiti migliorano senza costi.

## Costi effettivi

| Voce | Costo |
|---|---|
| VM + disco + traffico (Always Free) | 0 € |
| Dominio DuckDNS + certificato Let's Encrypt | 0 € |
| API dati (DexScreener, GeckoTerminal, Jupiter keyless, RugCheck, PumpPortal, RPC pubblico) | 0 € |
| Telegram Bot | 0 € |
| Chiavi gratuite opzionali (Helius, Jupiter, Reddit) | 0 € (richiedono registrazione) |
| **Totale** | **0 €/mese** |
| Solo con trading reale: fee di rete Solana per transazione | ~0,0001 SOL + fee DEX già incluse nei calcoli |

Alternativa a pagamento (non attivata): una VPS da ~4–5 €/mese elimina il rischio di recupero delle
istanze e i limiti di capacità.
