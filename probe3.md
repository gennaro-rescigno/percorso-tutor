# Schede complete dei dataset pumpdata (15 ottobre 2026) e trenches (agosto 2026)

## pumpdatafun/pump-fun-trades-sample / README.md

```
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
- config_name: launches
  data_files:
  - split: train
    path: launches/*.parquet
- config_name: graduations
  data_files:
  - split: train
    path: graduations/*.parquet
---
# pumpdata sample: one UTC day of pump.fun and PumpSwap trades, failed trades kept

One UTC day, **2026-10-15**, of every pump.fun bonding-curve trade and every PumpSwap trade the pumpdata.fun archive
ties to a coin, with the trades that failed on chain kept beside the ones that landed. Beside them are the day's events (creates, migrations, pools), its launches and graduations, every transaction's signature, and a receipt that checks the day's blocks against the chain. It's read from
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
| shards / size | 4 / 1,373.4 MB |

| shard | rows | size |
|---|---|---|
| `data/pumpdata-2026-10-15-00000-of-00004.parquet` | 12,802,709 | 434.4 MB |
| `data/pumpdata-2026-10-15-00001-of-00004.parquet` | 12,802,709 | 414.8 MB |
| `data/pumpdata-2026-10-15-00002-of-00004.parquet` | 12,802,709 | 402.8 MB |
| `data/pumpdata-2026-10-15-00003-of-00004.parquet` | 3,822,283 | 121.4 MB |

Beside the trades, the same day's other tables and its receipt:

| path | what | rows | size |
|---|---|---|---|
| `events/` | creates, completions, migrations, pools and the rest: `slot`, `idx`, `kind`, `ts`, and `a` to `f` by kind | 75,466 | 4.6 MB |
| `signatures/` (7 files) | one row per transaction: `slot`, `idx`, `signature` | 40,955,595 | 2,773.7 MB |
| `launches/` | the day's pump.fun launches: mint, creator, payer, name, symbol, supply, decimals and the quote token its curve trades against | 46,540 | 3.4 MB |
| `graduations/` | the pool leg of each buy that completed a curve: tokens out, quote in, LP, creator and buyback fees, pool reserves before and after | 302 | 37 KB |
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

Rows are ordered by `(ts, slot, idx, failed, seq)` within and across shards (shard `00000` comes first).

| column | type | meaning |
|---|---|---|
| `block_time` | timestamp, UTC | block time, as a timestamp |
| `ts` | int64 | block time, unix seconds |
| `slot` | int64 | Solana slot |
| `idx` | int32 | the transaction's 0-based position in its block, the same number in every table of the archive: several trades in one transaction share it, and a landed and a failed row never do. With `slot` it is the transaction's key; the full archive's signatures table joins on (`slot`, `idx`) |
| `seq` | int32 | the row's 0-based place among its transaction's rows (landed and failed counted apart), in execution order. Several trades of one coin in one transaction are told apart by it, and so are the identical rows of a failed transaction that tried several trade instructions (one row each) |
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
| `quote_amount` | int64 | the amount of `quote_mint` in the trade, in its base units, before fees; equal to `sol_lamports` when `quote_mint` is WSOL. Null on failed rows. On a token-quoted curve, several trades of one coin in one transaction each get their own amount, matched by `seq`; null in the rare case the quote records do not line up one for one with the trades (`summary.json` `fixes.curve_token_quoted_unsplit`) |
| `r1`, `r2`, `r3` | float64 | reserves as the archive's parser stores them. Null on failed rows. **Curve:** after the trade, `r1` is the virtual SOL reserve (lamports), `r2` the virtual token reserve (base units) and `r3` the real SOL reserve (lamports), as pump.fun's trade event reports them; price in SOL per token = `(r1 / 1e9) / (r2 / 1e6)`. In Mayhem-mode coins pump.fun's Mayhem program also moves the virtual SOL reserve between trades, so use `r3` for SOL in and out and treat `r1` as the curve's pricing state, not a running sum of trades. This export does not yet flag Mayhem-mode coins. **PumpSwap:** `r1` is the coin's reserve and `r2` the reserve of `quote_mint` before the trade (in base units; lamports for WSOL), whichever side of the pool each is on, and `r3` is a quote-side amount pumpdata adds to the quote reserve when it prices a pool (null on pools created with WSOL as the base). Pool rows before about epoch 1030 carry no `r3`. pumpdata's pricing is `_mcap_sql()` in `scripts/build_crossings.py` |
| `pool_base_mint`, `pool_quote_mint` | string | PumpSwap landed rows: the pool's base and quote mints as created on chain (so a pool with WSOL as its base shows here). Null on curve and failed rows, and when the pool's creation is not in the archive |
| `fee_lamports` | int64 | failed rows only: the fee the failed transaction paid, lamports. It is the transaction's fee, repeated on each of its rows: count it once per (`slot`, `idx`) |
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

With the day's other tables (when they are in this folder), each trade with its transaction's signature, and a
completing buy's pool leg beside its curve row:

```python
duckdb.sql("""SELECT t.slot, t.idx, t.mint, t.wallet, t.side, t.failed, s.signature
              FROM 'data/*.parquet' t JOIN 'signatures/*.parquet' s USING (slot, idx) LIMIT 5""")
duckdb.sql("""SELECT t.slot, t.idx, t.mint, t.token_amount, g.token_amount AS pool_leg_tokens, g.lp_fee, g.creator_fee
              FROM 'data/*.parquet' t JOIN 'graduations/*.parquet' g USING (slot, idx, mint, wallet) LIMIT 5""")
