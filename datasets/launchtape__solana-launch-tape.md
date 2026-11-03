# launchtape/solana-launch-tape

licenza: other · gated: False · file: 18 · dimensione totale: 0.27 GB

## File
- .gitattributes (0.0 MB)
- README.md (0.0 MB)
- data/MANIFEST.json (0.0 MB)
- data/SHA256SUMS (0.0 MB)
- data/curvetape-2026-10-13-1400-1600utc.jsonl.gz (79.4 MB)
- data/curvetape-2026-10-13-1400-1600utc.parquet (58.0 MB)
- data/gradholders-2026-10-14-0400-0600utc.jsonl.gz (0.4 MB)
- data/gradholders-2026-10-14-0400-0600utc.parquet (0.3 MB)
- data/gradtrades-2026-10-10-1400-1600utc.jsonl.gz (66.4 MB)
- data/gradtrades-2026-10-10-1400-1600utc.parquet (51.6 MB)
- data/launchmeta-2026-10-13-1400-1600utc.jsonl.gz (1.6 MB)
- data/launchmeta-2026-10-13-1400-1600utc.parquet (1.3 MB)
- data/meteora-pools-2026-10-10-1400-1600utc.jsonl.gz (1.6 MB)
- data/meteora-pools-2026-10-10-1400-1600utc.parquet (0.3 MB)
- data/padfeed-2026-10-10-1400-1600utc.jsonl.gz (0.3 MB)
- data/padfeed-2026-10-10-1400-1600utc.parquet (0.3 MB)
- data/pregrad-2026-10-10-1400-1600utc.jsonl.gz (2.1 MB)
- data/pregrad-2026-10-10-1400-1600utc.parquet (1.9 MB)

## Scheda

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

| type | key fields | meaning |
|---|---|---|
| `grad` | `pad` (dbc/ray), `mint`, `quote`, `b`/`q`, `px`, `supply`, `lagMs` | migration to the destination pool, mint facts |
| `px` | `pad`, `mint`, `b`, `q` | pool vault balances whenever they change (~6s) |
| `holders` | `pad`, `mint`, `top10`, `top20` | 20 largest token accounts at +60s and +5min |
| `qpx` | `usd` | US$ price of SOL and every quote mint, every 30s |

### meteora_pools columns

| field | meaning |
|---|---|
| `pool` | the DLMM pool address |
| `price` | quote per base token |
| `tvlUsd`, `vol24hUsd`, `fees24hUsd` | TVL, rolling 24h volume and fees, US$ |
| `vol24hDeltaUsd`, `feesMinUsd` | change since the pool's previous row |

### curvetape columns

| type | key fields | meaning |
|---|---|---|
| `create` | `mint`, `curve`, `creator`, `name`, `sym`, `uri`, `quote`, `vt`, `vs`, `rt`, `supply` | a new coin and its starting curve reserves (raw units); `quote` null = priced in SOL |
| `trade` | `slot`, `sig`, `i`, `bt`, `off`, `mint`, `side`, `wallet`, `tokens`, `sol`, `fee`, `cfee`, `capAfter`, `curveSol`, `vs`, `vt`, `ix` | one curve trade: SOL without fees (a buyer paid `sol + fee + cfee`), cap in SOL and reserves after it; `off` = slots since creation. Curves priced in another token carry `quote`, `qAmt`, `vq`, `rq`, `feeQ`, `cfeeQ` instead |
| `adopt` | `mint`, `why` | a coin followed from a trade, not its creation (`noCreate`, `revive`) |
| `complete` / `migrate` | `mint`, `pool`, `solAmount`, `mintAmount`, `poolMigrationFee` | the curve completed; the coin moved to PumpSwap |
| `end` | `mint`, `why`, `trades`, `buys`, `sells`, `vol`, `maxCap` | coin no longer followed (`graduated`, `idle`, `evicted`) with its totals |
| `tx` | `sig`, `role`, `txFee`, `prioFee`, `jitoTip`, `cuPrice`, `cuLimit`, `cuUsed` | fee picture of a creation or early-buy transaction |
| `gap` | `from`, `to`, `why`, `ms` | the live feed was off: trades in the window are missing (from 2026-10-14 repaired from whole blocks: rows with `src: "backfill"` and a `backfill` row) |

### launchmeta columns

| type | key fields | meaning |
|---|---|---|
| `meta` | `phase` (`create` / `grad`), `src`, `mint`, `creator`, `name`, `sym`, `uri`, `uriKind` | one row per coin at creation, another at graduation |
| `meta` | `json` (`name`, `symbol`, `description`, `image`, `website`, `showName`, `createdOn`, `hasTwitter`, `hasTelegram`), `jsonKeys`, `metaSha`, `metaBytes` | the metadata JSON's fields (social links reduced to true/false) and its sha256 |
| `meta` | `imgUrl`, `imgSha`, `imgBytes`, `imgType`, `cachedImg` | sha256 of the picture's bytes: the same picture = the same `imgSha` (pictures never stored) |
| `meta` | `err` | why a fetch failed; never guessed |
| `skip` | `mint`, `phase`, `why` | not fetched (`backlog` on a very busy hour) |

### gradholders columns

