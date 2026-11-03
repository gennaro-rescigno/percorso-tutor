# bryceweiner/fly-trader-seed

licenza: mit · gated: False · file: 4 · dimensione totale: 2.29 GB

## File
- .gitattributes (0.0 MB)
- README.md (0.0 MB)
- dump.sh (0.0 MB)
- fly_trader_core.dump (2293.5 MB)

## Scheda

---
license: mit
pretty_name: fly-trader training database
tags:
  - solana
  - memecoin
  - pump.fun
  - trading
  - time-series
---

# fly-trader training database

The PostgreSQL database [fly-trader](https://github.com/bryceweiner/fly-trader) trains on: every PumpSwap trade of
tokens that graduated from pump.fun, aggregated to 1-minute candles with order-flow, wallet and launch facts, from
2026-04-19 to 2026-09-21. This is what the shipped model was trained from; restore it to retrain on `master` without
re-downloading five months of archive.

**Not included:** runtime state (positions, decisions, the fly's learning tables), API logs, the ephemeral swap tapes,
and the per-day wallet-skill tables (30 GB of parquet; `master` rebuilds them from these tables with
`fly-trader fit-wallet-skill`).

## Contents

`fly_trader_core.dump` — a `pg_dump -Fc` (custom format, compressed) of these tables:

| Table | What |
|---|---|
| `pump_minutes` | 1-minute candles per token: OHLC, buy/sell SOL, trade counts, buyers, wash, top-holder and insider selling, buys by wallet-skill decile |
| `pump_events`, `pump_pools` | pool creations and graduations; PumpSwap pools with their reserves |
| `tokens`, `token_stats`, `token_insiders` | token metadata and decimals; Jupiter token stats history; creator, bundle and early wallets per token |
| `corpus_meta`, `corpus_tokens`, `corpus_features` | launch facts per token (bundle share, dev holdings, graduation top-10 share, curve state) and the training feature manifest |
| `mature_days`, `replay_days`, `replay_hours` | which archive days and hours are complete |
| `schema_version` | 6 |

## Restore

```bash
createdb fly_trader
pg_restore -d fly_trader --no-owner fly_trader_core.dump
git clone https://github.com/bryceweiner/fly-trader.git && cd fly-trader && uv sync
uv run fly-trader init-db          # adds the runtime tables the dump leaves out
```

Then `uv run fly-trader build-mature` / `train-selector` as described in the repository README. PostgreSQL 15 or newer.

## Provenance and licence

Trades from the [PumpAPI](https://pumpapi.io) archive and stream; token stats from [Jupiter](https://jup.ag). Public
on-chain data, aggregated. MIT, no warranty. A ready-to-run trader built from this data is at
[bryceweiner/fly-trader](https://huggingface.co/bryceweiner/fly-trader).

