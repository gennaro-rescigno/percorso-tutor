# Probe dei dataset gratuiti non ancora esaminati

# launchtape/solana-launch-tape
- licenza / tag: ['license:other', 'size_categories:100K<n<1M']
- ultima modifica: 2026-10-14T16:13:14.000Z · download: 388

## README.md

```
---
license: other
license_name: launch-tape-data-licence
pretty_name: Solana Launch Tape (Free 2-Hour Sample)
task_categories:
  - other
language:
  - en
tags:
  - solana
  - pump-fun
  - memecoin
  - crypto
  - trading
  - order-flow
  - liquidity
size_categories:
  - 100K<n<1M
configs:
  - config_name: default
    data_files:
      - split: gradtrades
        path: data/gradtrades-2026-10-10-1400-1600utc.jsonl.gz
      - split: pregrad
        path: data/pregrad-2026-10-10-1400-1600utc.jsonl.gz
      - split: padfeed
        path: data/padfeed-2026-10-10-1400-1600utc.jsonl.gz
      - split: meteora_pools
        path: data/meteora-pools-2026-10-10-1400-1600utc.jsonl.gz
      - split: curvetape
        path: data/curvetape-2026-10-13-1400-1600utc.jsonl.gz
      - split: launchmeta
        path: data/launchmeta-2026-10-13-1400-1600utc.jsonl.gz
      - split: gradholders
        path: data/gradholders-2026-10-14-0400-0600utc.jsonl.gz
---

# Solana Launch Tape — free 2-hour sample

Launch Tape records what actually happens on pump.fun, PumpSwap, two other Solana launchpads, and Meteora, 24/7, from public data only. This dataset is a free 2-hour sample of each of the seven files we sell by the day: 2026-10-10 14:00-16:00 UTC for the first four; `curvetape` and `launchmeta` 2026-10-13 14:00-16:00 UTC (their first day); `gradholders` 2026-10-14 04:00-06:00 UTC (on sale from that day). It is here so you can check the shape, the honesty of the recording, and whether the data answers your question before buying a full day.

- **Website / full catalog / pricing:** [launchtape.io](https://launchtape.io)
- **Contact:** launchio48@gmail.com
- **History:** short and honest. The oldest full day for sale is 2026-10-03 (`gradtrades`, `padfeed`) / 2026-10-04 (`pregrad`) / 2026-10-06 (`meteora-pools`) / 2026-10-13 (`curvetape`, `launchmeta`) / 2026-10-14 (`gradholders`), and it grows by one UTC day, every day. Coverage gaps (a dropped connection, a coin skipped under our data budget) are written into the files as rows (`down`, `up`, `resume`, `end` with a `why`) — never filled in, never guessed.

## Dataset structure

Seven splits, one per recorder, each covering 2 hours (windows above). `MANIFEST.json` and `SHA256SUMS` (in `data/`) carry exact row counts, byte sizes and checksums for every file.

| Split | Rows | What it is |
|---|---|---|
| `gradtrades` | 417,544 | Every buy/sell on PumpSwap in the first 30 minutes after each pump.fun graduation in the window: wallet, amounts, price, pool reserves, fees |
| `pregrad` | 14,417 | Who is behind each pump.fun launch in the window: creator, funding, curve buyers, graduation-slot buyers, the cap path, plus a +10 min price outcome |
| `padfeed` | 3,602 | Graduations on Meteora DBC (Bags, Jupiter Studio, ...) and Raydium LaunchLab (bonk.fun) in the window: migration facts, pool balances, top holders, US$ quote prices |
| `meteora_pools` | 23,794 | Per-minute price, TVL, volume and fees for ~200 Meteora DLMM pools, for the window |
| `curvetape` | 470,519 | Every trade on every pump.fun bonding curve in the window, from creation to graduation: wallet, tokens, SOL, fees, cap and reserves after each trade; plus creations, completions and migrations |
| `launchmeta` | 4,597 | Every new pump.fun coin's metadata (name, ticker, description, website) and a SHA-256 of its picture, at creation and at graduation |
| `gradholders` | 251 | Graduates' 20 largest token accounts with owners and shares at +1, +10 and +60 minutes |
| `graduates` (a CSV, not a split: `data/graduates-2026-10-10-1400-1600utc.csv`) | 105 | The window on one sheet, one row per pump.fun graduate: what it was, who was behind it, and what its price did in its first 10 and 30 minutes (reference = the price 10 s after graduation). Opens on a phone or in the ChatGPT / Claude app; columns explained at https://launchtape.io/#graduates |

**Every file also comes as Parquet** in `data/`, under the same name with `.parquet` (`data/pregrad-2026-10-10-1400-1600utc.parquet` and so on): the same rows in the same order, one typed column per field, checked against the `.jsonl.gz` before it ships; `MANIFEST.json` and `SHA256SUMS` cover both. One table per file: the columns are every field of every row type and a field a row does not have is null, so filter on `type` first. `t` stays integer milliseconds; nested objects are structs and arrays are lists; `padfeed`'s `usd` is a map keyed by quote mint; `pregrad`'s `curve`, `src` and `cross` (text in some row types, an object or a number in others) are text columns, an object or number as its JSON text. The paid day files come in both formats too, with these exact columns. (The splits above load the JSON lines: the `datasets` library has no type for `padfeed`'s map column, so read the Parquet copies with pandas, Polars or DuckDB, below.)

**How it's collected:** only public data (the Solana chain through the public RPC, and a paid RPC for gap repair and holder snapshots; PumpPortal's free feed; public IPFS gateways for coin metadata; Meteora's public API; Jupiter's free price API). No private keys, no logins, no scraped social profiles. No wallet labels or opinions ("insider", "rugger") — we sell what happened on chain, not our guesses about who did it. Our own trading wallets are stripped from every file. Every line is parsed and checked before export; malformed rows are dropped, not patched.

Each row is a JSON object; every row carries `type` and `t` (ms since 1970 UTC, when our recorder saw it). Full field-by-field schemas (every row type, every field) are published at launchtape.io; condensed below.

### gradtrades columns

| type | key fields | meaning |
|---|---|---|
| `grad` | `mint`, `pool`, `coinCreator`, `poolBase`/`poolQuote`, `price`, `capSol`, `curveSol`, `follow` | the graduation: starting pool state, whether this coin is followed |
| `trade` | `mint`, `side`, `user`, `baseAmount`, `quoteAmount`, `price`, `priceAfter`, `userTokensBefore`, fees, `creator` | one PumpSwap buy or sell |
| `end` | `mint`, `why`, `buys`, `sells` | coin no longer followed, with totals |
| `down`/`up`/`resume` | `t` | feed gap marker — missing, not guessed |

### pregrad columns

| type | key fields | meaning |
|---|---|---|
| `create` | `mint`, `creator`, `name`, `sym`, `devTokens`/`devSol`, `capSol` | the coin's creation and the creator's own buy |
| `curvex`/`ctrade` | `mint`, `cap`, `sol`, `side`, `user`, `tokens`, `capAfter` | curve cap crossings and trades, 200 SOL cap up to graduation |
| `record` | `mint`, `ageS`, `instant`, `creatorPctAtGrad`, `creatorInfo`, `gradSlot`, `curve` | full picture at graduation, incl. whether it filled the curve in <5s |
| `outcome` | `mint`, `capAt`, `maxGain`, `minDrop`, `crashed`, `dump`/`firstBigSell` | first 10 minutes after graduation: best/worst move vs the price 10 s after graduation (touched -80% = `minDrop` <= -80) and whether it fell 40%+ from its high (`crashed`; not an 80% drop) |

### padfeed columns

| type |
```