```

In `data/`, a curve-completing buy is one row with both parts (the curve's and the pool's) added together;
`graduations/` holds the pool part alone, with its fees and the pool's reserves before and after.

## Changes

- 2026-10-27: the introduction names the events, signatures and receipt, and says the rows are those the archive ties to a coin.
- 2026-10-27: re-exported from the archive as re-read on October 21 to 25, whose reader also takes trades on custom-pair curves and more kinds of failed trade (+20,926 landed and +1,030,321 failed rows against the first export); the day's events, signatures and completeness receipt added; `idx` described as the transaction's position in its block.
- 2026-10-17: first export.
- 2026-11-03: re-exported with each row's coin named from the coin's side. In pools created with WSOL as their base (5,323,298 landed rows) `mint` had said WSOL, with the coin's amount in `sol_lamports` and WSOL's in `token_amount`; trades routed through PumpSwap's multi_hop_swap had no coin and were left out (+96,737 landed rows now); a buy that empties the bonding curve is one row with its pool part (302 rows); new columns `quote_mint`, `quote_amount`, `pool_base_mint`, `pool_quote_mint`, and `sol_lamports` is null when the coin traded against a token other than SOL.
- 2026-11-03: new column `seq`, each row's place in its transaction in execution order, which tells apart several trades of one coin in one transaction and the identical rows of a failed transaction that tried several trade instructions; `quote_amount` filled per trade by it (4,732 token-quoted curve rows were null); new tables `launches/` (the day's 46,540 launches with the quote token each curve trades against) and `graduations/` (the pool leg of each of the 302 curve-completing buys, with its fees and the pool's reserves); the columns say how `r1`, `r2` and `r3` read on the curve, Mayhem-mode coins included, and to count a failed transaction's fee once.

## Made by

`scripts/export_sample.py` in pumpdata (utah, the archive's own parquet: `trades.parquet`, `fails.parquet`,
`blocks.parquet`, `events.parquet` per epoch), `2026-11-03T20:51:17Z`.

```

## hussxamg04/trenches-pumpfun-forward-2026-08 / README.md

```
---
license: other
license_name: polyform-noncommercial-1.0.0
license_link: https://polyformproject.org/licenses/noncommercial/1.0.0/
task_categories:
  - tabular-classification
  - time-series-forecasting
language:
  - en
tags:
  - solana
  - blockchain
  - defi
  - memecoin
  - pump-fun
  - bonding-curve
  - point-in-time
  - leakage
  - market-microstructure
  - tabular
  - finance
size_categories:
  - 100K<n<1M
pretty_name: Trenches pump.fun Forward Capture 2026-08
configs:
  - config_name: observations
    data_files: observations.parquet
  - config_name: features
    data_files: features.parquet
  - config_name: labels
    data_files: labels.parquet
  - config_name: truth_set
    data_files: truth_set.parquet
---

# Trenches pump.fun Forward Capture, 2026-08

A point-in-time observational dataset of Solana bonding-curve token launches.
730,850 observations over 85,442 mints across 4 venues, captured live from
2026-08-06T22:40:47Z to 2026-08-13T01:07:50Z at a 75.0 s poll cadence, with
**a derivability timestamp per field block on every row**.

That last property is the point of the dataset. Most financial tabular releases
carry one timestamp per row and leave the reader to argue about whether a
feature was knowable at decision time. Here each field block carries its own
`tau__` stamp in epoch milliseconds, so leakage is a quantity you compute
rather than a claim you make. The dataset ships with a worked example of the
stamps catching a real leak: the post-reach block passes an as-stamped replay
and fails an honest audit, because it resolves a median 20.52 s after the
instant it is stamped with.

Total download: 104,654,533 bytes (99.8 MB) across 13 files, of which
104,580,833 bytes (99.7 MB) are the 9 data files.

## Files

| File | Rows | Columns | Bytes |
| --- | --- | --- | --- |
| `observations.parquet` | 730,850 | 124 | 46,320,372 |
| `curve_paths.jsonl.gz` | 1,361 mints, 289,952 events | nested | 20,025,085 |
| `features.parquet` | 85,442 | 103 | 11,502,368 |
| `launch_windows.jsonl.gz` | 999 mints, 52,389 events | nested | 10,359,921 |
| `post_ids.csv` | 59,915 | 3 | 4,729,263 |
| `split.json` | 85,442 mints | 3 partitions | 4,439,538 |
| `labels.parquet` | 84,584 | 17 | 3,795,182 |
| `account_state.jsonl.gz` | 84,584 | 9 | 2,956,239 |
| `truth_set.parquet` | 3,676 | 19 | 452,865 |
| `MANIFEST.json` | 9 entries | n/a | 17,633 |
| `DATASHEET.md` | n/a | n/a | 30,639 |
| `README.md` | n/a | n/a | 13,741 |
| `dataset-metadata.json` | n/a | n/a | 11,687 |

`MANIFEST.json` carries a SHA-256, a row count, a column count and a source
attribution for every file. `DATASHEET.md` is the full datasheet, following
Gebru et al. (2021).

## Quick start

```python
import pandas as pd

features = pd.read_parquet("features.parquet")     # 85,442 rows, 103 columns
labels = pd.read_parquet("labels.parquet")         # 84,584 rows, 17 columns
panel = features.merge(labels[["mint", "path_completed", "n_obs", "segment"]],
                       on="mint", how="inner")     # 84,584 rows

import json
split = json.load(open("split.json"))
train = panel[panel["mint"].isin(set(split["in_sample"]))]      # 50,812 pump.fun mints
test = panel[panel["mint"].isin(set(split["out_of_sample"]))]   # 30,059 pump.fun mints

print(panel["path_completed"].mean())   # 0.011350, that is 1.135%
```

Loading through `datasets`:

```python
from datasets import load_dataset

observations = load_dataset("Tr4m0ryp/trenches-pumpfun-forward-2026-08", "observations", split="train")
print(observations.num_rows)            # 730850
```

The point-in-time panel is the larger file and rewards column pruning:

```python
import pyarrow.parquet as pq

table = pq.read_table("observations.parquet",
                      columns=["mint", "seen_at_ms", "gate_inputs__holder_count",
                               "tau__gate_inputs", "tau__reach", "tau__reach_read"])
