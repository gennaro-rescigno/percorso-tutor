# pumpdatafun/pump-fun-trades-sample

licenza: cc-by-4.0 · gated: False · file: 16 · dimensione totale: 4.15 GB

## File
- .gitattributes (0.0 MB)
- README.md (0.0 MB)
- data/pumpdata-2026-10-15-00000-of-00004.parquet (434.5 MB)
- data/pumpdata-2026-10-15-00001-of-00004.parquet (414.5 MB)
- data/pumpdata-2026-10-15-00002-of-00004.parquet (402.4 MB)
- data/pumpdata-2026-10-15-00003-of-00004.parquet (120.0 MB)
- events/pumpdata-2026-10-15-events.parquet (4.6 MB)
- receipt.json (0.0 MB)
- signatures/pumpdata-2026-10-15-signatures-00000-of-00007.parquet (449.6 MB)
- signatures/pumpdata-2026-10-15-signatures-00001-of-00007.parquet (450.2 MB)
- signatures/pumpdata-2026-10-15-signatures-00002-of-00007.parquet (450.3 MB)
- signatures/pumpdata-2026-10-15-signatures-00003-of-00007.parquet (449.9 MB)
- signatures/pumpdata-2026-10-15-signatures-00004-of-00007.parquet (449.9 MB)
- signatures/pumpdata-2026-10-15-signatures-00005-of-00007.parquet (449.6 MB)
- signatures/pumpdata-2026-10-15-signatures-00006-of-00007.parquet (74.2 MB)
- summary.json (0.0 MB)

## Scheda