## KNOWN_ISSUES.md

```
(non disponibile: HTTP Error 404: Not Found)
```

## File
- `.gitattributes` 0.0 MB
- `README.md` 0.0 MB
- `data/MANIFEST.json` 0.0 MB
- `data/SHA256SUMS` 0.0 MB
- `data/curvetape-2026-10-13-1400-1600utc.jsonl.gz` 79.4 MB
- `data/curvetape-2026-10-13-1400-1600utc.parquet` 58.0 MB
- `data/gradholders-2026-10-14-0400-0600utc.jsonl.gz` 0.4 MB
- `data/gradholders-2026-10-14-0400-0600utc.parquet` 0.3 MB
- `data/gradtrades-2026-10-10-1400-1600utc.jsonl.gz` 66.4 MB
- `data/gradtrades-2026-10-10-1400-1600utc.parquet` 51.6 MB
- `data/launchmeta-2026-10-13-1400-1600utc.jsonl.gz` 1.6 MB
- `data/launchmeta-2026-10-13-1400-1600utc.parquet` 1.3 MB
- `data/meteora-pools-2026-10-10-1400-1600utc.jsonl.gz` 1.6 MB
- `data/meteora-pools-2026-10-10-1400-1600utc.parquet` 0.3 MB
- `data/padfeed-2026-10-10-1400-1600utc.jsonl.gz` 0.3 MB
- `data/padfeed-2026-10-10-1400-1600utc.parquet` 0.3 MB
- `data/pregrad-2026-10-10-1400-1600utc.jsonl.gz` 2.1 MB
- `data/pregrad-2026-10-10-1400-1600utc.parquet` 1.9 MB

### data/MANIFEST.json: 1 righe
- `product` VARCHAR
- `schemaVersion` VARCHAR
- `generated` VARCHAR
- `note` VARCHAR
- `files` STRUCT(file VARCHAR, dataset VARCHAR, "day" DATE, "window" STRUCT("from" VARCHAR, "to" VARCHAR), bytes BIGINT, sha256 VARCHAR, "rows" BIGINT, badRows BIGINT, rowsByType STRUCT(trade BIGINT, "end" BIGINT, down BIGINT, up BIGINT, grad BIGINT, curvex BIGINT, ctrade BIGINT, "create" BIGINT, migrate BIGINT, record BIGINT, outcome BIGINT, px BIGINT, qpx BIGINT, holders BIGINT, pool BIGINT, adopt BIGINT, complete BIGINT, gap BIGINT, meta BIGINT), t STRUCT("first" VARCHAR, "last" VARCHAR, min VARCHAR, max VARCHAR, ordered BOOLEAN), parquet STRUCT(file VARCHAR, bytes BIGINT, sha256 VARCHAR))[]

```
              product schemaVersion                 generated                                 note                                files
0  Solana Launch Tape             2  2026-10-14T13:14:53.758Z  Every sample is a 2-hour cut of ...  [{'file': 'gradtrades-2026-10-10...
```

### data/curvetape-2026-10-13-1400-1600utc.parquet: 470,519 righe
- `type` VARCHAR
- `t` BIGINT
- `slot` BIGINT
- `off` BIGINT
- `bt` BIGINT
- `sig` VARCHAR
- `i` BIGINT
- `mint` VARCHAR
- `side` VARCHAR
- `wallet` VARCHAR
- `tokens` DOUBLE
- `sol` DOUBLE
- `capAfter` DOUBLE
- `curveSol` DOUBLE
- `fee` DOUBLE
- `cfee` DOUBLE
- `vs` BIGINT
- `vt` BIGINT
- `ix` VARCHAR
- `mayhem` BOOLEAN
- `quote` VARCHAR
- `qAmt` BIGINT
- `vq` BIGINT
- `rq` BIGINT
- `feeQ` BIGINT
- `cfeeQ` BIGINT
- `why` VARCHAR
- `creator` VARCHAR
- `src` VARCHAR
- `trades` BIGINT
- `buys` BIGINT
- `sells` BIGINT
- `vol` DOUBLE
- `volQ` BIGINT
- `lastCap` DOUBLE
- `maxCap` DOUBLE
- `firstT` BIGINT
- `lastTradeT` BIGINT
- `role` VARCHAR
- `version` VARCHAR
- `payer` VARCHAR
- `nsig` BIGINT
- `txFee` DOUBLE
- `prioFee` DOUBLE
- `cuPrice` BIGINT
- `cuLimit` BIGINT
- `cuUsed` BIGINT
- `jitoTip` DOUBLE
- `failed` BOOLEAN
- `byCreator` BOOLEAN
- `curve` VARCHAR
- `user` VARCHAR
- `name` VARCHAR
- `sym` VARCHAR
- `uri` VARCHAR
- `tokenProgram` VARCHAR
- `rt` BIGINT
- `supply` BIGINT
- `prioCfg` BIGINT
- `pool` VARCHAR
- `solAmount` DOUBLE
- `mintAmount` DOUBLE
- `poolMigrationFee` DOUBLE
- `quoteAmount` BIGINT
- `from` BIGINT
- `to` BIGINT
- `ms` BIGINT
- `trunc` BOOLEAN
- intervallo di `slot`: 456467204 → 456499933