print(table.num_rows)                   # 730850
```

## What is in each file

**`observations.parquet`** is the instrument record: one row per poll per
token, 730,850 rows. Column families are `gate_inputs__*` (24 vendor screen
numerics), `vendor_audit__*` (12 vendor audit numerics), `verdict__*` and
`gate__<name>__ran` / `__passed` (the live screen's decision over 6 gates),
`reach__*` (35 dehydrated X columns), `fold__*` (10 chain aggregates), 7 chain
scalars, and 10 `tau__` stamps.

**`features.parquet`** is the modelling panel: one row per mint at first
sighting, 85,442 rows and 103 columns, with curve-progress proxies excluded.

**`labels.parquet`** carries the outcome per pump.fun mint, 84,584 rows. Use
`path_completed` (960 true, 1.135%), the chain reading. `graduated` (880 true)
is the live resolver's independent call. **`y_theta_70` is degenerate in this
release and is false on every row**; see the limitations below.

**`split.json`** is a forward-only time split at 2026-08-08T21:38:15Z with a
10,800 s embargo: 51,311 mints in sample, 30,359 out of sample, 3,772
embargoed. It holds mint addresses, not row indices. No shuffling. Seed
20260814.

**`account_state.jsonl.gz`** is the terminal read of every pump.fun bonding
curve account, 84,584 records, 960 with the completion flag set. It is the
source of `path_completed`, published so the label is checkable.

**`curve_paths.jsonl.gz`** and **`launch_windows.jsonl.gz`** are decoded
per-trade chain data: 342,341 priced bonding-curve events with slot, block
time, transaction index, signed SOL and token amounts, post-trade virtual and
real reserves, and the trading wallet. They cover 2026-05-08T22:33:37Z to
2026-06-10T17:41:33Z and **do not join to the capture**: the intersection with
the 85,442 captured mints is 0 mints.

**`truth_set.parquet`** is 3,676 mints entered by tracked traders, with an
adjudicated boolean outcome (304 true, 8.27%) and a generated English
rationale. All 3,676 are present in the capture.

**`post_ids.csv`** is the dehydrated X layer: 59,915 rows of
`mint,post_id,seen_at_ms` over 20,495 distinct post identifiers.

## What is withheld

**Post content is not published.** Redistributing tweet text breaches X's
developer terms, so this is a dehydrated release: `text`, `author_handle`,
`author_description`, `conversation_id` and `author_id` are removed, and so
are the vendor's copies of the token's social links (`twitter`,
`twitter_handle`, `website`, `telegram`). Derived numerics are kept, because a
count is a measurement rather than content: view, like, reply, retweet, quote
and bookmark counts, follower and following counts, account age in seconds,
post character count, and the verified, blue-verified, default-profile,
default-avatar and protected flags.

To rehydrate, take `post_ids.csv` and call `GET /2/tweets?ids=<up to 100 ids>`
with a bearer token. Posts deleted since 2026-08 will not return.

**The raw vendor payload is withheld pending terms review.** Each captured row
held the vendor's API response verbatim, 133 keys. Republishing a commercial
API response wholesale is a question this project has not answered, so the
whole block is excluded. What is published instead are the 36 numeric fields
the study actually consumed, as `gate_inputs__*` and `vendor_audit__*`.
`features.parquet` is derived from exactly those.

**Chain data is published in full.** Curve paths, launch windows, account
state, completion labels and split indices are decoded public Solana state and
carry no restriction.

No credentials, keys or keyed endpoint URLs appear anywhere. Endpoint names
only. The bundle is scanned before release by `src/release/secretscan.py`,
which reads decoded columns rather than compressed bytes.

## Limitations you must read before using this

**The base rate is a property of the instrument, not of the market.** The
completion rate here is 1.135% (960 of 84,584 mints). The historical
832,941-launch corpus for the same venue runs at 0.198%. The vendor feed is
weighted toward launches already near completion, so this dataset is roughly
five times enriched. Report every rate against 1.07%, never against 0.198%,
and state which population you mean.

**There is a 69.09-hour gap, and it is not random with respect to time of
day.** Observations stop at 2026-08-10T00:37:48Z and resume at
2026-08-12T21:43:12Z. A second gap of 2.09 hours follows on 2026-08-12. The
capture spans 146.45 hours and observes 75.27 of them. Because the gap is an
outage rather than a sample, it removes the same clock positions on three
consecutive days. Every mint carries a `segment` column, `pre_gap` or
`post_gap`, and every result should state which side it was measured on.

**Chain state covers pump.fun only, 84,584 of 85,442 mints.** The other 858
mints launched on `ray_launchpad` (394), `meteora_dbc` (277) and `sugar` (187)
and have vendor and reach data but no outcome. Do not pool venues in a rate.

**The terminal label has precision 1.000 and recall 0.917, and recall falls
with observation count.** Judging the live resolver against the chain reading
over 84,584 mints: 880 true positives, 0 false positives, 80 false negatives.
Recall by number of looks is 0.9686 at 1 look, 0.9658 at 2, 0.9630 at 3 to 4,
0.9321 at 5 to 9, and 0.8333 at 10 or more. The resolver fires on absence from
the feed, so a mint that lingered is the one it is slowest to catch. Prefer
`path_completed`, and stratify by `n_obs`.

**`y_theta_70` is unusable.** The per-trade curve-path pull for this
population exhausted its RPC budget at 0.0 coverage, so `path_status` reads
`error:not_pulled` on all 84,584 rows, `max_progress_path` is null throughout,
and the peak-progress label is false everywhere. It is kept in the schema so
the failure is visible rather than silently dropped.

**The reach block is not derivable at first sighting.** Over the 56,593 reach
blocks present at first sighting, the corrected read stamp lands a median
20.52 s after the recorded stamp, minimum 15.60 s, 95th percentile 35.49 s,
maximum 96.58 s, and never earlier: 0 of 56,593 resolve before their stamp.
The block therefore carries `tau__reach_read` alongside `tau__reach`, and
`reach_derivable_at_decision` is true on 0 of 85,442 mints. Every `reach_*`
column is outside the admissible feature set. Additionally, `reach__route` is
`guest` on all 346,972 rows carrying a block, meaning the credential-free
fallback served the whole capture at roughly 1% of the primary route's
throughput, so reach coverage is a floor.

**1,225 mints (1.4337%) carry a negative age at first sighting, minimum
-27.6723 s.** A token cannot be observed before it is created, so this is a
stamp error. The known mechanism is that the capture client writes `seen_at`
before it issues the vendor call. It is unresolved and reported as a bound:
read every observer-stamped field as derivable at `seen_at + 27.68 s`, which
costs 28.2% of the 75.0 s cadence, or accept a lookahead of up to 27.68 s and
say so.

**Curve-progress proxies must not be used as features.** `features.parquet`
already excludes them. `observations.parquet` keeps them, under
`gate_inputs__progress`, `gate_inputs__market_cap`, `gate_inputs__liquidity`,
`market_cap_sol`, `vault` and `vault_implied_volume_sol`, because it is the
raw instrument record. A screen on `first_progress >= 0.70` returns a
30.4-fold lift at 100% precision purely by construction. The full 21-name ban
list is in `DATASHEET.md`.

**`launch_windows.jsonl.gz` was repaired.** The source file is a multi-member
gzip whose first member was truncated by an interrupted writer, so a plain
`gzip.open` returns 130 of 999 records without raising. The released copy is
recovered member by member and rewritten as one clean member.

## Field reference: the tau stamps

| Column | Meaning |
| --- | --- |
| `tau__gate_inputs` | derivability time of the vendor screen block, epoch ms |
| `tau__vendor_audit` | derivability time of the vendor audit block, epoch ms |
| `tau__reach` | as-recorded stamp of the X reach block, the poll instant |
| `tau__reach_read` | **corrected** stamp: when the X read actually resolved |
| `tau__fold` | derivability time of the chain fold aggregates |
| `tau__chain_volume_sol` | derivability time of folded chain volume |
| `tau__fees_sol` | derivability time of the fee reading |
| `tau__market_cap_sol` | derivability time of the SOL market capitalisation |
| `tau__vault` | derivability time of the creator vault address |
| `tau__vault_implied_volume_sol` | derivability time of vault-implied volume |

A field is admissible for a decision at time `t` when its stamp is strictly
less than `t`. Observer-recorded fields use the observation instant, never a
vendor-supplied creation timestamp, and the resulting algebra is a bound
rather than an identity.

## Citation

```bibtex
@misc{ouallaf2026trenches,
  title        = {Trenches pump.fun Forward Capture 2026-08: a point-in-time
                  dataset of Solana bonding-curve launches with per-field
                  derivability stamps},
  author       = {Ouallaf, Moussa},
  year         = {2026},
  howpublished = {Hugging Face Hub},
  url          = {https://huggingface.co/datasets/Tr4m0ryp/trenches-pumpfun-forward-2026-08},
  note         = {730,850 observations over 85,442 mints, 2026-08-06 to
                  2026-08-13. X layer dehydrated, raw vendor payload withheld.}
}
```

The measurement programme this dataset was built for:

```bibtex
@misc{ouallaf2026retrenched,
  title  = {reTRENCHed: Measuring Where Memecoin Edge Is Not},
  author = {Ouallaf, Moussa},
  year   = {2026}
}
```

## Licence

PolyForm Noncommercial License 1.0.0. Source-available, noncommercial use with
attribution, no resale. Copyright Keygraph, Inc.

Two carve-outs apply independently. The blockchain-derived files describe
public ledger state that no one owns, so the licence covers this compilation
and its derived columns rather than the underlying public facts. Any content
recovered by rehydrating `post_ids.csv` comes from X under X's terms, not
under this licence.

```

## hussxamg04/trenches-pumpfun-forward-2026-08 / DATASHEET.md

```
# Datasheet: trenches-pumpfun-forward-2026-08

A point-in-time observational dataset of Solana bonding-curve token launches,
captured live between 2026-08-06 and 2026-08-13, with per-field derivability
timestamps.

This datasheet follows the structure proposed in Gebru et al., "Datasheets for
Datasets" (Communications of the ACM 64(12), 2021). Every number below was
recomputed from the released files by `src/release/panel_stats.py` and
`src/release/build.py`, not copied from an earlier analysis.

---

## 1. Motivation

**For what purpose was the dataset created?**

To measure whether a machine can predict, at the moment a token launch first
becomes visible, that the launch will fill its bonding curve. The research
question is where reproducible edge in the Solana memecoin market comes from,
and the answer this programme reached was deflationary. The dataset is the
instrument, released so that the deflationary result can be checked and so
that the same instrument can be pointed at other questions.

The design constraint that shaped every file here: a feature attached to a
decision at time `t` must be provably derivable from data observable strictly
before `t`. That is why each observation carries `tau__` stamps per field
rather than one timestamp per row. The stamps are the distinguishing feature
of this dataset. They exist so that a leak is visible as a number instead of
being an argument.

**Who created the dataset and who funded it?**

Moussa Ouallaf, as part of the reTRENCHed measurement programme. Self-funded.
No sponsor had review rights over the results.

**Any other comments?**

The dataset records what a trader on this venue actually sees, because the
vendor feed under study is the one participants read. That choice makes the
population under study the vendor's population, which is a limitation stated
explicitly in section 6.

---

## 2. Composition

**What do the instances represent?**

Three kinds of instance, joined by Solana mint address.

1. **Observations** (`observations.parquet`, 730,850 rows, 124 columns). One
   row per poll per token. A poll is a read of the vendor's launch feed at a
   75.0 s cadence; a token appears once per poll for as long as it stays in
   the feed. Covers 85,442 distinct mints across 4 bonding-curve venues.
2. **Mints** (`features.parquet` 85,442 rows and 103 columns,
   `labels.parquet` 84,584 rows and 17 columns, `split.json`,
   `account_state.jsonl.gz` 84,584 rows, `truth_set.parquet` 3,676 rows). One
   row per mint.
3. **Trades** (`curve_paths.jsonl.gz` 1,361 mints carrying 289,952 decoded
   curve events, `launch_windows.jsonl.gz` 999 mints carrying 52,389 events).
   One JSON object per mint holding an ordered list of priced on-chain trades.

**How many instances are there in total?**

| File | Rows | Columns | Compressed bytes |
| --- | --- | --- | --- |
| `observations.parquet` | 730,850 | 124 | 46,320,372 (44.2 MB) |
| `curve_paths.jsonl.gz` | 1,361 | nested | 20,025,085 (19.1 MB) |
| `features.parquet` | 85,442 | 103 | 11,502,368 (11.0 MB) |
| `launch_windows.jsonl.gz` | 999 | nested | 10,359,921 (9.9 MB) |
| `post_ids.csv` | 59,915 | 3 | 4,729,263 (4.5 MB) |
| `split.json` | 85,442 mints | 3 partitions | 4,439,538 (4.2 MB) |
| `labels.parquet` | 84,584 | 17 | 3,795,182 (3.6 MB) |
| `account_state.jsonl.gz` | 84,584 | 9 | 2,956,239 (2.8 MB) |
| `truth_set.parquet` | 3,676 | 19 | 452,865 (442 KB) |
| **Total, 9 data files** | | | **104,580,833 (99.7 MB)** |

`MANIFEST.json` (17,633 bytes) carries a SHA-256, a row count, a column count
and a source attribution for each of those 9 files. With it and the three
documentation files the released directory is 104,654,533 bytes (99.8 MB) over
13 files.

**Does the dataset contain all possible instances or is it a sample?**

It is a sample, and the sampling is the single most important thing to
understand about it. The observations are every token the vendor's `trenches`
feed returned during the capture window, in three feed buckets: `new_creation`
(527,305 rows), `pump` (197,095 rows) and `near_completion` (6,450 rows). The
feed is curated by the vendor and weighted toward launches that are already
progressing. It is not a census of Solana token creations, and it is not a
random sample of one.

The two trade-level files are a different and earlier population entirely, see
section 6.

**What data does each instance consist of?**

`observations.parquet` columns, by family:

- **Identity and context** (8): `mint`, `symbol`, `seen_at_ms`, `bucket`,
  `curve_family`, `chain_decodable`, `platform_queried`, `age_seconds`.
- **`gate_inputs__*`** (24): the vendor's numeric screen fields at the poll
  instant. Curve progress, market capitalisation, liquidity, 24-hour volume
  and swap counts, holder count and concentration rates, creator balance
  share, fresh-wallet and bundler rates, creator funding address and its
  timestamp, and the derived social flags.
- **`vendor_audit__*`** (12): the vendor's fee decomposition and its own
  labels (`is_wash_trading`, `rug_ratio`, sniper and insider hold rates,
  bot and smart trader counts). These are captured for comparison against
  chain, never as screen inputs.
- **`verdict__*`** (6) and **`gate__<name>__ran` / `__passed`** (12): the live
  screen's decision at that poll, over six gates: `social_attention`,
  `fake_chart`, `holder_concentration`, `unconnected_funding`, `not_a_bundle`,
  `entry_band`.
- **`reach__*`** (35): the X post reach block, dehydrated. See section 4.
- **`fold__*`** (10) and 7 chain scalars: transaction counts, lamport volume
  and fee totals folded from confirmed blocks in a 250-transaction window,
  plus the creator vault address and the volume it implies.
- **`tau__*`** (10): one derivability timestamp per field block, in epoch
  milliseconds, plus the corrected `tau__reach_read`.

**Is there a label or target?**

Yes, in `labels.parquet`, one row per pump.fun mint.

- `path_completed` (bool, 960 true, 1.135% of 84,584) is the chain reading:
  the bonding curve's real SOL reserve reached the 85 SOL graduation
  threshold, or the program's own `complete` flag was set. It is sourced from
  `account_state.jsonl.gz`, which is published so the label can be checked
  rather than trusted.
- `graduated` (bool, 880 true, 1.040%) is the live resolver's independent
  call, made during the capture.
- `y_theta_70` (bool) is **degenerate in this release and must not be used**.
  It is false on all 84,584 rows. See section 6.

**Is any information missing from individual instances?**

Yes, extensively, and by design in two cases and by circumstance in others.

- The raw vendor payload (`vendor_raw`, 133 keys) is withheld. See section 4.
- Post text, handles and profile copy are removed. See section 4.
- `reach__*` is null on 383,878 of 730,850 observation rows, because the token
  carried no X post link or the link pointed at an account rather than a post.
- Chain fold columns are null on most rows: the chain budget was 10 mints per
  cycle, selected youngest first, so a fold is present only where the budget
  reached that mint.
- `labels.parquet` covers 84,584 of the 85,442 mints, the pump.fun subset. The
  other 858 mints launched on `ray_launchpad` (394), `meteora_dbc` (277) and
  `sugar` (187), venues for which this project has no curve decoder.

**Are relationships between instances made explicit?**

Yes, through `mint`. `labels.parquet`, `features.parquet`, `split.json`,
`account_state.jsonl.gz` and `truth_set.parquet` all key on it, and all
3,676 truth-set mints and all 84,584 labelled mints are present in
`features.parquet`. `curve_paths.jsonl.gz` and `launch_windows.jsonl.gz` do
**not** join: their mint sets intersect the capture in 0 rows.

**Are there recommended data splits?**

Yes, `split.json`: a forward-only time split at 2026-08-08T21:38:15Z, 51,311
mints in sample, 30,359 out of sample, 3,772 embargoed. The embargo is
10,800 s, derived as the 99th percentile of the observed resolution horizon
rounded up to the next whole hour, and it is an upper bound rather than a
measurement. No shuffling is used anywhere. Seed 20260814.

**Are there errors, sources of noise, or redundancies?**

Yes. Sections 3, 4 and 6 enumerate them. The important ones are the 69.09-hour
gap, the reach layer's 20.5 s median lag, the 1,225 negative first-sighting
ages, the degenerate `y_theta_70`, and a repaired source file.

**Is the dataset self-contained?**

Yes for every published column. The X layer is deliberately not self-contained:
`post_ids.csv` and `reach__post_id` are pointers into X, and re-fetching them
is subject to X's terms and to whatever has since been deleted. Section 4
gives the rehydration procedure.

**Does the dataset contain confidential, offensive, or personal data?**

No credentials, keys or endpoint URLs. `src/release/secretscan.py` reads every
decoded column and every decompressed line and checks eight credential
patterns plus a forbidden-column list; it passes on this bundle.

The dataset does contain **public blockchain addresses**: mint addresses,
creator funding addresses (8,333 distinct), creator vault addresses (20,200
distinct), and per-trade `user` wallet addresses inside the two trade files.
These are pseudonymous public ledger entries, published by the Solana network
itself, and they are the object of study. They are not de-anonymised here and
no attempt is made to link them to identities.

It also contains 24,582 distinct token `symbol` strings, which are creator-
chosen on-chain metadata. 22 of them contain a URL or an at-sign. They are
public chain state and are published under that heading; they can be re-read
from any Solana node given the mint address, which is also published.

Some token launches in this market are scams by construction. The dataset
describes them; it does not endorse them.

---

## 3. Collection Process

**How was the data acquired?**

Three layers, on a hard ladder from cheapest and most authoritative to most
expensive.

1. **Chain.** Solana JSON-RPC over 12 endpoints. Confirmed blocks decoded into
   priced curve events. Ground truth: on any conflict with a vendor, chain
   wins.
2. **Vendor.** The GMGN `market trenches` endpoint, polled at a 75.0 s cadence
   for two feed buckets. This is the layer that defines the population.
3. **Post reach.** X post view, like, reply and follower counts. View count is
   not on chain and the vendor carries the post's identity but not its reach,
   which is the standing exception to the ladder.

Endpoint **names** are recorded; no keyed URL appears in any artifact.

**Over what timeframe was the data collected?**

The capture ran from 2026-08-06T22:40:47Z to 2026-08-13T01:07:50Z, a span of
146.45 hours, of which **75.27 hours carry observations**. The run was
supervised by a crontab watchdog and restarted 38 times.

The trade-level files predate the capture and were pulled on 2026-08-01 and
2026-08-03 over a chain window running 2026-05-08T22:33:37Z to
2026-06-10T17:41:33Z.

**What was the sampling strategy?**

Exhaustive within the vendor feed: every row the feed returned on every poll
was written. Selection into the chain layer was budgeted, 10 mints per cycle,
youngest first, and explicitly **independent of the screen's verdict**, so the
chain layer is not conditioned on the model's own decisions.

**Who collected the data?**

An unattended capture supervisor written for this project
(`src/screen/capture/`), running on a single host, holding a per-run file lock
so a second writer cannot interleave the append-only files.

**Were the individuals notified, and did they consent?**

Not applicable in the usual sense, and worth stating plainly. The chain layer
is public ledger data published by the network. The vendor layer is a
commercial API read under its terms. The reach layer concerns public posts by
accounts that chose to post publicly, and it is the one layer where the
question bites; the response is that this release publishes **no post content
and no account identity**, only post identifiers and numeric measurements. An
account holder who deletes a post removes it from any rehydration of this
dataset, which is the practical consent mechanism a dehydrated release
provides.

**Has an ethical review process been conducted?**

No institutional review board reviewed this. The publication constraints in
section 4 were adopted as the operative standard instead.

---

## 4. Preprocessing, Cleaning and Labeling

### 4.1 What was removed before release, and why

Three constraints govern this bundle. They are encoded as data in
`src/release/policy.py` so that they are auditable in one file.

**C1. The X layer is dehydrated.** Redistributing post content breaches X's
developer terms. Standard academic practice is to publish identifiers and let
users re-fetch. Dropped from every reach block:

| Field | Kind |
| --- | --- |
| `text` | post body |
| `author_handle` | account handle |
| `author_description` | profile biography |
| `conversation_id` | thread identifier |
| `author_id` | stable account identifier |

`author_id` is not required by the constraint, since it is neither free text
nor a handle. It is dropped anyway because `post_id` rehydrates it at no cost,
and publishing a durable per-account key adds linkage risk for no measurement.

Dropped from `gate_inputs` under the same rule, being the vendor's verbatim
copy of the token's social links:

| Field | Kind |
| --- | --- |
| `twitter` | X post or profile URL |
| `twitter_handle` | account handle |
| `website` | free-text URL |
| `telegram` | free-text URL |

**Kept**, because a count is a measurement rather than content: `post_id`,
`views`, `likes`, `replies`, `retweets`, `quotes`, `bookmarks`,
`author_followers`, `author_following`, `author_statuses`,
`author_media_count`, `author_listed`, `author_favourites`,
`author_normal_followers`, `author_fast_followers`, `n_urls`, `n_hashtags`,
`n_mentions`, `n_media`, `author_verified`, `author_blue_verified`,
`author_default_profile`, `author_default_avatar`, `author_protected`,
`is_quote`, `possibly_sensitive`, `status`, `route`, `lang`.

**Derived in place of the dropped text**, as numerics: `reach__text_len`
(character count), `reach__post_created_at_ms` and
`reach__author_created_at_ms` (the two X timestamp strings parsed to epoch
milliseconds), `reach__post_age_s` and `reach__author_age_s` (account age at
the read, the measurement the study used), `reach__present`.

*Rehydration.* Take `post_ids.csv` (59,915 mint-to-post pairs over 20,495
distinct post identifiers) and call `GET /2/tweets?ids=<up to 100 ids>` with a
bearer token, requesting `tweet.fields=text,created_at,public_metrics` and
`expansions=author_id`. Posts deleted or made private since 2026-08 will not
return. Recovered content is subject to X's terms, not to this dataset's
licence.

**C2. The raw vendor payload is excluded.** `vendor_raw` held the GMGN API
response verbatim, **133 keys** per row including `logo_small_base64`,
translated names, community names and every field the study never used.
Republishing a vendor's response wholesale is a terms question this project has
not answered, so **the entire block is withheld pending terms review**. A
reader should know it exists and that its absence is a legal caution rather
than an absence of data.

What is published in its place are the numeric projections the study actually
consumed: `gate_inputs__*` (24 fields, the screen set) and `vendor_audit__*`
(12 fields, the audit set). `features.parquet` is derived from exactly these.

**C3. Chain data is published in full.** `curve_paths.jsonl.gz`,
`launch_windows.jsonl.gz`, `account_state.jsonl.gz`, `labels.parquet` and
`split.json` are decoded public Solana state. Nothing is withheld.

### 4.2 Columns banned as progress proxies (R-6)

`features.parquet` excludes curve progress and every monotone transform of it,
because the label is derived from the curve and a curve reading that defines
the label cannot be allowed to predict it. Verified absent from the released
file at build time:

```
progress                     gate_inputs.progress          vendor_raw.progress
first_progress               max_progress                  max_progress_path
progress_at_first_sighting   market_cap                    gate_inputs.market_cap
vendor_raw.market_cap        usd_market_cap                gate_inputs.usd_market_cap
vendor_raw.usd_market_cap    market_cap_sol                price
vendor_raw.price             liquidity                     gate_inputs.liquidity
vendor_raw.liquidity         vault_implied_volume_sol      vault
```

Also excluded from `features.parquet` by scope: `fold`, `fold_window_txs`,
`chain_volume_sol`, `fees_sol`, `fee_source`.

**`observations.parquet` deliberately keeps these fields**, under
`gate_inputs__progress`, `gate_inputs__market_cap`, `gate_inputs__liquidity`,
`market_cap_sol`, `vault` and `vault_implied_volume_sol`, because it is the
raw instrument record rather than a modelling panel. **Anyone building a
predictor from `observations.parquet` must drop them.** A screen on
`first_progress >= 0.70` returns a 30.4-fold lift at 100% precision purely by
construction.

### 4.3 Schema changes made for the release

- Nested blocks are flattened one level with a prefix: `gate_inputs__`,
  `vendor_audit__`, `verdict__`, `fold__`, `reach__`.
- The per-gate verdict list became 12 boolean columns,
  `gate__<name>__ran` and `gate__<name>__passed`. The per-gate free-text
  `detail` and the constant `derivability` field were not carried over.
- `reach.seen_at` (epoch seconds) became `tau__reach_read` (epoch
  milliseconds). See section 6.
- Nine `tau__` stamps are carried through **byte for byte unchanged**.

### 4.4 A repaired source file

`launch_windows.jsonl.gz` in the source repository is a multi-member gzip
whose first member was truncated mid-stream by an interrupted writer.
`gzip.open` therefore returns **130 of 999 records and raises nothing the
caller is obliged to notice**, which is the worst possible failure shape for a
published file. The released copy was recovered member by member
(`src/release/gzip_repair.py`), yielding 999 unique mints and 52,389 events,
with 1 unparseable partial line discarded, and rewritten as one clean member.

---

## 5. Uses

**Has the dataset been used already?**

Yes, for the reTRENCHed measurement programme: a pre-registered admissibility
audit, a graduation-hazard model, a screen ablation, and a key-opinion-leader
signal study. The programme's headline results are deflationary and 42 of its
own claims were retracted.

**What tasks could it be used for?**

- Binary prediction of curve completion from first-sighting features, under a
  forward-only split with a stated embargo.
- Point-in-time methodology research. The `tau__` stamps make leak detection a
  measurement rather than a code review, and the reach block is a worked
  example of a field that passes an as-stamped replay and fails an honest
  admissibility audit.
- Microstructure work on the two trade files: 342,341 decoded, priced,
  block-ordered bonding-curve trades with slot and transaction index.
- Vendor-versus-chain agreement studies. `vendor_audit__*` sits next to chain
  aggregates for the same mint and the same instant.

**Is there anything that puts users at risk of unfair treatment or harm?**

The dataset describes a market in which most participants lose money. A model
fitted here predicts an instrument-specific event on a vendor-curated
population over 7 days, and the base rate it learns is not the market's, see
section 6. Treating a completion probability from this dataset as a trading
edge is the specific misuse this programme spent four phases refuting.

**Are there tasks for which it should not be used?**

- Do not use it to estimate the market-wide rate of anything. The population
  is vendor-curated.
- Do not use `y_theta_70`. It is degenerate.
- Do not use any progress proxy as a feature.
- Do not use the reach block as a decision-time feature without a 20.5 s
  correction or an explicit admission of lookahead.
- Do not use the two trade files as if they joined to the capture.

---

## 6. Limitations

Six limitations are load-bearing. Each is stated with the number that shows it.

### 6.1 The base rate is an instrument property, not a market rate

The completion rate here is **1.135%** on the chain reading (960 of 84,584) and
**1.040%** on the live resolver's call (880 of 84,584). Restricted to the
82,320 mints whose outcome is decidable within the horizon, the resolver rate
is **1.069%**. The programme's design documents quote **1.073%** (883 of
82,323) from the label build that preceded the final rebuild; the released
files give 1.069%, and the released files are authoritative.

Against that, the historical 832,941-launch corpus for the same venue carries a
base rate of **0.198%** (1,651 graduations). This dataset's rate is roughly
five times higher, and the cause is the instrument rather than the market: the
vendor feed is weighted toward launches already near completion. **Every rate
computed on this dataset must be reported against 1.07%, never against
0.198%, and every paper using it must state which population it describes.**

### 6.2 A 69.09-hour gap, and it is not random with respect to time of day

Observations stop at **2026-08-10T00:37:48Z** and resume at
**2026-08-12T21:43:12Z**, a gap of **69.09 hours** in a 146.45-hour span. A
second gap of **2.09 hours** runs from 2026-08-12T22:48:48Z. Total observed
time is **75.27 hours**, roughly half the nominal week.

The gap is an outage, so it removes the same three clock positions on three
consecutive days rather than a random 47% of the calendar. Anything with a
diurnal component is measured on a biased clock. Every mint carries a
`segment` column, `pre_gap` (82,994 mints in the feature panel) or `post_gap`
(2,448), and **every result computed on this dataset must state which side of
the gap it was measured on.** The recommended split places the boundary before
the gap so that the out-of-sample partition straddles it.

### 6.3 Chain state covers pump.fun only, 84,584 of 85,442 mints

The capture watched 4 venues: `pumpfun` (265,865 observation rows),
`ray_launchpad` (188,078), `meteora_dbc` (144,235) and `sugar` (132,672). Only
pump.fun has a curve decoder in this project. So `labels.parquet`,
`account_state.jsonl.gz` and every chain-derived column exist for the 84,584
pump.fun mints and are **absent for the remaining 858** (394 `ray_launchpad`,
277 `meteora_dbc`, 187 `sugar`). Those 858 mints are present in
`features.parquet` and `observations.parquet` with vendor and reach data but
no outcome. Pooling venues in a rate calculation will silently mix a labelled
population with an unlabelled one.

### 6.4 The terminal label has precision 1.000 and recall 0.917, and recall falls with observation count

Judging the live resolver's `graduated` call against the chain reading
`path_completed` over all 84,584 mints:

| Metric | Value |
| --- | --- |
| True positives | 880 |
| False positives | **0** |
| False negatives | 80 |
| Precision | **1.0000** |
| Recall | **0.9167** |

Precision is exactly 1.000: the resolver never claimed a completion that the
chain did not confirm. Recall is 0.917, and it **degrades monotonically with
how many times a mint was observed**:

| Looks | Positives | Recovered | Recall |
| --- | --- | --- | --- |
| 1 | 255 | 247 | **0.9686** |
| 2 | 117 | 113 | 0.9658 |
| 3 to 4 | 108 | 104 | 0.9630 |
| 5 to 9 | 162 | 151 | 0.9321 |
| 10 or more | 318 | 265 | **0.8333** |

The mechanism is that the resolver fires on **absence from the feed**: a mint
that has stopped appearing is adjudicated. A mint observed many times is one
that lingered, and lingering mints are exactly the ones whose disappearance
the resolver is slowest to catch before the capture ends. So label quality is
correlated with `n_obs`, and `n_obs` is a stratifier in `features.parquet` for
that reason. **Prefer `path_completed` over `graduated` as the target**, and
stratify any evaluation by `n_obs`.

**A separate and more serious defect: `y_theta_70` is unusable.** The
per-trade curve-path pull for the capture population never landed, exhausting
its RPC budget at 0.0 coverage. `path_status` therefore reads
`error:not_pulled` on all 84,584 rows, `max_progress_path` is null on all of
them, and `y_theta_70`, defined as peak curve progress at or above 0.70, is
**false on every row**. It is retained in the schema so that the failure is
visible rather than quietly dropped. The peak-progress estimand ladder
reported in the programme's design documents was computed from the poll
sequence, not from this column.

### 6.5 The reach block is not derivable at first sighting

The X reach read is stamped with the poll instant, but it resolves later. Over
the **56,593** reach blocks present at first sighting, the corrected read
stamp lands a median **20.52 s** after the recorded stamp, minimum **15.60 s**,
95th percentile **35.49 s**, maximum **96.58 s**, and it is **never earlier**:
0 of 56,593 blocks resolve before their stamp. Over all 219,406 distinct reach
reads in the full panel the median lag is **30.27 s**, minimum **15.17 s**,
maximum **113.84 s**, again with 0 negatives.

The block therefore carries a corrected stamp, `tau__reach_read`, alongside the
as-recorded `tau__reach`, and `features.parquet` carries `reach_lag_ms` and
`reach_derivable_at_decision`. That last column is **true on 0 of 85,442
mints**. Every `reach_*` column is excluded from the admissible feature set for
this reason, and it is why the reach block passes an as-stamped replay and
fails an honest admissibility audit. The decision instant was **not** moved to
cover the lag; the discrepancy is flagged, not papered over.

One further caveat on this layer: `reach__route` is `guest` on **all 346,972**
rows carrying a block. The credential-free guest-token fallback served the
entire capture and the batched X v2 route never ran, which caps throughput at
roughly 1% of the primary route while the layer still reports as healthy.
Reach coverage should be read as a floor. Of those rows, 307,886 returned
metrics, 39,085 returned `not_found`, and 1 returned `unavailable`.

### 6.6 Negative ages at first sighting, unresolved and reported as a bound

**1,225 mints, 1.4337% of 85,442**, carry a negative `age_seconds` at first
sighting, with a minimum of **-27.6723 s**. Median age at first sighting is
+46.30 s. Exactly 1,225 rows of 730,850 are affected, one per affected mint.

A token cannot be observed before it is created, so this is a stamp error, not
a physical fact. The known mechanism is that the capture client writes
`seen_at` **before** it issues the vendor call, so the value returned reflects
vendor state at some instant after the stamp. That accounts for the sign, but
this release does not claim to have resolved it: the vendor's own
`created_timestamp` has its own clock and its own error, and the two cannot be
separated from the data here.

It is therefore **reported as a bound rather than corrected**. Every
observer-stamped field in this dataset should be read as derivable at
`seen_at + 27.68 s` rather than at `seen_at`, which costs 28.2% of the 75.0 s
poll cadence. Two defensible readings follow: take the bound and pay the
27.68 s, or accept a lookahead of up to 27.68 s and say so. What is not
defensible is treating `seen_at` as exact.

---

## 7. Distribution

**How will it be distributed?**

As a public dataset on Hugging Face Hub, mirrored on Kaggle. Both carry the
identical file set and the same `MANIFEST.json`, which lists a SHA-256 for
every file. The Hugging Face copy is canonical.

**When?**

On first publication of the release. This datasheet describes bundle contents
fixed at build time; `MANIFEST.json` carries the generation timestamp.

**Under what licence?**

PolyForm Noncommercial License 1.0.0. Source-available, noncommercial use with
attribution, no resale. Copyright Keygraph, Inc.

Two carve-outs a user must respect independently of that licence. The
blockchain-derived files describe public ledger state that no one owns; the
licence covers this compilation and its derived columns, not the underlying
public facts. And any content recovered by rehydrating `post_ids.csv` comes
from X under X's terms, not under this licence.

**Have any IP-based or other restrictions been imposed?**

Yes, and they are the reason for section 4. The raw vendor payload is withheld
pending terms review. The X layer is dehydrated. Neither restriction is
negotiable by a downstream user re-uploading the missing pieces.

**Do any export controls or regulatory restrictions apply?**

None known. Users are responsible for their own jurisdiction's rules on
financial data and on automated trading.

---

## 8. Maintenance

**Who will support and maintain the dataset?**

Moussa Ouallaf, through the `trenches` repository.

**How can the owner be contacted?**

Through the issue tracker of the source repository, or the contact address on
the dataset card.

**Is there an erratum?**

Corrections will be posted as a new revision on Hugging Face, with the change
recorded in `MANIFEST.json`. Known defects at first publication are section 6;
the degenerate `y_theta_70` and the repaired `launch_windows.jsonl.gz` are the
two a user is most likely to trip over.

**Will the dataset be updated?**

The capture is closed. The window ran to its pre-registered deadline and no
further observations will be appended, because extending it by restarting was
explicitly refused by the capture supervisor. Two updates are plausible and
neither would change the observations: the curve-path pull could be re-run to
give `y_theta_70` a real value, and the vendor terms review could release
`vendor_raw`.

**Will older versions continue to be supported?**

Yes. Hugging Face revisions are immutable, so a result pinned to a commit hash
stays reproducible.

**Can others extend or contribute?**

Yes. The bundling code is `src/release/` in the source repository and the
constraints are data in `src/release/policy.py`, so an extension can be
checked against the same policy that produced this release. Contributions that
would add a field must state which of the three constraints they fall under.

---

## Reproducing this bundle

```bash
python -m src.release.build --repo . --out data/release/trenches-pumpfun-forward-2026-08
python -m src.release.secretscan data/release/trenches-pumpfun-forward-2026-08
```

The first command streams 4.0 GB of append-only JSONL in one pass, applies the
three constraints at the reader, and writes `MANIFEST.json` from the resulting
bytes. The second reads every decoded column and every decompressed line and
fails loudly on a credential pattern or a forbidden field.

```