---
license: cc-by-4.0
pretty_name: pump.fun and PumpSwap trades, one day (pumpdata.fun sample)
language:
- en
tags:
- solana
- pump.fun
- pumpswap
- memecoins
- defi
- crypto
- blockchain
- trades
- parquet
size_categories:
- 10M<n<100M
task_categories:
- tabular-classification
- time-series-forecasting
configs:
- config_name: default
  data_files:
  - split: train
    path: data/*.parquet
- config_name: events
  data_files:
  - split: train
    path: events/*.parquet
- config_name: signatures
  data_files:
  - split: train
    path: signatures/*.parquet
---
# pumpdata sample: one UTC day of pump.fun and PumpSwap trades, failed trades kept

One UTC day, **2026-10-15**, of every pump.fun bonding-curve trade and every PumpSwap trade the pumpdata.fun archive
ties to a coin, with the trades that failed on chain kept beside the ones that landed. Beside them are the day's events (creates, migrations, pools), every transaction's signature, and a receipt that checks the day's blocks against the chain. It's read from
the chain's own ledger, not an indexer's copy. Parquet, zstd, in shards of at most 500 MB. Not affiliated with
pump.fun.

## Coverage

| | |
|---|---|
| UTC day | `2026-10-15T00:00:00Z` to `2026-10-16T00:00:00Z` (end exclusive) |
| rows | 42,230,410 |
| landed trades | 21,801,882 (curve 4,556,524, PumpSwap 17,245,358) |
| failed trades | 20,428,528 (curve 10,396,021, PumpSwap 10,032,507) |
| PumpSwap landed trades in the coin's own migration pool / in other pools | 10,997,308 / 6,248,050 |
| distinct mints / wallets / pools | 81,402 / 849,927 / 19,691 |
| first / last block time | 2026-10-15T00:00:00Z / 2026-10-15T23:59:59Z |
| longest stretch with no landed trade | 2 s |
| raw venue codes (`venue:venue_code` rows) | `curve:c` 14,952,545, `pumpswap:a` 27,277,865 |
| archive epochs read | 1057, 1058 |
| shards / size | 4 / 1,371.4 MB |

| shard | rows | size |
|---|---|---|
| `data/pumpdata-2026-10-15-00000-of-00004.parquet` | 12,818,368 | 434.5 MB |
| `data/pumpdata-2026-10-15-00001-of-00004.parquet` | 12,818,368 | 414.5 MB |
| `data/pumpdata-2026-10-15-00002-of-00004.parquet` | 12,818,368 | 402.4 MB |
| `data/pumpdata-2026-10-15-00003-of-00004.parquet` | 3,775,306 | 120.0 MB |

Beside the trades, the same day's other tables and its receipt:

| path | what | rows | size |
|---|---|---|---|
| `events/` | creates, completions, migrations, pools and the rest: `slot`, `idx`, `kind`, `ts`, and `a` to `f` by kind | 75,466 | 4.6 MB |
| `signatures/` (7 files) | one row per transaction: `slot`, `idx`, `signature` | 40,955,595 | 2,773.7 MB |
| `receipt.json` | the day's first and last slot, its blocks and skipped slots, and the rows in each table, with the blocks compared against the chain's own list | | |


## The full archive

This sample is one day. The full archive has every day since pump.fun's first day, as daily Parquet, with these tables beside the trades:

| table | one row per | columns |
|---|---|---|
| events | a create, completion, migration or pool | `slot`, `idx`, `ts`, `kind`, and per kind: for a create, the mint, the creator field, the paying wallet, name, symbol and supply; for a migration, the mint, pool, tokens and SOL |
| signatures | a transaction | `slot`, `idx`, `signature` |
| holder balance changes | a change in any wallet's balance of a pump.fun coin, by trade or transfer | `slot`, `idx`, `mint`, `owner`, `after`, `delta` |
| completeness receipt | a UTC day | first and last slot, blocks, slots the chain skipped, rows per table |

- **Joins:** every table carries `slot` and `idx`, and the signatures table joins all of them on that pair, this sample's trades included. Several trades in one transaction share its signature.
- **No first-seen time:** the archive is read from Solana's ledger, not recorded from a stream, so block time is the only time.
- **Scale:** September 2026 was 821.1 million landed trades (about 30 GB), 358.0 million failed trades (2.8 GB), 2.0 million events (0.2 GB), 1.09 billion signatures (74 GB) and 941.6 million balance changes (17 GB), across 8,828,944 blocks.
- **Licence of the full files:** internal research use; aggregate results (statistics, charts, backtest results, findings) are yours to publish, but not the rows, or datasets that could stand in for them. This sample stays CC BY 4.0.

The full history, any month or a custom cut: support@pumpdata.fun, or the quote form at [pumpdata.fun/pump-fun-bulk-data](https://pumpdata.fun/pump-fun-bulk-data?utm_source=hf&utm_medium=listing&utm_campaign=open).

## The UTC day

A row belongs to the day when its **block time** is in `[2026-10-15T00:00:00Z, 2026-10-16T00:00:00Z)`. Block time is the
Solana block's own timestamp (unix seconds), the same `ts` every pumpdata call uses. For a failed trade it's the
time of the block the failed transaction landed in (the archive's `blocks.parquet`, by slot). Midnight
`00:00:00Z` is in. The next midnight is in the next day.

Rows with no coin are left out: PumpSwap trades in a pool the archive has no creation record for, and failed
multi-hop routes (PumpSwap's `multi_hop_swap`, since October 7, 2026), which go through several pools and name no single
coin. A landed trade routed through `multi_hop_swap` is kept: its coin comes from its pool's creation record. The
receipt counts the rows in these files, and the summary counts what was left out.

## Columns

Rows are ordered by `(ts, slot, idx, failed)` within and across shards (shard `00000` comes first).

| column | type | meaning |
|---|---|---|
| `block_time` | timestamp, UTC | block time, as a timestamp |
| `ts` | int64 | block time, unix seconds |
| `slot` | int64 | Solana slot |
| `idx` | int32 | the transaction's 0-based position in its block, the same number in every table of the archive: several trades in one transaction share it, and a landed and a failed row never do. With `slot` it is the transaction's key; the full archive's signatures table joins on (`slot`, `idx`) |
| `venue` | string | `curve` (the pump.fun bonding curve) or `pumpswap` (a PumpSwap pool) |
| `venue_code` | string | the archive's raw venue code. Curve codes are `c`, `curve`, `bonding_curve` or `0`, and any other code is PumpSwap (`scripts/build_crossings.py` `CURVE_VENUES`). The coverage table lists the codes present |
| `failed` | bool | `false`: the trade landed. `true`: the transaction tried a curve or PumpSwap trade, made it into a block and failed (`error` says why). Failed rows have no amounts and no reserves, only who tried what, the fee they paid and the error |
| `mint` | string | the coin's mint address. On a PumpSwap row it is the pool's token that is not WSOL, whichever side of the pool it sits on: a pool can be created with WSOL as its base (`pool_base_mint`), and the coin is then the pool's quote |
| `pool` | string | the PumpSwap pool address. Null on curve rows and on failed rows (the archive keeps no pool for a failed trade) |
| `migration_pool` | bool | PumpSwap landed rows only: `true` when `pool` is the coin's own pump.fun migration pool quoted in WSOL (its `migrate` and `pool` events, as pumpdata's base rates count it), `false` for any other pool trading the mint (third-party pools, other quotes). Null on curve and failed rows |
| `wallet` | string | the trader. On a landed trade, the account the program's own trade event names as the user: usually the transaction's fee payer, but a router or program can trade for a wallet, and that account need not sign the transaction. On a failed row, the transaction's fee payer |
| `side` | string | `buy` or `sell`, of the coin in `mint`, whatever the pool's orientation |
| `sol_lamports` | int64 | SOL in the trade, lamports (1 SOL = 1e9), before the protocol, LP and creator fees (a buyer pays them on top; a seller receives this less them). Null on failed rows, and null when the coin traded against a token other than SOL (`quote_mint`) |
| `token_amount` | int64 | the coin's amount in the trade, base units (pump.fun coins have 6 decimals). Null on failed rows. A buy that empties the bonding curve and goes on into the new pool in the same instruction (pump.fun's PostCompleteBuyEvent, since October 7, 2026) is one row with both parts |
| `quote_mint` | string | what the coin traded against: WSOL (`So111...112`) for SOL, or the token for a curve or pool quoted in one (pump.fun's custom pairs since May 2026, other PumpSwap pools). Null on failed rows |
| `quote_amount` | int64 | the amount of `quote_mint` in the trade, in its base units, before fees; equal to `sol_lamports` when `quote_mint` is WSOL. Null on failed rows |
| `r1`, `r2`, `r3` | float64 | reserves as the archive's parser stores them. Null on failed rows. **Curve:** `r1` is the SOL reserve (lamports) and `r2` the token reserve (base units), price in SOL per token = `(r1 / 1e9) / (r2 / 1e6)`. **PumpSwap:** `r1` is the coin's reserve and `r2` the reserve of `quote_mint` before the trade (in base units; lamports for WSOL), whichever side of the pool each is on, and `r3` is a quote-side amount pumpdata adds to the quote reserve when it prices a pool (null on pools created with WSOL as the base). Pool rows before about epoch 1030 carry no `r3`. pumpdata's pricing is `_mcap_sql()` in `scripts/build_crossings.py` |
| `pool_base_mint`, `pool_quote_mint` | string | PumpSwap landed rows: the pool's base and quote mints as created on chain (so a pool with WSOL as its base shows here). Null on curve and failed rows, and when the pool's creation is not in the archive |
| `fee_lamports` | int64 | failed rows only: the fee the failed transaction paid, lamports |
| `error` | string | failed rows only: the transaction's error as the runtime reported it |
| `epoch` | int32 | the archive epoch the row was read from |

## Reading it

```python
import duckdb
duckdb.sql("SELECT venue, failed, count(*) FROM 'data/*.parquet' GROUP BY ALL")
```

```python
import pandas as pd
df = pd.read_parquet("data/")  # pyarrow; block_time comes back tz-aware UTC
```

With the day's other tables (when they are in this folder), each trade with its transaction's signature:

```python
duckdb.sql("""SELECT t.slot, t.idx, t.mint, t.wallet, t.side, t.failed, s.signature
              FROM 'data/*.parquet' t JOIN 'signatures/*.parquet' s USING (slot, idx) LIMIT 5""")
```

## Changes

- 2026-10-27: the introduction names the events, signatures and receipt, and says the rows are those the archive ties to a coin.
- 2026-10-27: re-exported from the archive as re-read on October 21 to 25, whose reader also takes trades on custom-pair curves and more kinds of failed trade (+20,926 landed and +1,030,321 failed rows against the first export); the day's events, signatures and completeness receipt added; `idx` described as the transaction's position in its block.
- 2026-10-17: first export.
- 2026-11-03: re-exported with each row's coin named from the coin's side. In pools created with WSOL as their base (5,323,298 landed rows) `mint` had said WSOL, with the coin's amount in `sol_lamports` and WSOL's in `token_amount`; trades routed through PumpSwap's multi_hop_swap had no coin and were left out (+96,737 landed rows now); a buy that empties the bonding curve is one row with its pool part (302 rows); new columns `quote_mint`, `quote_amount`, `pool_base_mint`, `pool_quote_mint`, and `sol_lamports` is null when the coin traded against a token other than SOL.

## Made by

`scripts/export_sample.py` in pumpdata (utah, the archive's own parquet: `trades.parquet`, `fails.parquet`,
`blocks.parquet`, `events.parquet` per epoch), `2026-11-03T02:41:43Z`.