```
    type              t       slot   off          bt                                  sig  i                                 mint  side                               wallet        tokens       sol  capAfter   curveSol       fee      cfee            vs               vt    ix mayhem quote  qAmt  vq  rq  feeQ  cfeeQ   why creator   src  trades  buys  sells  vol  volQ  lastCap  maxCap  firstT  lastTradeT  role version payer  nsig  txFee  prioFee  cuPrice  cuLimit  cuUsed  jitoTip failed byCreator curve  user  name   sym   uri tokenProgram  rt  supply  prioCfg  pool  solAmount  mintAmount  poolMigrationFee  quoteAmount  from  to  ms trunc
0  trade  1791900000059  456467204    68  1791899999  5JN2KoxxoVLAuE2UAzLJHKnWpTAQWUVk...  0  5M9PbrKfHt3XU5DLK8FYYmPwBgwX4zj6...  sell  sagiiWi9RADqXxHtEwTjFxQNA7CeFyDt...  1.444083e+06  0.081429   56.2803  12.563632  0.000774  0.000244   42563632427  756279437965462  sell    NaN  None   NaN NaN NaN   NaN    NaN  None    None  None     NaN   NaN    NaN  NaN   NaN      NaN     NaN     NaN         NaN  None    None  None   NaN    NaN      NaN      NaN      NaN     NaN      NaN    NaN       NaN  None  None  None  None  None         None NaN     NaN      NaN  None        NaN         NaN               NaN          NaN   NaN NaN NaN   NaN
1  trade  1791900000060  456467204   137  1791899999  NvwEk5eETkbhEbgoomTPgYRKVRjjx9af...  0  AbtzvivhrP1A7fdvwzQcm2PYh7fHnxus...  sell  GjZj1uQZCJYzHVdS43wNKrAziKcjrbkD...  4.603457e+06  0.426561   91.9402  24.401791  0.004052  0.001280   54401791004  591708461713821  sell    NaN  None   NaN NaN NaN   NaN    NaN  None    None  None     NaN   NaN    NaN  NaN   NaN      NaN     NaN     NaN         NaN  None    None  None   NaN    NaN      NaN      NaN      NaN     NaN      NaN    NaN       NaN  None  None  None  None  None         None NaN     NaN      NaN  None        NaN         NaN               NaN          NaN   NaN NaN NaN   NaN
2  trade  1791900000060  456467204  3337  1791899999  3eeKmVnX8CbxktsvQMeTx9FPLFXCqaMQ...  0  4A68FxMhKnS81zDPKCa94TrqB9syewBe...  sell  JB1X4XNxvpRdxcWDTxdeMNw7P4K5xW38...  2.059576e+05  0.079512  385.7869  81.438232  0.000755  0.000239  111438232356  288859574262648  sell    NaN  None   NaN NaN NaN   NaN    NaN  None    None  None     NaN   NaN    NaN  NaN   NaN      NaN     NaN     NaN         NaN  None    None  None   NaN    NaN      NaN      NaN      NaN     NaN      NaN    NaN       NaN  None  None  None  None  None         None NaN     NaN      NaN  None        NaN         NaN               NaN          NaN   NaN NaN NaN   NaN
```

# hussxamg04/trenches-pumpfun-forward-2026-08
- licenza / tag: ['license:other', 'size_categories:100K<n<1M', 'format:parquet']
- ultima modifica: 2026-10-01T13:08:07.000Z · download: 233

## README.md

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
API response wholesale is a ques
```

## KNOWN_ISSUES.md

```
(non disponibile: HTTP Error 404: Not Found)
```

## File
- `.gitattributes` 0.0 MB
- `DATASHEET.md` 0.0 MB
- `MANIFEST.json` 0.0 MB
- `README.md` 0.0 MB
- `account_state.jsonl.gz` 3.0 MB
- `curve_paths.jsonl.gz` 20.0 MB
- `features.parquet` 11.5 MB
- `labels.parquet` 3.8 MB
- `launch_windows.jsonl.gz` 10.4 MB
- `observations.parquet` 46.3 MB
- `post_ids.csv` 4.7 MB
- `split.json` 4.4 MB
- `truth_set.parquet` 0.5 MB

### MANIFEST.json: 1 righe
- `dataset` VARCHAR
- `generated_at` TIMESTAMP
- `total_bytes` BIGINT
- `total_human` VARCHAR
- `n_files` BIGINT
- `provenance` STRUCT(repairs STRUCT(file VARCHAR, source_members BIGINT, members_truncated BIGINT, records_recovered BIGINT, records_a_plain_gzip_reader_returns BIGINT, unparseable_lines_discarded BIGINT)[], run_id VARCHAR, sources VARCHAR[], endpoint_names_only BOOLEAN, cadence_s DOUBLE, code VARCHAR)
- `capture_summary` STRUCT(n_rows BIGINT, n_mints BIGINT, n_post_id_rows BIGINT, n_distinct_post_ids BIGINT, buckets STRUCT(new_creation BIGINT, pump BIGINT, near_completion BIGINT), curve_families STRUCT(pumpfun BIGINT, ray_launchpad BIGINT, meteora_dbc BIGINT, sugar BIGINT), platforms_queried STRUCT("Pump.fun" BIGINT, letsbonk BIGINT, bags BIGINT, sugar BIGINT, jup_studio BIGINT), first_seen_epoch_s DOUBLE, last_seen_epoch_s DOUBLE, span_hours DOUBLE, observed_hours DOUBLE, gaps_over_10_min STRUCT(start_epoch_s DOUBLE, end_epoch_s DOUBLE, "hours" DOUBLE)[], n_gaps_over_10_min BIGINT, largest_gap_hours DOUBLE, age_at_first_sighting STRUCT(n_with_age BIGINT, n_negative BIGINT, pct_negative DOUBLE, min_s DOUBLE, median_s DOUBLE), reach STRUCT(n_rows_with_reach BIGINT, n_distinct_blocks BIGINT, median_lag_s DOUBLE, min_lag_s DOUBLE, max_lag_s DOUBLE, p95_lag_s DOUBLE, n_lag_negative BIGINT, n_lag_zero_or_positive BIGINT), keys_present_but_not_published MAP(VARCHAR, JSON), age_all_rows STRUCT(n_rows_with_age BIGINT, n_rows_negative BIGINT, n_mints_with_any_negative BIGINT, min_s DOUBLE), source VARCHAR)
- `exclusions` STRUCT(C1_x_layer_dehydrated STRUCT("rule" VARCHAR, reach_fields_dropped VARCHAR[], gate_inputs_fields_dropped VARCHAR[], kept_in_place_of_text VARCHAR[], rehydration VARCHAR), C2_raw_vendor_withheld STRUCT("rule" VARCHAR, blocks_dropped VARCHAR[], kept VARCHAR[]), C3_chain_data_unrestricted STRUCT("rule" VARCHAR, files VARCHAR[]), R6_progress_proxies_dropped_from_features VARCHAR[])
- `files` STRUCT("name" VARCHAR, bytes BIGINT, sha256 VARCHAR, "rows" BIGINT, "columns" BIGINT, format VARCHAR, derived_from VARCHAR, note VARCHAR, column_names VARCHAR[])[]

```
                            dataset        generated_at  total_bytes total_human  n_files                           provenance                      capture_summary                           exclusions                                files