| type | key fields | meaning |
|---|---|---|
| `holders` | `mint`, `mark` (1 / 10 / 60), `tGrad`, `lagS`, `slot`, `supply`, `pool` | one snapshot per graduate and mark (minutes after graduation) |
| `holders` | `top[]` (`acct`, `owner`, `amt`, `pct`, `role`, `pda`) | the 20 largest token accounts, biggest first; `role` `pool` / `curve`, `pda` = program-owned |
| `holders` | `top10Pct`, `top20Pct`, `top10PctAll`, `poolPct`, `curvePct` | shares of supply, with and without the pool and curve |
| `holders` | `err` | the snapshot failed (`429`, `late`): no holder fields, never guessed |

## What you can do with it

From three days of the full feed (2,193 pump.fun graduates with prices in their 10-minute outcome, Oct 10-12 2026 UTC — bigger than this 2-hour sample, shown as a worked example of the kind of question `pregrad` answers). "Touched -80%" means `minDrop` <= -80 (vs the price 10 s after graduation). Of the 2,193, 38.1% touched -80%, 15.0% touched 2x and 5.3% touched 3x; 62.9% fell 40%+ from a high (`crashed`).

1. **Fast fills were not the rug signal people think.** Of 2,187 graduates that also have a `record` row, 1,384 filled their bonding curve within 5 seconds of creation ("instant"). They touched -80% about as often as the 803 slower fills (38.4% vs. 37.6%). The slower fills fell 40%+ from a high more often (85.6% vs. 50.0%), but also touched 2x three times as often (26.3% vs. 8.5%).
2. **Creator exit timing matters.** Of 1,913 graduates with creator-holding data, the 1,310 whose creator still held more than 5% of supply at graduation touched -80% 33.6% of the time; the 603 whose creator had already sold down to 5% or less, 47.4%.
3. **Big sells come fast, rarely from the creator.** Median time from graduation to the first big sell: 3.3 minutes (921 coins had one). The creator was that first big seller only 2.6% of the time.

(An earlier version of this card called `crashed` an 80%+ fall; it is a 40%+ fall from the high, corrected Oct 14.)

`pregrad`'s `record` and `outcome` splits carry everything needed to reproduce all three (`instant`, `creatorPctAtGrad`, `minDrop`/`maxGain`, `crashed`, `firstBigSell`).

## Load it

```python
from datasets import load_dataset

data_files = {
    "gradtrades": "data/gradtrades-2026-10-10-1400-1600utc.jsonl.gz",
    "pregrad": "data/pregrad-2026-10-10-1400-1600utc.jsonl.gz",
    "padfeed": "data/padfeed-2026-10-10-1400-1600utc.jsonl.gz",
    "meteora_pools": "data/meteora-pools-2026-10-10-1400-1600utc.jsonl.gz",
    "curvetape": "data/curvetape-2026-10-13-1400-1600utc.jsonl.gz",
    "launchmeta": "data/launchmeta-2026-10-13-1400-1600utc.jsonl.gz",
    "gradholders": "data/gradholders-2026-10-14-0400-0600utc.jsonl.gz",
}
ds = load_dataset("launchtape/solana-launch-tape", data_files=data_files)
# or, from a local clone:
ds = load_dataset("json", data_files=data_files)

print(ds["pregrad"][0])
```

The Parquet copies, with pandas or DuckDB:

```python
import pandas as pd
from huggingface_hub import hf_hub_download

path = hf_hub_download("launchtape/solana-launch-tape", "data/pregrad-2026-10-10-1400-1600utc.parquet", repo_type="dataset")
df = pd.read_parquet(path)
records = df[df["type"] == "record"]          # nested fields are dicts: records["creatorInfo"].str["funder"]
```

```sql
SELECT type, count(*) AS n
FROM read_parquet('hf://datasets/launchtape/solana-launch-tape/data/gradtrades-2026-10-10-1400-1600utc.parquet')
GROUP BY type ORDER BY n DESC;
```

Each split loads as a flat table of JSON objects; filter by `type` for the row kind you want (see the column tables above). Rows are plain JSON, so `pandas.read_json(path, lines=True)` and DuckDB's `read_json_auto(path)` work directly on the `.gz` files too.

## Getting full days

This sample is one 2-hour window. Full UTC-day files (JSON lines and Parquet) are on [launchtape.io](https://launchtape.io), paid in USDC or SOL on Solana (other chains on request).

**On sale now:** every UTC day from 2026-10-03 to 2026-10-13 (each dataset from its first full day, listed above), and one more day is added each day as it closes.

Three ways to buy:

- One day, $10 once: any UTC day you pick, with every graduate's first 30 minutes (`gradtrades`) and who was behind each launch (`pregrad`), plus the test prompt with that day's files filled in. No subscription.
- Starter, $10 a month: all 7 datasets, each new day's files by email as the UTC day closes, plus the last 7 days on file
- Full history, $49 a month: everything in Starter, plus every day on file back to October 3 2026

Prices are in USDC; paying in SOL is the same amount at the day's SOL price.

Questions: launchio48@gmail.com.

## License

Personal and research use only, inside your own team. No resale, no republishing, no redistribution of the files in whole or in part. Derived results (charts, papers, models, strategies) are yours to keep and use freely. Provided as is, no warranty — this is market data, not financial advice.

> Solana Launch Tape - data licence
>
> Copyright (c) 2026 Launch Tape.
>
> You may use the data files (including this free sample) for personal and research use, inside your own team.
> You may not resell, republish or redistribute the files, in whole or in part, or share them outside your own team.
> Derived results (charts, papers, models, strategies) are yours.
>
> The data is provided as is, with no warranty of any kind. It is market data, not financial advice.