0  trenches-pumpfun-forward-2026-08 2026-08-16 17:51:32    104580833     99.7 MB        9  {'repairs': [{'file': 'launch_wi...  {'n_rows': 730850, 'n_mints': 85...  {'C1_x_layer_dehydrated': {'rule...  [{'name': 'observations.parquet'...
```

### features.parquet: 85,442 righe
- `mint` VARCHAR
- `decision_ms` DOUBLE
- `n_obs` INTEGER
- `obs_band` VARCHAR
- `curve_family` VARCHAR
- `chain_decodable` BOOLEAN
- `platform_queried` VARCHAR
- `bucket` VARCHAR
- `segment` VARCHAR
- `screen_admitted` BOOLEAN
- `screen_n_abstained` TINYINT
- `screen_pass_kind` VARCHAR
- `screen_rejected_by` VARCHAR
- `gate_social_attention_passed` BOOLEAN
- `gate_social_attention_ran` BOOLEAN
- `gate_fake_chart_passed` BOOLEAN
- `gate_fake_chart_ran` BOOLEAN
- `gate_holder_concentration_passed` BOOLEAN
- `gate_holder_concentration_ran` BOOLEAN
- `gate_unconnected_funding_passed` BOOLEAN
- `gate_unconnected_funding_ran` BOOLEAN
- `gate_not_a_bundle_passed` BOOLEAN
- `gate_not_a_bundle_ran` BOOLEAN
- `gate_entry_band_passed` BOOLEAN
- `gate_entry_band_ran` BOOLEAN
- `tau__gate_inputs` DOUBLE
- `tau__vendor_audit` DOUBLE
- `tau__reach` DOUBLE
- `tau__reach_read` DOUBLE
- `reach_lag_ms` DOUBLE
- `reach_derivable_at_decision` BOOLEAN
- `holder_count` DOUBLE
- `top_10_holder_rate` DOUBLE
- `creator_balance_rate` DOUBLE
- `dev_team_hold_rate` DOUBLE
- `fresh_wallet_rate` DOUBLE
- `new_wallet_volume` DOUBLE
- `bundler_mhr` DOUBLE
- `bundler_trader_amount_rate` DOUBLE
- `volume_24h` DOUBLE
- `swaps_24h` DOUBLE
- `buys_24h` DOUBLE
- `sells_24h` DOUBLE
- `x_user_follower` DOUBLE
- `twitter_dup` DOUBLE
- `website_dup` DOUBLE
- `twitter_is_tweet` BOOLEAN
- `has_at_least_one_social` BOOLEAN
- `total_fee` DOUBLE
- `trade_fee` DOUBLE
- `priority_fee` DOUBLE
- `tip_fee` DOUBLE
- `sniper_count` DOUBLE
- `top70_sniper_hold_rate` DOUBLE
- `suspected_insider_hold_rate` DOUBLE
- `rat_trader_amount_rate` DOUBLE
- `bot_degen_count` DOUBLE
- `smart_degen_count` DOUBLE
- `rug_ratio` DOUBLE
- `is_wash_trading` BOOLEAN
- `age_seconds` DOUBLE
- `creator_funding_age_s` DOUBLE
- `tweet_age_s` DOUBLE
- `age_seconds_present` BOOLEAN
- `has_twitter` BOOLEAN
- `has_telegram` BOOLEAN
- `has_website` BOOLEAN
- `has_fund_from_address` BOOLEAN
- `creator_funding_age_present` BOOLEAN
- `tweet_age_present` BOOLEAN
- `reach_views` DOUBLE
- `reach_likes` DOUBLE
- `reach_replies` DOUBLE
- `reach_retweets` DOUBLE
- `reach_quotes` DOUBLE
- `reach_bookmarks` DOUBLE
- `reach_author_followers` DOUBLE
- `reach_author_following` DOUBLE
- `reach_author_statuses` DOUBLE
- `reach_author_media_count` DOUBLE
- intervallo di `tau__gate_inputs`: 1786056047986.6387 → 1786583270381.483
- intervallo di `reach_retweets`: 0.0 → 208961.0

```
                                  mint   decision_ms  n_obs obs_band curve_family  chain_decodable platform_queried        bucket  segment  screen_admitted  screen_n_abstained screen_pass_kind screen_rejected_by gate_social_attention_passed  gate_social_attention_ran gate_fake_chart_passed  gate_fake_chart_ran gate_holder_concentration_passed  gate_holder_concentration_ran gate_unconnected_funding_passed  gate_unconnected_funding_ran gate_not_a_bundle_passed  gate_not_a_bundle_ran gate_entry_band_passed  gate_entry_band_ran  tau__gate_inputs  tau__vendor_audit    tau__reach  tau__reach_read  reach_lag_ms  reach_derivable_at_decision  holder_count  top_10_holder_rate  creator_balance_rate  dev_team_hold_rate  fresh_wallet_rate  new_wallet_volume  bundler_mhr  bundler_trader_amount_rate   volume_24h  swaps_24h  buys_24h  sells_24h  x_user_follower  twitter_dup  website_dup  twitter_is_tweet  has_at_least_one_social  total_fee  trade_fee  priority_fee   tip_fee  sniper_count  top70_sniper_hold_rate  suspected_insider_hold_rate  rat_trader_amount_rate  bot_degen_count  smart_degen_count  rug_ratio  is_wash_trading  age_seconds  creator_funding_age_s   tweet_age_s  age_seconds_present  has_twitter  has_telegram  has_website  has_fund_from_address  creator_funding_age_present  tweet_age_present  reach_views  reach_likes  reach_replies  reach_retweets  reach_quotes  reach_bookmarks  reach_author_followers  reach_author_following  reach_author_statuses  reach_author_media_count  reach_author_listed  reach_author_favourites  reach_author_normal_followers  reach_author_fast_followers  reach_n_urls  reach_n_hashtags  reach_n_mentions  reach_n_media reach_author_verified reach_author_blue_verified reach_author_default_profile reach_author_default_avatar reach_author_protected reach_is_quote reach_possibly_sensitive reach_status reach_route reach_lang  reach_text_len  reach_post_age_s  reach_author_age_s  reach_present  reach_views_present
0  DAfZUpiYUmTn9jYHm8hLb1kG8vWm2azK...  1.786056e+12      3      3-4      pumpfun             True         Pump.fun  new_creation  pre_gap            False                   0         rejected   social_attention                        False                       True                    NaN                False                              NaN                          False                             NaN                         False                      NaN                  False                    NaN                False      1.786056e+12       1.786056e+12  1.786056e+12              inf           NaN                        False           1.0              0.0000                 0.000            0.000000             0.0000                0.0     0.000000                      0.0000     0.000000        0.0       0.0        0.0              0.0          0.0          0.0             False                    False   0.000000   0.000000      0.000000  0.000000           1.0                0.000000                       0.0000                     0.0              0.0                0.0        0.0            False    -1.013361                    NaN           NaN                 True        False         False        False                  False                        False              False          NaN          NaN            NaN             NaN           NaN              NaN                     NaN                     NaN                    NaN                       NaN                  NaN                      NaN                            NaN                          NaN           NaN               NaN               NaN            NaN                   NaN                        NaN                          NaN                         NaN                    NaN            NaN                      NaN         None        None       None             NaN               NaN                 NaN          False                False
1  Db1NHazkcf6Wv1hC659YMiKieYThkfYm...  1.786056e+12      3      3-4      pump
```

### post_ids.csv: 59,915 righe
- `mint` VARCHAR
- `post_id` BIGINT
- `seen_at_ms` BIGINT

```
                                  mint              post_id     seen_at_ms
0  Db1NHazkcf6Wv1hC659YMiKieYThkfYm...  2085496150975492228  1786056047987
1  79AUXfx8Nv7LE8jomNDWydhvetrtJCTb...  2085494376981995533  1786056047987
2  itS8vX5edChjMC5fsmUNWPZNjDK378wb...  2085495979965366658  1786056047987
```

# AratiKamat/red-pump-2026
- licenza / tag: ['license:cc-by-4.0', 'size_categories:100K<n<1M', 'format:json']
- ultima modifica: 2026-10-13T23:34:18.000Z · download: 205

## README.md

```
---
license: cc-by-4.0
pretty_name: RED-PUMP-2026 pump.fun token launches
language:
- en
tags:
- finance
- cryptocurrency
- solana
- pump.fun
- market-microstructure
- measurement-error
- tabular
size_categories:
- 100K<n<1M
configs:
- config_name: launches
  data_files: red_pump_2026_v1_launches.jsonl.gz
  default: true
---

# RED-PUMP-2026: pump.fun token launches with collector-recorded labels (May to June 2026)

**Canonical source and DOI:** this is a mirror of the data files of **RED-PUMP-2026-v1** on Zenodo.
Please cite the concept DOI **[10.5281/zenodo.20633486](https://doi.org/10.5281/zenodo.20633486)**, which always resolves to the latest version.
The full deposit (code, pre-specified analysis protocol, manuscript and documentation) is on Zenodo; the data files here are byte-identical to the published version.

**Author:** Arati Uday Kamat (ORCID [0009-0000-4781-312X](https://orcid.org/0009-0000-4781-312X)) · **License:** CC BY 4.0

## What it is

A public record of **860,213 token-launch records (860,194 unique mints)** on the Solana launch platform pump.fun, created between **2026-05-08 17:14 UTC and 2026-06-10 18:11 UTC**, together with a per-mint terminal label recorded by the author's data collector within 24 hours of launch.

It is useful for studying launch activity, the metadata of new tokens (social links, description length, initial market capitalisation), and, above all, **how outcome labels produced by a data collector differ from platform-side events**.

## Files

| File | Rows | Contents | SHA-256 |
|---|---:|---|---|
| `red_pump_2026_v1_launches.jsonl.gz` | 860,213 | One JSON object per launch record: `seenAt`, `t`, `mint`, `symbol`, `name`, `created_timestamp` (ms), `initial_market_cap_sol`, `has_twitter`, `has_website`, `has_telegram`, `description_length` | `042940379e8c897ac97403e6b25a5b302fb32b6902a8fc0cef4ab70ac11e8f84` |
| `red_pump_2026_v1_outcomes.csv.gz` | 833,192 data lines | Collector-recorded terminal label per mint: `outcome` (`GRADUATED` or `TIMEOUT`), `note` (`bonding_curve_filled` or `no_graduation_within_24h`), timing and market-cap fields | `c0a327ea442d91c6f970b2bad9a2a9b778e163d8c3eb38f71eccd3e92209a974` |
| `reconstructed_mint_observation_windows_v1.parquet` | 860,194 | Per-mint reconstructed observation windows and analysis flags used in the accompanying paper | `f785a812a38445fedd222e357eede246132ae69dffc4ed62131246614d39bfd5` |

## Dataset viewer and loading

The dataset viewer shows the **launches** table. The Hub viewer reads one file format per repository, so the outcomes file (`.csv.gz`) and the observation-window file (`.parquet`) are not in the viewer. They are kept here unchanged, byte-identical to Zenodo, and load directly:

```python
from datasets import load_dataset
import pandas as pd
from huggingface_hub import hf_hub_download

repo = "AratiKamat/red-pump-2026"
launches = load_dataset(repo, "launches", split="train")

windows = pd.read_parquet(
    hf_hub_download(repo, "reconstructed_mint_observation_windows_v1.parquet", repo_type="dataset"))

# Tolerant read: the outcomes file mixes two schemas and has a few malformed lines (see below).
outcomes = pd.read_csv(
    hf_hub_download(repo, "red_pump_2026_v1_outcomes.csv.gz", repo_type="dataset"),
    on_bad_lines="skip", low_memory=False)
```

## Important: what the label means

- The `GRADUATED` / `TIMEOUT` label is the **collector's own classification**, made by polling pump.fun for the 50 newest tokens on each poll, **not** the platform-side bonding-curve completion event.
- In the paper's primary window, `GRADUATED` labels were written about **1 to 6 minutes after on-chain creation**. In practice, the label means "completed while the token was still among the 50 newest tokens on a poll"; it is not a record of every platform-side completion.
- Update (October 2026): in August 2026 an outside analyst first questioned the collector's coverage, and my own audit of the collector's code and logs confirmed the limit (it saw only the 50 newest tokens on each poll, so graduations could be missed). I updated the dataset and paper (Zenodo v1.6; arXiv 2607.02823 v4). The updated version no longer reports the earlier survival-analysis claims made with this dataset (graduation-rate and hazard-ratio estimates); they should not be cited. The launch data are unchanged. The current accompanying paper is a measurement audit: *Auditing Collector-Generated Graduation Labels on Pump.fun: Measurement Error and Temporal Non-Generalization* (arXiv:2607.02823).

## Known data-quality notes

- The outcomes file mixes an early 8-field schema and a later 11-field schema. A small number of lines are malformed (for example, commas inside token symbols, and truncated or blank lines). Read it with a tolerant CSV parser. The full reconciliation (category counts) is documented in the Zenodo deposit.
- Token names and symbols are public on-chain metadata created by third parties, and are reproduced as recorded. Some contain offensive text.

## How to cite

> Kamat, A. U. (2026). *RED-PUMP-2026-v1: A public benchmark of 860,213 pump.fun token launches with collector-generated terminal labels (May–June 2026 regime)* [Data set]. Zenodo. https://doi.org/10.5281/zenodo.20633486

```bibtex
@dataset{kamat_redpump_2026,
  author    = {Kamat, Arati Uday},
  title     = {{RED-PUMP-2026-v1}: A public benchmark of 860,213 pump.fun
               token launches with collector-generated terminal labels
               (May--June 2026 regime)},
  year      = {2026},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.20633486},
  url       = {https://doi.org/10.5281/zenodo.20633486}
}
```

```

## KNOWN_ISSUES.md

```
(non disponibile: HTTP Error 404: Not Found)
```

## File
- `.gitattributes` 0.0 MB
- `CITATION.cff` 0.0 MB
- `LICENSE.txt` 0.0 MB
- `README.md` 0.0 MB
- `SHA256SUMS` 0.0 MB
- `reconstructed_mint_observation_windows_v1.parquet` 91.8 MB
- `red_pump_2026_v1_launches.jsonl.gz` 47.9 MB
- `red_pump_2026_v1_outcomes.csv.gz` 43.6 MB

### reconstructed_mint_observation_windows_v1.parquet: 860,194 righe
- `mint` VARCHAR
- `t` BIGINT
- `seenAt` VARCHAR
- `created_timestamp` BIGINT
- `ordinal_index` BIGINT
- `initial_market_cap_sol` DOUBLE
- `has_twitter` BOOLEAN
- `has_website` BOOLEAN
- `has_telegram` BOOLEAN
- `description_length` BIGINT
- `estimated_first_invisible_poll_N40` BIGINT
- `estimated_last_visible_poll_N40` BIGINT
- `estimated_exit_midpoint_N40` BIGINT
- `ordinal_exit_time_40` BIGINT
- `estimated_first_invisible_poll_N45` BIGINT
- `estimated_last_visible_poll_N45` BIGINT
- `estimated_exit_midpoint_N45` BIGINT
- `ordinal_exit_time_45` BIGINT
- `estimated_first_invisible_poll` BIGINT
- `estimated_last_visible_poll` BIGINT
- `estimated_exit_midpoint` BIGINT
- `ordinal_exit_time_50` BIGINT
- `estimated_first_invisible_poll_N55` BIGINT
- `estimated_last_visible_poll_N55` BIGINT
- `estimated_exit_midpoint_N55` BIGINT
- `ordinal_exit_time_55` BIGINT
- `estimated_first_invisible_poll_N60` BIGINT
- `estimated_last_visible_poll_N60` BIGINT
- `estimated_exit_midpoint_N60` BIGINT
- `ordinal_exit_time_60` BIGINT
- `feed_exit_time_primary` BIGINT
- `observable_minutes` DOUBLE
- `tie_boundary` BOOLEAN
- `poll_gap_seconds` FLOAT
- `overflow_risk` VARCHAR
- `reconstruction_confidence` VARCHAR
- `reconstruction_confidence_reason` VARCHAR
- `outcome` VARCHAR
- `graduated_at_ms` DOUBLE
- `minutes_to_outcome` DOUBLE
- `final_market_cap_sol` DOUBLE
- `created_at_chain_iso` VARCHAR
- `minutes_to_outcome_chain` DOUBLE
- `detection_lag_min` DOUBLE
- `event` TINYINT
- `recon_violation` BOOLEAN
- `observed_last_visible_time` DOUBLE
- `analysis_time` DOUBLE
- `graduation_detected` TINYINT
- `event_minutes` DOUBLE
- `mcap_changed` BOOLEAN
- `no_outcome_reason` VARCHAR
- `restart_censoring` BOOLEAN
- `enters_primary` BOOLEAN
- `cohort_v3_primary` BOOLEAN
- `dev_set` BOOLEAN
- `validation_set` BOOLEAN
- intervallo di `created_timestamp`: 1778260478000 → 1781115061000
- intervallo di `ordinal_exit_time_40`: 1778260604000 → 1781115068000
- intervallo di `ordinal_exit_time_45`: 1778260643000 → 1781115068000
- intervallo di `ordinal_exit_time_50`: 1778260932000 → 1781115068000
- intervallo di `ordinal_exit_time_55`: 1778260937000 → 1781115068000
- intervallo di `ordinal_exit_time_60`: 1778260957000 → 1781115068000
- intervallo di `feed_exit_time_primary`: 1778260875639 → 1781115068532
- intervallo di `observed_last_visible_time`: 1778296913195.0 → 1780964495352.0
- intervallo di `analysis_time`: 0.0 → 10.500883333333332

```
                                  mint              t                    seenAt  created_timestamp  ordinal_index  initial_market_cap_sol  has_twitter  has_website  has_telegram  description_length  estimated_first_invisible_poll_N40  estimated_last_visible_poll_N40  estimated_exit_midpoint_N40  ordinal_exit_time_40  estimated_first_invisible_poll_N45  estimated_last_visible_poll_N45  estimated_exit_midpoint_N45  ordinal_exit_time_45  estimated_first_invisible_poll  estimated_last_visible_poll  estimated_exit_midpoint  ordinal_exit_time_50  estimated_first_invisible_poll_N55  estimated_last_visible_poll_N55  estimated_exit_midpoint_N55  ordinal_exit_time_55  estimated_first_invisible_poll_N60  estimated_last_visible_poll_N60  estimated_exit_midpoint_N60  ordinal_exit_time_60  feed_exit_time_primary  observable_minutes  tie_boundary  poll_gap_seconds overflow_risk reconstruction_confidence     reconstruction_confidence_reason  outcome  graduated_at_ms  minutes_to_outcome  final_market_cap_sol created_at_chain_iso  minutes_to_outcome_chain  detection_lag_min  event  recon_violation  observed_last_visible_time  analysis_time  graduation_detected  event_minutes  mcap_changed no_outcome_reason  restart_censoring  enters_primary  cohort_v3_primary  dev_set  validation_set
0  4yHyBE7T7RnWGquYv2Uic4SkErnv4jGY...  1778260658493  2026-05-08T17:17:38.493Z      1778260478000              0               33.000000         True         True         False                   0                       1778260658493                    1778260658493                1778260658493         1778260604000                       1778260658493                    1778260658493                1778260658493         1778260643000                   1778261092785                1778260658493            1778260875639         1778260932000                       1778261092785                    1778260658493                1778260875639         1778260937000                       1778261092785                    1778260658493                1778260875639         1778260957000           1778260875639              3.6191         False               0.0        severe                       Low  gap>120|batch=50|restart|inferre...  TIMEOUT     1.778347e+12              1441.3             33.000000                                            NaN                NaN      0            False                         NaN         3.6191                    0            NaN         False                                False            True              False     True           False
1  G2N1XMyY2hpoymDmtnHBx6X3vp3TBaaD...  1778260658493  2026-05-08T17:17:38.493Z      1778260481000              1               30.250039        False        False         False                  51                       1778260658493                    1778260658493                1778260658493         1778260610000                       1778260658493                    1778260658493                1778260658493         1778260643000                   1778261092785                1778260658493            1778260875639         1778260932000                       1778261092785                    1778260658493                1778260875639         1778260945000                       1778261092785                    1778260658493                1778260875639         1778260959000           1778260875639              3.6191         False               0.0        severe                       Low  gap>120|batch=50|restart|inferre...  TIMEOUT     1.778347e+12              1441.3             30.250039                                            NaN                NaN      0            False                         NaN         3.6191                    0            NaN         False                                False            True              False     True           False
2  DyAojSTXZR1pRDHGfkzmTeJZ1CJnQGej...  1778260658493  2026-05-08T17:17:38.493Z      1778260483000              2               30.000000  
```

### red_pump_2026_v1_outcomes.csv.gz: errore InvalidInputException: Invalid Input Error: CSV Error on Line: 161422
Original Line: 2026-05-14T01:33:12.246Z,KJYkam8yi921WokpP8xeP62craTGiE6zfkBJYwMpump,4CHUD |,TIMEOUT,1440.0,30,30.193651282,no_graduation_within_24h,2026-05-13T01:33:08.000Z,1440.07,0.05
Expected Number of Columns: 1 Found: 2
Possible fixes:
* Enable nul

# cryptodata/pumpfun-dataset-light
- metadati non disponibili: HTTP Error 401: Unauthorized

## README.md

```
(non disponibile: HTTP Error 401: Unauthorized)
```

## KNOWN_ISSUES.md

```
(non disponibile: HTTP Error 401: Unauthorized)
```
- elenco dei file non disponibile: HTTP Error 401: Unauthorized

# pumpdatafun/pump-fun-trades-sample
- licenza / tag: ['license:cc-by-4.0', 'size_categories:10M<n<100M', 'format:parquet']
- ultima modifica: 2026-11-03T20:55:13.000Z · download: 1519

## README.md

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
| `venue_code` | string | the archive's raw venue code. Curve codes are `c`, `curve`, `bonding_cur
```

## KNOWN_ISSUES.md

```
(non disponibile: HTTP Error 404: Not Found)
```

## File
- `.gitattributes` 0.0 MB
- `README.md` 0.0 MB
- `data/pumpdata-2026-10-15-00000-of-00004.parquet` 434.4 MB
- `data/pumpdata-2026-10-15-00001-of-00004.parquet` 414.8 MB
- `data/pumpdata-2026-10-15-00002-of-00004.parquet` 402.8 MB
- `data/pumpdata-2026-10-15-00003-of-00004.parquet` 121.4 MB
- `events/pumpdata-2026-10-15-events.parquet` 4.6 MB
- `graduations/pumpdata-2026-10-15-graduations.parquet` 0.0 MB
- `launches/pumpdata-2026-10-15-launches.parquet` 3.4 MB
- `receipt.json` 0.0 MB
- `signatures/pumpdata-2026-10-15-signatures-00000-of-00007.parquet` 449.6 MB
- `signatures/pumpdata-2026-10-15-signatures-00001-of-00007.parquet` 450.2 MB
- `signatures/pumpdata-2026-10-15-signatures-00002-of-00007.parquet` 450.3 MB
- `signatures/pumpdata-2026-10-15-signatures-00003-of-00007.parquet` 449.9 MB
- `signatures/pumpdata-2026-10-15-signatures-00004-of-00007.parquet` 449.9 MB
- `signatures/pumpdata-2026-10-15-signatures-00005-of-00007.parquet` 449.6 MB
- `signatures/pumpdata-2026-10-15-signatures-00006-of-00007.parquet` 74.2 MB
- `summary.json` 0.0 MB

### data/pumpdata-2026-10-15-00000-of-00004.parquet: 12,802,709 righe
- `block_time` TIMESTAMP WITH TIME ZONE
- `ts` BIGINT
- `slot` BIGINT
- `idx` INTEGER
- `seq` INTEGER
- `venue` VARCHAR
- `venue_code` VARCHAR
- `failed` BOOLEAN
- `mint` VARCHAR
- `pool` VARCHAR
- `migration_pool` BOOLEAN
- `wallet` VARCHAR
- `side` VARCHAR
- `sol_lamports` BIGINT
- `token_amount` BIGINT
- `quote_mint` VARCHAR
- `quote_amount` BIGINT
- `r1` DOUBLE
- `r2` DOUBLE
- `r3` DOUBLE
- `pool_base_mint` VARCHAR
- `pool_quote_mint` VARCHAR
- `fee_lamports` BIGINT
- `error` VARCHAR
- `epoch` INTEGER
- intervallo di `block_time`: 2026-10-15 00:00:00+00:00 → 2026-10-15 08:07:42+00:00
- intervallo di `ts`: 1792022400 → 1792051662
- intervallo di `slot`: 457030039 → 457164981
- intervallo di `sol_lamports`: 0 → 4990000000000
- intervallo di `fee_lamports`: 5000 → 2700005000

```
                 block_time          ts       slot  idx  seq  venue venue_code  failed                                 mint  pool migration_pool                               wallet  side  sol_lamports    token_amount                           quote_mint  quote_amount            r1            r2            r3 pool_base_mint pool_quote_mint  fee_lamports error  epoch
0 2026-10-15 00:00:00+00:00  1792022400  457030039  106    0  curve          c   False  4yssA3q3qSDvFPFb1EJQopg3xfQtyLNX...  None            NaN  58eyjtdbPDf5nPfW6Q31vvBysGjKtdGZ...  sell     361213150   2893532145701  So111111111111111111111111111111...     361213150  6.321072e+10  5.092490e+14  3.321072e+10           None            None           NaN  None   1057
1 2026-10-15 00:00:00+00:00  1792022400  457030039  108    0  curve          c   False  4t4WhFYxUmjVS9mLuvPB9bemLKc7FFsW...  None            NaN  FHwR5RdMt9iibdh6UNjVdoqNNkya6CRo...  sell    1466639795  34166373040903  So111111111111111111111111111111...    1466639795  3.644650e+10  8.832124e+14  6.446500e+09           None            None           NaN  None   1057
2 2026-10-15 00:00:00+00:00  1792022400  457030039  110    0  curve          c   False  4t4WhFYxUmjVS9mLuvPB9bemLKc7FFsW...  None            NaN  6byytWSuRCMfgsjJV32vVHQPCEqnfrqk...  sell     649633376  16028337623548  So111111111111111111111111111111...     649633376  3.579687e+10  8.992408e+14  5.796867e+09           None            None           NaN  None   1057
```

### events/pumpdata-2026-10-15-events.parquet: 75,466 righe
- `slot` UBIGINT
- `idx` UINTEGER
- `kind` VARCHAR
- `ts` BIGINT
- `a` VARCHAR
- `b` VARCHAR
- `c` VARCHAR
- `d` VARCHAR
- `e` VARCHAR
- `f` VARCHAR
- intervallo di `slot`: 457030039 → 457429521
- intervallo di `ts`: 1792022400 → 1792108799

```
        slot  idx    kind          ts                                    a                                    b                                    c                                    d             e                 f
0  457030039  415    pool  1792022400  So111111111111111111111111111111...  6mt6VQhbd26FK4nqPhHuPqsMq3PrivRF...  7wRPmkGg84hPbJMsfUwGg79APduKTrmG...  Bz4eytxCL8kzroQKKgCZhwUF1dD1R4wR...  168000000000   217799968320904
1  457030045   66  create  1792022401  7xWcYfVmBwXx1vHZgN5MrdYNX3gzJ35f...  9jwfZT1V4rvG8ZRdfR8gQfu9yYKSmZee...  9jwfZT1V4rvG8ZRdfR8gQfu9yYKSmZee...                             Kirkcoin          Kirk  1000000000000000
2  457030048  417  create  1792022401  DKqreigeHRrprvz7zduATdY3442dgVbs...  J7mfert6r5L39pydN2tq8CjEbAgvoq66...  J7mfert6r5L39pydN2tq8CjEbAgvoq66...                      lamb in a lamb          Lambo  1000000000000000
```

### graduations/pumpdata-2026-10-15-graduations.parquet: 302 righe
- `block_time` TIMESTAMP WITH TIME ZONE
- `ts` BIGINT
- `slot` BIGINT
- `idx` INTEGER
- `mint` VARCHAR
- `wallet` VARCHAR
- `quote_mint` VARCHAR
- `token_amount` BIGINT
- `quote_amount` BIGINT
- `lp_fee` BIGINT
- `creator_fee` BIGINT
- `buyback_fee` BIGINT
- `pool_base_before` BIGINT
- `pool_quote_before` BIGINT
- `pool_base_after` BIGINT
- `pool_quote_after` BIGINT
- intervallo di `block_time`: 2026-10-15 00:05:25+00:00 → 2026-10-15 23:58:18+00:00
- intervallo di `ts`: 1792022725 → 1792108698
- intervallo di `slot`: 457031549 → 457429059

```
                 block_time          ts       slot  idx                                 mint                               wallet                           quote_mint   token_amount  quote_amount    lp_fee  creator_fee  buyback_fee  pool_base_before  pool_quote_before  pool_base_after  pool_quote_after
0 2026-10-15 00:05:25+00:00  1792022725  457031549  147  7WzmwZz6jRWvmjW1E99BHyptWi7BX5nD...  6aUfMzy4RH7Xomko2SikeqqLcWctHWZY...  So111111111111111111111111111111...   817034213792     336951827   3201043      1010856      1600521   206900000000000        84990359592  206082965786208       85327311419
1 2026-10-15 00:11:04+00:00  1792023064  457033108  914  GqNEGPLMevz3zxDwe91drc8oeFAbVdBE...  3dL83TFwgc7zzRvscDnLoK99sEVvU39f...  So111111111111111111111111111111...  3669462917536    1534557629  14578298      4603673      7289149   206900000000000        84990359061  203230537082464       86524916690
2 2026-10-15 00:15:58+00:00  1792023358  457034484  601  DLjxHm4YUs13fiT9Hy2LFQ527swmig4k...  GLLth2eP23BAwYrFZqpdz1QmkcaBx7RN...  So111111111111111111111111111111...    78196750119      32133799    305272        96402       152636   206900000000000        84990361332  206821803249881       85022495131
```

### launches/pumpdata-2026-10-15-launches.parquet: 46,540 righe
- `block_time` TIMESTAMP WITH TIME ZONE
- `ts` BIGINT
- `slot` BIGINT
- `idx` INTEGER
- `mint` VARCHAR
- `creator` VARCHAR
- `payer` VARCHAR
- `name` VARCHAR
- `symbol` VARCHAR
- `supply` BIGINT
- `decimals` INTEGER
- `quote_mint` VARCHAR
- intervallo di `block_time`: 2026-10-15 00:00:01+00:00 → 2026-10-15 23:59:59+00:00
- intervallo di `ts`: 1792022401 → 1792108799
- intervallo di `slot`: 457030045 → 457429521

```
                 block_time          ts       slot  idx                                 mint                              creator                                payer             name    symbol            supply  decimals                           quote_mint
0 2026-10-15 00:00:01+00:00  1792022401  457030045   66  7xWcYfVmBwXx1vHZgN5MrdYNX3gzJ35f...  9jwfZT1V4rvG8ZRdfR8gQfu9yYKSmZee...  9jwfZT1V4rvG8ZRdfR8gQfu9yYKSmZee...         Kirkcoin      Kirk  1000000000000000         6  So111111111111111111111111111111...
1 2026-10-15 00:00:01+00:00  1792022401  457030048  417  DKqreigeHRrprvz7zduATdY3442dgVbs...  J7mfert6r5L39pydN2tq8CjEbAgvoq66...  J7mfert6r5L39pydN2tq8CjEbAgvoq66...  lamb in a lamb      Lambo  1000000000000000         6  So111111111111111111111111111111...
2 2026-10-15 00:00:01+00:00  1792022401  457030048  493  HUiZt33xM11DvHqGYqpwqhSGRgKbABkQ...  89qB5wopBMW95BZLPfcApihXCMwoKqLg...  89qB5wopBMW95BZLPfcApihXCMwoKqLg...         lift.fun  lift.fun  1000000000000000         6  So111111111111111111111111111111...
```

### receipt.json: 1 righe
- `day` DATE
- `first_slot` BIGINT
- `last_slot` BIGINT
- `slots_in_range` BIGINT
- `blocks` BIGINT
- `slots_skipped` BIGINT
- `rows` STRUCT(trades_landed BIGINT, trades_failed BIGINT, events BIGINT, signatures BIGINT, launches BIGINT, graduations BIGINT)
- `check` STRUCT(against VARCHAR, chain_blocks BIGINT, in_chain_not_here BIGINT, here_not_in_chain BIGINT)
- intervallo di `first_slot`: 457030039 → 457030039
- intervallo di `last_slot`: 457429525 → 457429525
- intervallo di `slots_in_range`: 399487 → 399487
- intervallo di `blocks`: 399170 → 399170
- intervallo di `slots_skipped`: 317 → 317

```
         day  first_slot  last_slot  slots_in_range  blocks  slots_skipped                                 rows                                check
0 2026-10-15   457030039  457429525          399487  399170            317  {'trades_landed': 21801882, 'tra...  {'against': 'getBlocks(first_slo...
```

### signatures/pumpdata-2026-10-15-signatures-00000-of-00007.parquet: 6,643,303 righe
- `slot` BIGINT
- `idx` INTEGER
- `signature` VARCHAR
- intervallo di `slot`: 457030039 → 457091742

```
        slot  idx                            signature
0  457030039  106  ViSVaV8irXnJ6VHZvzmHGPk2VZLGtpvz...
1  457030039  108  47qD5a8pYYHSVsBQUFMuxoqPBkMd8Xgk...
2  457030039  110  4pfp3YkBGyM75edSQcEAY6zsJqYsJL3B...
```
