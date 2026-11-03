# Probe dei dataset storici gratuiti

## jocry/Pumpfun_Memecoin_Corpus / KNOWN_ISSUES.md

```
# Known Issues — PumpFun Launch-to-Graduation Corpus

This document is the authoritative, complete record of every data-quality
issue found in this corpus, how it was confirmed, its exact scale, and how
to handle it. Every number below was independently verified by direct
querying against the real data — nothing here is assumed or inherited
without a check.

**Read this before running any analysis.** Several items below are not
optional to handle correctly — skipping them will produce silently wrong
results, not an error.

---

## 1. Fixed issues (already corrected in `tokens.parquet`)

### 1.1 Mayhem-mode 2B-supply concentration bug

Mayhem Mode tokens mint 2,000,000,000 tokens, double the standard
1,000,000,000 — but concentration percentages (`initial_top1/5/10_pct`,
`dev_buy_pct`) were originally computed against a hardcoded 1B-supply
assumption for *every* token, mayhem or not. Proof of the bug: pre-fix,
`initial_top10_pct` reached values up to 200% for mayhem tokens — a
mathematically impossible percentage.

- **Scale:** 109,561 tokens (~12.7% of the corpus)
- **Fix applied:** `*_corrected` columns (`initial_top1_pct_corrected`,
  `initial_top5_pct_corrected`, `initial_top10_pct_corrected`,
  `dev_buy_pct_corrected`, `supply_bug_corrected`) — **use these, not the
  originals**, for any concentration analysis.

---

## 2. Unfixable, excluded issues

### 2.1 Bonding-curve-balance leak

A separate, smaller set of tokens show impossible concentration values
(median `top1_pct` 98.8%, up to 129.3% at top10) caused by a check meant to
exclude the bonding curve's own token balance from the "largest holder"
calculation failing to fire. Confirmed via correlation: `top1_pct`
correlates 0.71 with curve balance at first trade for affected tokens, vs.
-0.02 for unaffected tokens.

- **Scale:** 1,486 tokens, concentrated in a Jun 23-24 window tied to a
  burst of clone/factory-launch creator activity
- **Handling:** No correct value can be recovered — these rows are
  **flagged via `top10_pct_suspect`, and should be excluded**, not
  corrected or imputed.

---

## 3. Trade-level data issues (`trades.parquet`)

### 3.1 `sol_amount` internally inconsistent with `token_amount x price_sol`

For a genuine subset of trade rows, `sol_amount` does not match
`token_amount x price_sol` — in the worst cases, off by up to ~39,000,000x.
Root cause not fully diagnosed (a units/decimals mismatch somewhere in
ingestion is a plausible candidate, not confirmed).

- **Scale:** 1,136,321 rows (3.38% of 33,581,765)
- **Detection:** flag any row where
  `sol_amount / (token_amount * price_sol)` falls outside `[0.01, 100]`
- **Handling:** exclude from any SOL-denominated computation (volume, P&L,
  leaderboards). This filter is large enough to fully distort a naive
  top-wallet ranking if skipped — confirmed during this project's own
  research.

### 3.2 `sol_amount` / `price_sol` NULL (missing, not corrupted — distinct issue)

Separately from §3.1, a real share of trades have `sol_amount` and
`price_sol` as NULL rather than wrong — the price was simply never
captured for that trade.

- **Scale:** 2,360,061 rows (7.03%)
- **Pattern, confirmed via direct investigation:**
  - Heavily front-loaded in time — the corpus's first ~10 days carry a
    disproportionate share, **peaking at 33.6%/45.3% null on Jun 9-10**
    (the same 2-day window as the holder-count break, §5.1 — an
    interesting coincidence, not proven to share a root cause).
  - **Not** tied to trade direction (buy 7.3% vs. sell 6.7% — similar) or
    to a specific ingestion source.
  - **A whole-token phenomenon, not scattered per-trade gaps**: of ~20,300
    affected mints, over 99.8% are tokens where *every* trade is
    null-price, not a handful of trades within an otherwise-fine token.
  - Skews toward very early trades in a token's life (median ~20 min
    post-launch among null rows, vs. ~2.4h corpus-wide).
- **Handling:** flagged via `sol_price_missing` — kept deliberately separate
  from `sol_amount_suspect` (§3.1) so the two issues are never conflated.

### 3.3 Non-human wallet contamination

The address `BwWK17cbHxwWBKZkUYvzxLcNQ1YVyaFezduWbtm2de6s` is the Solana
System Program, confirmed via block explorer (Owner: System Program,
isOnCurve: FALSE) — not a market participant.

- **Scale:** 6,690,901 trade rows (19.92% of all trades), touching ~35% of
  all mints in the corpus
- **Handling:** **exclude this address from any wallet-derived feature** —
  unique wallet counts, wallet concentration, P&L leaderboards, wash
  -trading signals. Left in, it silently inflates unique-wallet counts by
  one and contaminates every wallet-concentration metric on a third of the
  corpus.

### 3.4 `curve_pct_depleted` / `curve_pct_depleted_eob` values outside [0,100]%

Both the per-trade (`trades.curve_pct_depleted`) and end-of-bucket
(`snapshots.curve_pct_depleted_eob`) versions of this field show values
outside the theoretically valid [0,100]% range.

- **Scale:** 1,215,810 trade rows (3.62%), 730,670 snapshot rows (2.71%)
- **Magnitude, confirmed via direct distribution check:** all bad values
  are capped at **exactly 110.0**, with 99.95%+ of them barely over the
  100% boundary (in the 100-200 bucket, essentially none above 200) — this
  looks like a bounded, designed overshoot mechanism, not open-ended
  corruption.
- **Mayhem-mode correlation:** real but weak (5.33% bad for mayhem tokens
  vs. 3.26% non-mayhem, ~1.6x) — too weak to be the primary mechanism; the
  known supply bug (§1.1) produces a much starker gap when it's the actual
  cause, confirmed via a synthetic test during this project's own research.
- **Temporal pattern (the dominant signal):** flat and low (0.02%-1.7%)
  for the entire corpus from Jun 5 through Jul 2, then **jumps sharply to
  8-11% starting Jul 4 and holds through the corpus end (Jul 14)**.
- **Jul 3 is a confirmed one-day gap** — zero recorded trades that day,
  due to a websocket collection outage. This explains the missing day
  itself. It does **not**, by itself, fully explain why the badness rate
  shifted upward and stayed elevated for the ten days following recovery —
  whether that reflects a config/version change made during outage
  recovery, a platform-side change coinciding with the same window, or
  something else has not been further diagnosed.
- **Handling:** treat as a fifth, distinct regime break (§5.5). Any model
  or analysis using curve-derived features (`curve_velocity`,
  `curve_accel`, `curve_pct_depleted_at_horizon`) should account for this
  shift, especially for the final third of the collection window.

---

## 4. `wallet_stats.parquet` reliability — read this before using this table at all

This table's own activity/volume columns cannot be trusted without
independent verification.

- **Systematic cross-check** (100,000 sampled wallets against a live
  recount from `trades.parquet`): only **37.7% exact match** on
  `total_trades` (59.7% exact match on `tokens_traded`). Mean ratio of
  (real / reported) trades = **15.9x**, median = **2x**, max = **16,055x**.
- **Root cause, confirmed via a targeted diagnostic distinguishing three
  competing hypotheses:** a **stale snapshot**, not a truncated
  aggregation window or a random sampling bug. The discrepancy ratio
  climbs monotonically from ~3.3x (wallets whose last real trade fell in
  the corpus's first week) to ~46.2x (wallets whose last real trade fell
  in the final week) — the exact signature of a table built once, early or
  mid-collection, and never regenerated.
- **What is affected:** `tokens_traded`, `total_trades`,
  `total_buy_volume_sol`, `total_sell_volume_sol`. **Do not use these four
  columns for any activity-volume analysis** — recompute directly from
  `trades.parquet` instead (see `quickstart.py` for the pattern).
- **What is not (confirmed) affected:** `first_seen_at`/`last_seen_at`
  timestamps were not part of the cross-check that found this issue — they
  may still be usable, though they were not independently verified either.
  Treat with appropriate caution, not blind trust .

---

## 4.5. outcome_label has no 'rug' value — using it as one will silently
return zero rows. Real values: dead, pump_dump, slow_bleed,
major_pump, minor_pump, sustained. quickstart.py's Section 5
(Gini-vs-rug metric) filters on outcome_label = 'rug' and is currently
broken as a result. Use rug_detected (boolean, in postgard_outcomes.parquet)
for a direct rug flag, or group dead/pump_dump/slow_bleed as "failed"
outcomes if you want the broader category. Fix pending.

## 4.55. migrations.parquet.pool_address contains synthetic sentinel values,
not real pool addresses, for ~25% of rows. synthetic_graduation_queue
(1,380 rows) marks graduations queued but not yet matched to a real pool;
backfilled_from_pumpswap_trade (69 rows) marks pool addresses
reconstructed after the fact from PumpSwap trade data rather than observed
directly at migration time. Filter these out if you need a real on-chain
pool address, or check pool_address NOT IN ('synthetic_graduation_queue',
'backfilled_from_pumpswap_trade') before joining downstream.

**Items 4.5 and 4.55 reported by M. Huzaifa (July 2026) — thank you.**

## 5. Regime breaks / non-stationarity

Five separate, independently-confirmed step-changes exist within the same
39-day corpus. Any cross-corpus time comparison, or any train/test split
whose boundary straddles one of these dates, should account for it.

### 5.1 Jun 9-10: `initial_holder_count` hard-cap change

Maximum value changed from exactly 54 to exactly 20 across a 2-day
transition, and never reverted. `initial_top1/5/10_pct` move in lockstep,
almost certainly because holder count is the denominator context for those
percentiles. Ruled out as a collection outage — hourly trade volume across
Jun 5-20 shows no gap at this boundary. Working hypothesis, not
independently confirmed: Solana's `getTokenLargestAccounts` RPC method is
natively capped at 20 accounts by protocol design, and this date marks a
change in (or loss of a workaround for) that native limit. **Left unfixed
in the data** — this is a real, permanent feature of the corpus, not
something to patch.

### 5.2 Jun 20-22: Mayhem Mode rollout

A new token type (2B supply, see §1.1) did not exist before this date and
ramped to ~28-30% of new launches within three weeks. A real product
change, not a bug — but means token-type composition is not stationary
across the collection window.

### 5.3 Jun 23-24: Second concentration-bug window

Overlaps with the bonding-curve-balance leak (§2.1) and a burst of
clone-launch creator activity in the same window.

### 5.4 Jun 24-25: Platform-wide silence-rate drop

The share of tokens with zero post-launch trading activity dropped from
~96.4% to ~88.9%. Checked and ruled out as a polling-cadence artifact
(sampling interval unchanged across the boundary) — most likely reflects
genuinely rising launch volume on the platform.

### 5.5 Jul 3-4: Websocket outage + `curve_pct_depleted` shift

See §3.4 for full detail. Jul 3 is a confirmed collection outage (zero
trades that day). The subsequent shift in `curve_pct_depleted` badness
rate (flat <2% before, 8-11% after, sustained through corpus end) is
temporally associated with this outage but not fully root-caused beyond
that.

---

## 6. Schema & naming gotchas

- **`outcome_label = 'dead'`** (a token that graduated, then died within
  24h) is a **completely different population** from a token that never
  graduated at all. Same word, two unrelated meanings across different
  parts of this corpus — do not conflate them.
- **`postgard_outcomes.parquet`'s real exported schema does not match**
  older collector source-code comments. Fields like `label_time_top10_pct`
  / `label_time_gini` are defined in source-level DDL but do **not** exist
  in the actual exported file. Always verify against a live `DESCRIBE`,
  never trust schema from code comments or documentation.
- **`postgard_snapshots.parquet` covers more distinct mints (5,701) than
  a typical filtered target population** (e.g. graduated, non-mayhem
  tokens is a smaller subset) — filter explicitly by your actual target
  population; don't assume table membership implies population membership.
- **`v_tokens_bonding_curve` / `v_sol_bonding_curve`** (in `trades.parquet`)
  are raw micro-token units, not human-scale token counts. A naive `/1e9`
  conversion produces values off by orders of magnitude (though
  correlations computed on the wrongly-scaled values remain valid, since
  it's a consistent scaling error). The correct relationship is
  `price_sol = (v_sol_bonding_curve / v_tokens_bonding_curve) / 1000`.

---

## 7. Modeling gotchas (not data bugs, but easy to leak on)

- **`entry_price_20s_usd` / `entry_price_30s_usd` / `entry_price_1m_usd`**
  are a near-perfect label proxy if used naively as predictive features.
  Null rate is ~0.14-0.18% for graduated tokens vs. ~93.5-93.6% for
  non-graduated tokens, with **no time-to-graduation gradient** — these
  fields are populated almost exclusively *because* a token graduated, not
  because of when. Suppressing the missingness indicator column is **not**
  sufficient to prevent leakage — tree-based models (XGBoost, LightGBM)
  learn native NaN split directions and will still effectively split on
  "is this field present." If building any graduation-prediction model on
  this corpus, exclude these three fields entirely rather than
  indicator-suppress them.
- **`first_trade_price_sol`** was checked with the same methodology and is
  **fine** — its null gap is small and roughly even across outcomes
  (27.9% graduated vs. 25.5% non-graduated), not the same near-total
  separator as the fields above.

---

## 8. What's confirmed clean (checked, not just assumed)

- **`market_cap_sol` / `price_sol`** in `trades.parquet` are correctly
  supply-invariant (derived from raw bonding-curve reserve ratios, not a
  percentage-of-total-supply calculation) — confirmed clean of both the
  mayhem-mode bug (§1.1) and the bonding-curve-balance leak (§2.1). Don't
  assume every supply-related field is contaminated just because nearby
  fields are — each was checked individually against its actual formula.

---

## 9. Tooling note (DuckDB users)

If querying this corpus with DuckDB, `USING SAMPLE N` (reservoir method)
has been observed to silently return 0 rows on filtered queries in some
environments, even though the identical query without the sample clause
returns thousands of rows — not root-caused against DuckDB internals, but
reproducible via direct A/B testing. `USING SAMPLE N` (bernoulli method)
throws an outright parser error when combined with a discrete row-count
target. Workaround that was verified to work correctly, including with
joins, at matching scale: use `setseed()` + `ORDER BY random()` + `LIMIT`
instead of `USING SAMPLE` entirely.

```

## jocry/Pumpfun_Memecoin_Corpus / quickstart.py

```
"""
================================================================================
PUMP.FUN MEMECOIN RESEARCH CORPUS — EXPANDED QUICKSTART & ANALYST SUITE
================================================================================

HOW TO DOWNLOAD THE DATASET & LOAD YOUR WORKSPACE:
--------------------------------------------------------------------------------
1. Using huggingface-cli (Recommended — downloads all files & shards in parallel):
   $ pip install huggingface_hub
   $ huggingface-cli download <your-hf-username>/<your-repo-name> --local-dir ./pumpfun_data

2. Using Git LFS:
   $ git lfs install
   $ git clone https://huggingface.co/datasets/<your-hf-username>/<your-repo-name> ./pumpfun_data

3. Programmatic zero-disk load in Python via DuckDB over HTTP:
   import duckdb
   df = duckdb.query('''
       SELECT * FROM 'https://huggingface.co/datasets/<username>/<repo>/resolve/main/tokens.parquet' 
       LIMIT 10
   ''').df()

EXPECTED DIRECTORY STRUCTURE (--data-dir ./pumpfun_data):
   pumpfun_data/
   ├── tokens.parquet              (798,430 rows | Master definitions & creator features)
   ├── snapshots.parquet           (26,934,769 rows | Pre-grad bonding curve time-series)
   ├── postgard_snapshots.parquet  (1,392,133 rows | Post-grad DEX liquidity snapshots)
   ├── postgard_outcomes.parquet   (5,669 rows | Post-grad outcome labels & performance)
   ├── wallet_stats.parquet        (1,016,374 rows | User wallet activity & volume profiles)
   ├── migrations.parquet          (5,701 rows | Raydium migration event logs)
   └── trades/                     (33,581,704 rows | Sharded execution ledger)
       ├── shard_01.parquet
       ├── ...
       └── shard_11.parquet

MANDATORY DATA-QUALITY FILTERS APPLIED IN THIS SUITE:
   1. System Program Exclusion: 
      user_wallet != 'BwWK17cbHxwWBKZkUYvzxLcNQ1YVyaFezduWbtm2de6s'
      (Excludes protocol system-level SOL transfer accounting records from trade logs).
   2. Suspect Concentration Row Exclusion: 
      WHERE NOT COALESCE(top10_pct_suspect, FALSE)
      (Excludes tokens with scraped top-10 concentration data anomalies).
   3. Trade-Derived Feature Reconstruction:
      Rebuilds time-windowed microstructure signals directly from trades/*.parquet 
      to bypass snapshot heartbeat-duplication artifacts (~90-95% carry-forward dupes).

USAGE:
   $ python quickstart.py --data-dir ./pumpfun_data
   $ python quickstart.py --data-dir /path/to/dataset --threads 8 --memory-limit 8GB
================================================================================
"""

import argparse
import os
import sys
import time
from typing import List, Tuple
import duckdb

# System Program Wallet Address (MUST be excluded from trade-level analysis)
SYSTEM_PROGRAM_WALLET = "BwWK17cbHxwWBKZkUYvzxLcNQ1YVyaFezduWbtm2de6s"


def print_banner(section_num: int, title: str) -> None:
    """Prints a standardized visual CLI section banner."""
    print("\n" + "=" * 80)
    print(f"=== SECTION {section_num}: {title.upper()} ===")
    print("=" * 80)


def configure_duckdb(threads: int = 4, memory_limit: str = "4GB") -> duckdb.DuckDBPyConnection:
    """
    Initializes an in-memory DuckDB connection optimized for high-throughput 
    Parquet scanning across multi-threaded CPU cores.
    """
    con = duckdb.connect(database=":memory:")
    con.execute(f"PRAGMA threads={threads};")
    con.execute(f"PRAGMA memory_limit='{memory_limit}';")
    con.execute("PRAGMA preserve_insertion_order=false;")
    return con


# ==============================================================================
# 1. CORPUS DISCOVERY & TABLE FOOTPRINT AUDIT
# ==============================================================================
def audit_corpus_structure(con: duckdb.DuckDBPyConnection, data_dir: str) -> None:
    """
    Validates physical presence and DuckDB readability of all 7 dataset components.
    Executes schema checks and scans row/column footprints, including multi-file 
    shards in `trades/*.parquet`.
    """
    print_banner(1, "Corpus Structure & File Inspection")

    table_configs: List[Tuple[str, str]] = [
        ("tokens", f"{data_dir}/tokens.parquet"),
        ("snapshots", f"{data_dir}/snapshots.parquet"),
        ("postgard_snapshots", f"{data_dir}/postgard_snapshots.parquet"),
        ("postgard_outcomes", f"{data_dir}/postgard_outcomes.parquet"),
        ("wallet_stats", f"{data_dir}/wallet_stats.parquet"),
        ("migrations", f"{data_dir}/migrations.parquet"),
        ("trades (sharded 11x)", f"{data_dir}/trades/*.parquet"),
    ]

    total_records = 0
    print(f"{'Table Name':<25} | {'Row Count':>15} | {'Col Count':>10} | {'Status'}")
    print("-" * 65)

    for name, path_glob in table_configs:
        try:
            # Query column structure and row counts using parallel Parquet readers
            col_query = f"SELECT COUNT(COLUMN_NAME) FROM (DESCRIBE SELECT * FROM read_parquet('{path_glob}'))"
            col_count = con.execute(col_query).fetchone()[0]

            row_query = f"SELECT COUNT(*) FROM read_parquet('{path_glob}')"
            row_count = con.execute(row_query).fetchone()[0]
            
            total_records += row_count
            print(f"{name:<25} | {row_count:>15,} | {col_count:>10} | VALID")
        except Exception as err:
            print(f"{name:<25} | {'N/A':>15} | {'N/A':>10} | ERROR ({err})")

    print("-" * 65)
    print(f"{'TOTAL INTEGRATED RECORDS':<25} | {total_records:>15,} |")
    print("\n[INFO] Sharded read check on trades/*.parquet verified across all Parquet shards.")


# ==============================================================================
# 2. DATA QUALITY AUDIT: TOKENS & CREATOR DIAGNOSTICS
# ==============================================================================
def audit_tokens_quality(con: duckdb.DuckDBPyConnection, data_dir: str) -> None:
    """
    Audits the master token definitions table (`tokens.parquet`):
    - Evaluates total token population and baseline graduation rate (~0.71%).
    - Quantifies suspect top-10 concentration rows that must be excluded.
    - Inspects structural missingness in initial_gini (requires >=3 holders to compute).
    """
    print_banner(2, "Tokens Table Quality & Graduation Base Rate")

    query = f"""
        SELECT 
            COUNT(*) AS total_tokens,
            COUNT(*) FILTER (WHERE COALESCE(top10_pct_suspect, FALSE)) AS n_suspect_rows,
            COUNT(*) FILTER (WHERE graduated_at IS NOT NULL) AS n_graduated,
            COUNT(*) FILTER (WHERE initial_gini IS NULL) AS n_null_gini,
            COUNT(*) FILTER (WHERE initial_gini IS NULL AND graduated_at IS NOT NULL) AS n_null_gini_graduated,
            ROUND(AVG(initial_holder_count), 2) AS avg_initial_holders
        FROM read_parquet('{data_dir}/tokens.parquet')
    """
    stats = con.execute(query).fetchdf()

    total = stats['total_tokens'][0]
    suspect = stats['n_suspect_rows'][0]
    graduated = stats['n_graduated'][0]
    null_gini = stats['n_null_gini'][0]
    null_gini_grad = stats['n_null_gini_graduated'][0]

    grad_rate = (graduated / total) * 100.0
    clean_total = total - suspect

    print(f"Total Tokens Evaluated:      {total:>10,}")
    print(f"Suspect Top10% Rows:        {suspect:>10,} (Excl. required for clean feature models)")
    print(f"Clean Tokens Population:    {clean_total:>10,}")
    print(f"Graduated Tokens:           {graduated:>10,} ({grad_rate:.2f}% base graduation rate)")
    print(f"Initial Gini NULLs:         {null_gini:>10,} ({100*null_gini/total:.1f}% overall — structural: <3 holders)")
    print(f"Initial Gini NULLs (Grad):  {null_gini_grad:>10,} (Only {null_gini_grad} graduated token missing Gini)")
    print(f"\n[DIAGNOSTIC] Initial Gini missingness is strictly structural (tokens with <3 holders at block zero).")


# ==============================================================================
# 3. DATA QUALITY AUDIT: TRADES & SYSTEM PROGRAM FILTERING
# ==============================================================================
def audit_trades_quality(con: duckdb.DuckDBPyConnection, data_dir: str) -> None:
    """
    Audits the execution ledger across all sharded Parquet files (`trades/*.parquet`):
    - Detects and quantifies System Program wallet records (must be filtered out).
    - Checks for price and volume integrity anomalies (NULL/zero amounts).
    - Measures overall distinct active trader addresses.
    """
    print_banner(3, "Trades Ledger Quality & System Wallet Filtering")

    query = f"""
        SELECT 
            COUNT(*) AS total_trades,
            COUNT(*) FILTER (WHERE user_wallet = '{SYSTEM_PROGRAM_WALLET}') AS sysprog_trades,
            COUNT(*) FILTER (WHERE price_sol IS NULL OR price_sol <= 0) AS invalid_price_trades,
            COUNT(*) FILTER (WHERE sol_amount IS NULL OR sol_amount <= 0) AS invalid_sol_trades,
            COUNT(DISTINCT user_wallet) AS unique_active_traders,
            COUNT(DISTINCT mint) AS unique_traded_mints
        FROM read_parquet('{data_dir}/trades/*.parquet')
    """
    df = con.execute(query).fetchdf()

    n_total = df['total_trades'][0]
    n_sys = df['sysprog_trades'][0]
    n_bad_price = df['invalid_price_trades'][0]
    n_bad_sol = df['invalid_sol_trades'][0]
    n_traders = df['unique_active_traders'][0]

    sys_pct = 100.0 * n_sys / n_total

    print(f"Total Granular Trades:       {n_total:>12,}")
    print(f"System Program Wallet Trades:{n_sys:>12,} ({sys_pct:.2f}% of corpus — EXCLUSION MANDATORY)")
    print(f"Unique Active Wallets:       {n_traders:>12,}")
    print(f"Invalid Price Rows (<=0/NULL):{n_bad_price:>11,}")
    print(f"Invalid SOL Amount Rows:     {n_bad_sol:>12,}")
    print(f"\n[FILTERING NOTE] Filtering out '{SYSTEM_PROGRAM_WALLET}' removes protocol accounting trades.")


# ==============================================================================
# 4. METRIC A: GRADUATION RATE BY CREATOR EXPERIENCE TIER
# ==============================================================================
def metric_creator_experience(con: duckdb.DuckDBPyConnection, data_dir: str) -> None:
    """
    Computes token graduation rate bucketed by developer track record (`creator_past_tokens`).
    Demonstrates that experienced creators achieve up to ~19x-25x higher graduation rates.
    """
    print_banner(4, "Metric A: Graduation Rate by Creator Experience Tier")

    query = f"""
        WITH tiered AS (
            SELECT
                mint,
                graduated_at IS NOT NULL AS is_graduated,
                CASE
                    WHEN COALESCE(creator_past_tokens, 0) = 0 THEN '01_first_time (0)'
                    WHEN creator_past_tokens <= 10 THEN '02_novice (1-10)'
                    WHEN creator_past_tokens <= 100 THEN '03_experienced (11-100)'
                    ELSE '04_serial_creator (100+)'
                END AS creator_tier
            FROM read_parquet('{data_dir}/tokens.parquet')
            WHERE NOT COALESCE(top10_pct_suspect, FALSE)
        )
        SELECT
            creator_tier AS "Creator Past Tokens Tier",
            COUNT(*) AS n_tokens,
            SUM(CASE WHEN is_graduated THEN 1 ELSE 0 END) AS n_graduated,
            ROUND(100.0 * SUM(CASE WHEN is_graduated THEN 1 ELSE 0 END) / COUNT(*), 3) AS graduation_rate_pct
        FROM tiered
        GROUP BY 1
        ORDER BY 1
    """
    res = con.execute(query).fetchdf()
    print(res.to_string(index=False))
    print("\n[KEY FINDING] Creators with previous project history display dramatically higher graduation odds.")


# ==============================================================================
# 5. METRIC B: HOLDER CONCENTRATION VS RUG RISK ANALYSIS
# ==============================================================================
def metric_concentration_vs_outcomes(con: duckdb.DuckDBPyConnection, data_dir: str) -> None:
    """
    Analyzes holder Gini index (`initial_gini`) vs post-graduation rug risk (`postgard_outcomes`).
    Filters out suspect concentration records for statistical validity.
    """
    print_banner(5, "Metric B: Holder Concentration (Gini) vs Post-Graduation Rug Risk")

    query = f"""
        WITH clean_tokens AS (
            SELECT 
                mint,
                initial_gini,
                initial_top10_pct
            FROM read_parquet('{data_dir}/tokens.parquet')
            WHERE NOT COALESCE(top10_pct_suspect, FALSE)
              AND initial_gini IS NOT NULL
        ),
        outcomes AS (
            SELECT 
                t.mint,
                t.initial_gini,
                o.outcome_label,
                o.rug_detected,
                CASE WHEN o.rug_detected THEN 1 ELSE 0 END AS is_rug
            FROM clean_tokens t
            INNER JOIN read_parquet('{data_dir}/postgard_outcomes.parquet') o ON t.mint = o.mint
        ),
        bucketed AS (
            SELECT 
                NTILE(5) OVER (ORDER BY initial_gini) AS gini_quintile,
                initial_gini,
                is_rug
            FROM outcomes
        )
        SELECT 
            gini_quintile AS "Gini Quintile",
            ROUND(MIN(initial_gini), 3) AS min_gini,
            ROUND(MAX(initial_gini), 3) AS max_gini,
            COUNT(*) AS n_graduated_tokens,
            SUM(is_rug) AS n_rugs,
            ROUND(100.0 * SUM(is_rug) / COUNT(*), 2) AS rug_rate_pct
        FROM bucketed
        GROUP BY 1
        ORDER BY 1
    """
    res = con.execute(query).fetchdf()
    print(res.to_string(index=False))
    print("\n[KEY FINDING] High holder inequality (Gini > 0.75) strongly predicts post-graduation rugging.")


# ==============================================================================
# 6. MICROSTRUCTURE: CLEAN TRADE-GRID FEATURE RECONSTRUCTION
# ==============================================================================
def compute_trade_microstructure_sample(con: duckdb.DuckDBPyConnection, data_dir: str) -> None:
    """
    Demonstrates building time-windowed trade flow metrics (T+3m, T+6m) directly
    from sharded `trades/*.parquet` files to bypass snapshot heartbeat duplicates.
    """
    print_banner(6, "Trade Microstructure Flow (Derived directly from trades/*.parquet)")

    query = f"""
        WITH filtered_trades AS (
            SELECT 
                mint,
                seconds_since_launch,
                is_buy,
                sol_amount
            FROM read_parquet('{data_dir}/trades/*.parquet')
            WHERE user_wallet != '{SYSTEM_PROGRAM_WALLET}'
              AND seconds_since_launch <= 360  -- First 6 minutes post-launch
        ),
        aggregated AS (
            SELECT 
                mint,
                COUNT(*) AS trades_first_6m,
                SUM(CASE WHEN seconds_since_launch <= 180 AND is_buy THEN sol_amount ELSE 0 END) AS buy_vol_3m,
                SUM(CASE WHEN seconds_since_launch <= 180 AND NOT is_buy THEN sol_amount ELSE 0 END) AS sell_vol_3m,
                SUM(CASE WHEN is_buy THEN sol_amount ELSE 0 END) AS buy_vol_6m,
                SUM(sol_amount) AS total_vol_6m
            FROM filtered_trades
            GROUP BY mint
        )
        SELECT 
            t.mint,
            t.symbol,
            a.trades_first_6m,
            ROUND(a.buy_vol_3m, 2) AS buy_vol_3m_sol,
            ROUND(a.sell_vol_3m, 2) AS sell_vol_3m_sol,
            ROUND(a.buy_vol_6m / NULLIF(a.total_vol_6m, 0), 3) AS buy_pressure_6m
        FROM aggregated a
        JOIN read_parquet('{data_dir}/tokens.parquet') t ON a.mint = t.mint
        WHERE NOT COALESCE(t.top10_pct_suspect, FALSE)
        ORDER BY a.total_vol_6m DESC
        LIMIT 5
    """
    res = con.execute(query).fetchdf()
    print(res.to_string(index=False))
    print("\n[METHODOLOGY] Constructing signals directly from trades avoids snapshot heartbeat duplication.")


# ==============================================================================
# 7. POST-GRADUATION DEX OUTCOME & LIQUIDITY ANALYSIS
# ==============================================================================
def analyze_postgrad_performance(con: duckdb.DuckDBPyConnection, data_dir: str) -> None:
    """
    Analyzes DEX survival classifications (`postgard_outcomes.parquet`) and liquidity 
    decay trajectories (`postgard_snapshots.parquet`).
    """
    print_banner(7, "Post-Graduation Outcomes & DEX Liquidity Retention")

    # Outcome Label Breakdown
    print("--> Categorical Survival Breakdown across Graduated Population:")
    query_outcomes = f"""
        SELECT 
            outcome_label AS "Outcome Label",
            COUNT(*) AS n_tokens,
            ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) AS pct_of_graduated,
            ROUND(AVG(price_change_24h_pct), 2) AS avg_24h_price_change_pct,
            SUM(CASE WHEN still_liquid_at_24h THEN 1 ELSE 0 END) AS liquid_at_24h_count
        FROM read_parquet('{data_dir}/postgard_outcomes.parquet')
        GROUP BY outcome_label
        ORDER BY n_tokens DESC
    """
    res_outcomes = con.execute(query_outcomes).fetchdf()
    print(res_outcomes.to_string(index=False))

    # Post-Grad Snapshots Liquidity Sample Check
    print("\n--> DEX Liquidity & Volume Time-Series Sample (postgard_snapshots.parquet):")
    query_snapshots = f"""
        SELECT 
            mint,
            seconds_since_graduation,
            ROUND(price_usd, 6) AS price_usd,
            ROUND(liquidity_usd, 2) AS liquidity_usd,
            ROUND(volume_1h, 2) AS vol_1h_usd,
            buy_pressure_1h
        FROM read_parquet('{data_dir}/postgard_snapshots.parquet')
        WHERE liquidity_usd IS NOT NULL
        ORDER BY snapshot_time DESC
        LIMIT 5
    """
    res_snapshots = con.execute(query_snapshots).fetchdf()
    print(res_snapshots.to_string(index=False))


# ==============================================================================
# 8. WALLET ANALYTICS & HIGH-FREQUENCY TRADER PROFILING
# ==============================================================================
def analyze_wallet_profiles(con: duckdb.DuckDBPyConnection, data_dir: str) -> None:
    """
    Profiles trader behaviors and volume distributions across 1.02M unique addresses 
    logged in `wallet_stats.parquet`.
    """
    print_banner(8, "Wallet Stats & High-Frequency Trader Distribution")

    query = f"""
        WITH wallet_tiers AS (
            SELECT 
                wallet,
                tokens_traded,
                graduated_tokens_traded,
                total_trades,
                total_buy_volume_sol + total_sell_volume_sol AS total_volume_sol,
                CASE 
                    WHEN total_trades >= 1000 THEN '01_bot_or_infra (1000+ trades)'
                    WHEN total_trades >= 100 THEN '02_heavy_trader (100-999)'
                    WHEN total_trades >= 10 THEN '03_regular_trader (10-99)'
                    ELSE '04_casual_trader (1-9)'
                END AS trader_tier
            FROM read_parquet('{data_dir}/wallet_stats.parquet')
        )
        SELECT 
            trader_tier AS "Trader Activity Tier",
            COUNT(*) AS n_wallets,
            ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) AS pct_wallets,
            ROUND(AVG(tokens_traded), 1) AS avg_tokens_traded,
            ROUND(SUM(total_volume_sol), 1) AS tier_total_volume_sol
        FROM wallet_tiers
        GROUP BY 1
        ORDER BY 1
    """
    res = con.execute(query).fetchdf()
    print(res.to_string(index=False))
    print("\n[INSIGHT] A small percentage of automated bot wallets drive a major share of execution frequency.")


# ==============================================================================
# 9. MIGRATION EVENT LOGS & RAYDIUM TIMING ANALYSIS
# ==============================================================================
def analyze_migrations_performance(con: duckdb.DuckDBPyConnection, data_dir: str) -> None:
    """
    Inspects Raydium migration timing patterns logged in `migrations.parquet`.
    Computes summary distribution statistics for bonding curve graduation speed.
    """
    print_banner(9, "Raydium Migration Event Timing & Velocity Distribution")

    query = f"""
        SELECT 
            COUNT(*) AS total_migrations,
            ROUND(AVG(seconds_to_graduation), 1) AS avg_seconds_to_grad,
            ROUND(MEDIAN(seconds_to_graduation), 1) AS median_seconds_to_grad,
            ROUND(QUANTILE_CONT(seconds_to_graduation, 0.10), 1) AS p10_seconds,
            ROUND(QUANTILE_CONT(seconds_to_graduation, 0.90), 1) AS p90_seconds,
            MIN(seconds_to_graduation) AS fastest_grad_seconds,
            MAX(seconds_to_graduation) AS slowest_grad_seconds
        FROM read_parquet('{data_dir}/migrations.parquet')
    """
    res = con.execute(query).fetchdf()
    print(res.to_string(index=False))
    print("\n[INSIGHT] Graduation speed ranges from hyper-fast sniped launches to multi-day gradual curves.")


# ==============================================================================
# 10. SUMMARY & PIPELINE DATA-QUALITY CHECKLIST
# ==============================================================================
def print_pipeline_summary() -> None:
    """Prints a checklist of required data quality rules before building models."""
    print_banner(10, "Summary & Data Quality Checklist for Machine Learning")

    checklist = [
        ("1. System Program Exclusion", "ALWAYS filter out user_wallet = 'BwWK17cbHxwWBKZkUYvzxLcNQ1YVyaFezduWbtm2de6s'"),
        ("2. Suspect Row Exclusion", "ALWAYS exclude rows where COALESCE(top10_pct_suspect, FALSE) is True"),
        ("3. Heartbeat Duplicate Prevention", "Rebuild time-series signals directly from trades/*.parquet shards"),
        ("4. Structural Missingness", "Treat initial_gini NULLs as structural (<3 holders), not random missingness"),
        ("5. Walk-Forward CV Splits", "Use time-based walk-forward splits to account for non-stationary base rates"),
    ]

    for item, rule in checklist:
        print(f"  [CHECK] {item:<32} -> {rule}")
    print("\nSee README.md for full model feature engineering guidelines and replication benchmarks.")


# ==============================================================================
# MAIN CLI DRIVER
# ==============================================================================
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Expanded Quickstart & Quality Audit Script for Pump.fun Memecoin Dataset"
    )
    parser.add_argument(
        "--data-dir", 
        required=True, 
        help="Path to root directory containing parquet files and trades/ subfolder"
    )
    parser.add_argument(
        "--threads", 
        type=int, 
        default=4, 
        help="Number of CPU threads for DuckDB engine (default: 4)"
    )
    parser.add_argument(
        "--memory-limit", 
        type=str, 
        default="4GB", 
        help="DuckDB memory ceiling, e.g. '4GB', '8GB' (default: 4GB)"
    )

    args = parser.parse_args()
    data_dir = args.data_dir.rstrip("/")

    # Directory existence check
    if not os.path.exists(data_dir):
        print(f"[ERROR] Directory '{data_dir}' does not exist. Please check --data-dir path.")
        sys.exit(1)

    t_start = time.time()
    print(f"Initializing DuckDB Engine (Threads: {args.threads}, Memory Limit: {args.memory_limit})...")
    con = configure_duckdb(threads=args.threads, memory_limit=args.memory_limit)

    # Run analytical sections sequentially
    audit_corpus_structure(con, data_dir)
    audit_tokens_quality(con, data_dir)
    audit_trades_quality(con, data_dir)
    metric_creator_experience(con, data_dir)
    metric_concentration_vs_outcomes(con, data_dir)
    compute_trade_microstructure_sample(con, data_dir)
    analyze_postgrad_performance(con, data_dir)
    analyze_wallet_profiles(con, data_dir)
    analyze_migrations_performance(con, data_dir)
    print_pipeline_summary()

    t_elapsed = time.time() - t_start
    print("\n" + "=" * 80)
    print(f"SUCCESS: ALL 10 ANALYTICAL SECTIONS COMPLETED IN {t_elapsed:.2f} SECONDS.")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
```

## loopholetape/pumpfun-launches / KNOWN_ISSUES.md

```
# Known issues of "pump.fun launches with outcomes" (loopholetape)

Release of 2026-11-03: 2,331,945 launches, 58 UTC days (2026-08-31 to 2026-10-27), in the subsets `launches_legacy` and `launches`, and 39,967 pools, config `graduation_pools`. Every number below was measured on the files of this release by script. KI-01 to KI-06 are the six issues in the API's own schema document (https://api.loopholetape.com/v1/datasets/schema/pumpfun_launches); KI-07 is the recorder restart of 2026-09-29, which is not in that document; KI-08 to KI-17 were found while building the first release. "Cause not established" means we measured it and did not trace it.

## KI-01 features_are_a_sample

Columns: `f10_*`, `f60_*`.

The early features exist where our shadow harness sampled the mint, and the sampling is not random: a launch with no early activity is less likely to be sampled. The `f60_*` columns exist on the mints that the harness's copy strategies touched.

In this release: a snapshot under 10 s of age (`f10_*`) exists for 1,838,307 rows (78.8%). There is none on 2026-08-31 and 2026-09-01, 22.7% on 2026-09-02, and 50.3% to 99.5% on each day from 2026-09-03. A snapshot between 10 and 60 s (`f60_*`) exists for 1,497,345 rows (64.2%). Some sampled rows have null fields: on 32,052 sampled rows (1.7% of the sampled ones) `f10_dev_share`, `f10_bundle_wallets`, `f10_rep_n`, `f10_rep_rug`, `f10_rep_grad` and `f10_n_buys` are null together, because the snapshot carries just `f10_insider_share`, `f10_rs` and `f10_age` (their ages are mostly 0.0 to 0.05 s); we did not trace why. `f10_rep_rug` and `f10_rep_grad` are also null on 509,516 sampled rows with a full snapshot, where the creator has no earlier resolved launch in our table. The selection matters: among classic launches of 2026-09-03 onward, those with a snapshot graduated at 2.86% and were rugged on 66.0% of the resolved ones; those without a snapshot graduated at 4.06% and were rugged on 43.0%.

What to do: treat a null as "not sampled", never as zero. A model trained on the sampled rows has a different base rate from the whole table; say so, or use the outcome columns alone.

## KI-02 decoder_seam_2026-09-27

Columns: `f10_n_buys`, `f10_bundle_wallets`, `peak_rs`, `rugged`, `rug_dt_s`.

Before 2026-09-27 00:18:34 UTC our capture did not decode two buy instructions (`buy_exact_sol_in` and Jupiter's `buy_exact_quote_in_v2`): about 48% of buy rows and 32% of the SOL entering curves were not booked (the recorder's own count). `f10_n_buys` and `f10_bundle_wallets` are undercounts before that time, and a peak reached through those buys is understated, so `rugged` misses some rugs before the seam. The schema document states that `graduated` is not affected; the label check in KI-09 is the evidence we have.

In this release: 859,208 rows (`launches_legacy`, days up to 2026-09-26) are before the seam and 1,472,117 rows (`launches`, from 2026-09-27 00:18:34 UTC) are after it; the first day of `launches`, 2026-09-27, also holds 620 rows launched before the fix (`decoder_complete` = 0), because a day file is placed by its date. The column `decoder_complete` marks the regime of every row (0 = before the seam). Measured on the API's day files around the seam:

| launch day | launches | f10_n_buys p90 | f10_bundle_wallets p90 | rugged share of resolved SOL launches | median migrate_dt_s of graduated classic launches (s) | in this release |
|---|---:|---:|---:|---:|---:|---|
| 2026-09-18 | 36,003 | 2 | 2 | 68.7% | 0.7 | yes |
| 2026-09-19 | 31,901 | 3 | 3 | 65.6% | 0.8 | yes |
| 2026-09-20 | 30,672 | 3 | 2 | 66.0% | 0.5 | yes |
| 2026-09-21 | 34,565 | 3 | 3 | 67.8% | 2.2 | yes |
| 2026-09-22 | 32,988 | 3 | 3 | 67.9% | 1.6 | yes |
| 2026-09-23 | 34,644 | 3 | 2 | 68.4% | 1.5 | yes |
| 2026-09-24 | 34,510 | 3 | 2 | 68.6% | 2.5 | yes |
| 2026-09-25 | 34,576 | 2 | 2 | 68.9% | 2.3 | yes |
| 2026-09-26 | 43,058 | 3 | 3 | 70.2% | 18.6 | yes |
| 2026-09-27 (seam 00:18:34Z) | 37,908 | 4 | 5 | 73.5% | 6.3 | yes |
| 2026-09-28 | 42,266 | 4 | 5 | 70.6% | 7.8 | yes |
| 2026-09-29 (restart 10:56:23Z) | 43,327 | 4 | 4 | 72.2% | 0.2 | yes |
| 2026-09-30 | 49,042 | 4 | 4 | 73.8% | 0.0 | yes |

In the table, the 90th percentile of `f10_n_buys` is 2 to 3 up to 2026-09-26 and 4 from 2026-09-27; of `f10_bundle_wallets` 2 to 3 before and 4 to 5 after. The rugged share of resolved SOL-quoted launches is 65.6% to 68.9% up to 2026-09-25 and 70.2% to 73.8% from 2026-09-26. Part of that rise can be the seam (rugs previously missed) and part the market; we cannot separate them. 2026-09-26 is before the seam and already at 70.2%.

What to do: split any model or statistic by `decoder_complete`. On rows with `decoder_complete` = 0 the counts are lower bounds and rug labels are slightly too low.

## KI-03 curves_quoted_in_other_assets

Columns: `quote_asset`, `quote_mint`, and every SOL-denominated column (`dev_buy_sol`, `graduated`, `rugged`, `rug_dt_s`, `peak_rs`, `terminal_rs`, `f10_rs`, `f60_rs`).

Not every pump.fun curve is quoted in SOL. Our launch table books reserves as SOL, so on a curve quoted in another asset the SOL columns would be quote units read as SOL; they are null here. `curve_complete` still says whether such a curve completed.

In this release: 375,157 rows (16.1%) are not SOL-quoted: USDC 39,624 (1.7%), tokenized stocks 63,783 (2.7%), other coins 271,750 (11.7%), over 4,688 quote mints; no PYUSD-quoted launch falls in these days. 4,640 of them (1.2%) completed on the chain. The share varies by day: 3.2% to 5.6% of the launches of 2026-08-31 to 2026-09-08 (USDC), 6.3% to 33.9% from 2026-09-09 on, when other assets joined. 31 rows have no curve read and no stream mark, so their quote is not established; they keep their SOL columns and may be non-SOL curves.

What to do: filter on `quote_asset == "sol"` for anything measured in SOL, and drop the 31 unknown rows.

## KI-04 mayhem_mode

Columns: `mayhem`, `curve_complete`, `migrate_dt_s`.

Mayhem-mode launches are an opt-in setting in which pump.fun's own agent may trade the coin. They are 27.0% of the rows of this release (18.8% to 38.4% by day). SOL-quoted mayhem launches graduate at 0.02% (classic: 3.10%) and were rugged on 88.6% of the resolved ones (classic: 61.1%). 17,038 of the 600,839 SOL-quoted mayhem launches (2.8%) are marked complete on the chain; 67 of them are labelled graduated and the other 16,971 completed far below 85 SOL (median `peak_rs` 1.01 SOL). 13,163 of the 17,038 have a pool sighting (`migrate_dt_s`, median 279 s after launch). A completion below the threshold is a close and not a graduation, so `graduated` stays 0 and `migrate_dt_s` records the pool sighting. 109 SOL-quoted mayhem launches are labelled graduated in all. The API's schema document gives about 2.5% for 2026-09-29.

What to do: separate mayhem rows before computing a graduation rate or training on outcomes.

## KI-05 late_outcomes

Columns: `graduated`, `rugged`, `peak_rs`, `terminal_rs`, `curve_complete`.

Outcomes settle late. The API rebuilds its newest three day files every night, and a few percent of the newest day's rows are unresolved. A day is added to this dataset when its date is 7 or more days before the publication date, so none of its files is inside that rebuild window.

In this release: from 2026-09-05 on, 26 to 581 SOL-quoted rows a day are still unresolved (0.12% to 1.31% of the day); the share is higher on the newest days (133 rows, 0.32%, on 2026-10-27). The first four days are a larger problem: KI-08.

What to do: nothing beyond KI-08; unresolved rows are null, not false.

## KI-06 coverage

Columns: all.

One recorder on one stream: a launch our capture did not see is not in the table, and a launch whose trades it missed has `peak_rs` 0. We ran no independent census of launches for this release. The project knows of no multi-hour gap in the capture since 2026-08-25; the gaps below are shorter.

In this release: the first launch is at 2026-08-31 04:03:25 UTC, so the 2026-08-31 file starts mid-day. No clock hour of the 1,388 hours has zero launches (median hour 1,607 launches, lowest 329 at 2026-09-12 06:00 UTC). Gaps between consecutive launches longer than 5 minutes:

- 2026-09-09 06:39Z to 07:08Z (28.9 min)
- 2026-09-09 07:08Z to 07:26Z (17.9 min)
- 2026-09-02 02:54Z to 03:04Z (9.5 min)
- 2026-10-16 03:00Z to 03:05Z (5.1 min)
- 2026-09-02 16:40Z to 16:45Z (5.1 min)

On 2026-09-09 the 10-minute bins from 06:40 to 07:30 UTC hold 0, 0, 2, 0 and 39 launches, against 115 to 177 in the hour before and 95 to 188 in the hour after, so several hundred launches are missing in that window. There are 55 gaps over 60 s and 11 over 120 s in all.

What to do: count against an independent source before using the table as a census; do not read the gap windows as quiet markets.

## KI-07 recorder_restart_seam_2026-09-29

Columns: `migrate_dt_s`; in `graduation_pools`: `open_t`, `drain70_t`, `collapsed_t` (they are measured from `open_t`).

On 2026-09-29 at 10:56:23 UTC the recorder was restarted with a decoder for the `migrate_v2` instruction. A migration record is now written at the migration transaction itself (a migrate_v2 call that did not create the pool is not counted). Before the restart the record appeared at the first PumpSwap swap seen for the mint. `migrate_dt_s` ("seconds from launch to the first migration or pool sighting") and `open_t` therefore point to different events before and after that instant.

In this release: 1,376,879 rows launched on or after the restart are in `launches` (from 2026-09-29): for them `migrate_dt_s` points to the migration transaction, for the other rows to the first pool sighting, which is later than the migration transaction by an amount we have not measured; a launch shortly before the restart can also graduate after it, and no column marks that. The median `migrate_dt_s` of graduated classic launches, by launch day, is in the table under KI-02 (next to last column): 0.5 to 2.5 s up to 2026-09-25, then 18.6 s on 2026-09-26, 6.3 s on 2026-09-27, 7.8 s on 2026-09-28, and 0.2 s and 0.0 s on 2026-09-29 and 2026-09-30. The shift starts on 2026-09-26, three days before the restart; we did not establish its cause.

What to do: do not compare `migrate_dt_s` or pool timings across 2026-09-29 10:56:23 UTC; no column marks this seam, so split on `t0` (and on `open_t` for the pools).

## KI-08 unresolved_outcomes

Columns: `rugged`, `rug_dt_s`, `dev_first_sell_dt_s`, `peak_rs`, `terminal_rs`.

The columns are written when the recorder closes a curve's path (a migrated curve quiet for 10 minutes, or a curve under 1 SOL quiet for an hour). A path that was never closed keeps null in all of them.

In this release: 60,345 SOL-quoted rows (3.1%) are unresolved. 44,866 of them (74.3%) are launches of 2026-09-01 to 2026-09-04: 7,622 rows on 2026-09-01 (21.8% of that day's SOL-quoted launches), 19,923 on 2026-09-02 (63.9%), 13,710 on 2026-09-03 (43.9%) and 3,611 on 2026-09-04 (12.8%). 2026-08-31 has none. 2,569 rows (5.9% of the day's SOL-quoted launches) are launches of 2026-09-30: nearly all of them launches of 00:00 to 02:59 UTC (72% of the 01:00 hour's SOL-quoted launches, 46% of the 02:00 hour's); the process that closes curve paths was restarted at 02:26:30 UTC that day, and curves open across the restart were never closed. 3,121 rows (6.6% of the day's SOL-quoted launches) are launches of 2026-10-06: nearly all of them launches of 00:00 to 03:46 UTC (57% of the 02:00 hour's SOL-quoted launches, 83% of the 03:00 hour's); the process that closes curve paths was restarted at 03:46:40 UTC that day, and curves open across the restart were never closed. 2,699 rows (7.9% of the day's SOL-quoted launches) are launches of 2026-10-23: nearly all of them launches of 15:00 to 16:45 UTC (54% of the 15:00 hour's SOL-quoted launches, 76% of the 16:00 hour's); the process that closes curve paths was restarted at 16:45:28 UTC that day, and curves open across the restart were never closed. The rest is the small daily residual of KI-05. Among the unresolved rows 498 are labelled graduated and 1,106 have `curve_complete` = 1, so null does not mean "did not graduate". We did not establish the cause.

What to do: exclude 2026-09-01 to 2026-09-04 and 2026-09-30 and 2026-10-06 and 2026-10-23 from any analysis that needs `rugged`, `peak_rs` or `terminal_rs`, or model them as missing not at random. Never impute "not rugged".

## KI-09 graduated_label_recall

Columns: `graduated`, `curve_complete`.

The `graduated` label (the curve completed, reaching 85 SOL of real reserve, or a migration was seen after it reached 80 SOL) is checked against the chain's `complete` flag on classic launches (SOL-quoted, not mayhem, curve account read). Over this release: 1,355,895 launches, 42,480 complete on the chain, 41,990 labelled graduated, 41,921 both: recall 98.68%, precision 99.84%. The live schema document reports recall 98.71% and precision 99.81% over 64 days. By launch day:

| launch day | classic launches with a curve read | chain says complete | labelled graduated | recall |
|---|---:|---:|---:|---:|
| 2026-08-31 | 23,596 | 657 | 648 | 98.63% |
| 2026-09-01 | 27,462 | 776 | 756 | 97.42% |
| 2026-09-02 | 23,017 | 650 | 582 | 89.54% |
| 2026-09-03 | 21,615 | 673 | 638 | 94.80% |
| 2026-09-04 | 17,979 | 648 | 630 | 97.22% |
| 2026-09-05 | 12,744 | 612 | 605 | 98.86% |
| 2026-09-06 | 14,668 | 645 | 638 | 98.91% |
| 2026-09-07 | 20,028 | 797 | 789 | 99.00% |
| 2026-09-08 | 21,052 | 726 | 719 | 99.04% |
| 2026-09-09 | 20,436 | 761 | 751 | 98.69% |
| 2026-09-10 | 18,180 | 688 | 683 | 99.27% |
| 2026-09-11 | 15,552 | 612 | 609 | 99.51% |
| 2026-09-12 | 13,644 | 621 | 619 | 99.68% |
| 2026-09-13 | 14,306 | 608 | 604 | 99.34% |
| 2026-09-14 | 15,355 | 659 | 652 | 98.79% |
| 2026-09-15 | 20,175 | 721 | 705 | 97.78% |
| 2026-09-16 | 20,303 | 765 | 759 | 99.22% |
| 2026-09-17 | 23,440 | 810 | 802 | 99.01% |
| 2026-09-18 | 21,728 | 789 | 785 | 99.49% |
| 2026-09-19 | 20,236 | 762 | 755 | 99.08% |
| 2026-09-20 | 19,079 | 815 | 810 | 99.39% |
| 2026-09-21 | 21,711 | 789 | 785 | 99.49% |
| 2026-09-22 | 20,960 | 821 | 813 | 99.03% |
| 2026-09-23 | 21,489 | 781 | 777 | 99.49% |
| 2026-09-24 | 21,091 | 813 | 812 | 99.63% |
| 2026-09-25 | 20,944 | 758 | 748 | 98.68% |
| 2026-09-26 | 30,962 | 842 | 824 | 97.86% |
| 2026-09-27 | 24,528 | 727 | 723 | 99.45% |
| 2026-09-28 | 27,914 | 906 | 903 | 99.67% |
| 2026-09-29 | 26,946 | 827 | 816 | 98.55% |
| 2026-09-30 | 29,206 | 930 | 917 | 98.60% |
| 2026-10-01 | 30,781 | 981 | 973 | 99.18% |
| 2026-10-02 | 29,836 | 928 | 920 | 99.14% |
| 2026-10-03 | 35,245 | 955 | 943 | 98.74% |
| 2026-10-04 | 35,029 | 957 | 946 | 98.85% |
| 2026-10-05 | 35,399 | 831 | 811 | 97.59% |
| 2026-10-06 | 34,836 | 907 | 895 | 98.68% |
| 2026-10-07 | 33,332 | 900 | 896 | 99.44% |
| 2026-10-08 | 33,042 | 865 | 858 | 99.08% |
| 2026-10-09 | 28,624 | 828 | 822 | 98.67% |
| 2026-10-10 | 27,426 | 712 | 705 | 98.60% |
| 2026-10-11 | 24,229 | 664 | 657 | 98.04% |
| 2026-10-12 | 29,334 | 785 | 785 | 99.49% |
| 2026-10-13 | 24,212 | 762 | 759 | 99.08% |
| 2026-10-14 | 22,461 | 705 | 702 | 98.87% |
| 2026-10-15 | 22,982 | 619 | 616 | 99.03% |
| 2026-10-16 | 23,525 | 636 | 633 | 99.06% |
| 2026-10-17 | 22,179 | 614 | 611 | 99.51% |
| 2026-10-18 | 22,056 | 550 | 551 | 98.91% |
| 2026-10-19 | 23,986 | 580 | 578 | 99.14% |
| 2026-10-20 | 23,381 | 576 | 575 | 99.13% |
| 2026-10-21 | 21,910 | 594 | 583 | 97.81% |
| 2026-10-22 | 20,087 | 608 | 604 | 98.85% |
| 2026-10-23 | 20,088 | 681 | 666 | 97.50% |
| 2026-10-24 | 17,682 | 582 | 583 | 99.66% |
| 2026-10-25 | 16,409 | 495 | 494 | 99.60% |
| 2026-10-26 | 21,615 | 609 | 605 | 99.01% |
| 2026-10-27 | 25,863 | 567 | 562 | 98.59% |

Recall is below 98.5% on 2026-09-01 (97.4%), 2026-09-02 (89.5%), 2026-09-03 (94.8%), 2026-09-04 (97.2%), 2026-09-15 (97.8%), 2026-09-26 (97.9%), 2026-10-05 (97.6%), 2026-10-11 (98.0%), 2026-10-21 (97.8%), 2026-10-23 (97.5%); every other day is 98.5% or higher. 2026-09-01, 2026-09-02, 2026-09-03, 2026-09-04, 2026-10-23 are also days of KI-08; 2026-09-15, 2026-09-26, 2026-10-05, 2026-10-11, 2026-10-21 are not. We did not establish the cause.

What to do: for classic launches use `curve_complete` as a cross-check, or as the label when you need recall on the first days. `curve_complete` is read on 2026-09-30 (KI-15).

## KI-10 legacy_curve_layout

Columns: `holder_reward`, `creator_fee_bps`.

The values come from the curve account. Older accounts are shorter and do not contain these fields, so the recorder reads null where the layout does not reach them: accounts of 115 bytes carry neither field (144,564 launches), accounts of 124 bytes carry the fee but not the holder-reward flag (41,260 launches). In this release: `holder_reward` is null on 185,824 rows (8.0%), all of them launches up to 2026-09-12 (on 2026-08-31 51.7% of the rows); `creator_fee_bps` is null on 144,564 rows (6.2%), launches up to 2026-09-09. Both are also null on the 58 rows whose curve account was not read. Where present, `holder_reward` = 1 on 284,403 rows (13.3% of the non-null) and `creator_fee_bps` is 0 on 1,945,017 rows (88.9% of the non-null; 300, 100, 30 and 200 are the next most common values).

What to do: treat null as "the account has no such field", not as 0. For these columns use launches from 2026-09-13 (`holder_reward`) and 2026-09-10 (`creator_fee_bps`) on.

## KI-11 negative_intervals

Columns: `rug_dt_s`, `migrate_dt_s`, `dev_first_sell_dt_s`, `f10_age`.

12 rows have a negative interval: `rug_dt_s` (5 rows, as low as -138 s), `migrate_dt_s` (1, -69 s), `dev_first_sell_dt_s` (4, -138 s), `f10_age` (8, -161 s). All fall on 2026-09-09: 11 of them are launches between 13:54:53 and 13:56:26 UTC and one at 14:55:17 UTC. Events for these mints carry times earlier than the `t0` the table holds: either the launch time was recorded late or the event times are early. We did not establish which.

What to do: drop these rows from timing analyses.

## KI-12 peak_above_curve_limit

Column: `peak_rs`.

A curve stops at about 85 SOL of real reserve. 5967 rows have `peak_rs` above 85.1 SOL (2989 above 86, maximum 99.57); a curve cannot hold that, so these peaks are measurement errors of unknown cause.

What to do: clip at 85.1 or drop.

## KI-13 labels_are_not_exclusive

Columns: `graduated`, `rugged`.

The DEV DUMP branch of the rug rule is judged inside the first 300 s of the launch, so a launch can be rugged and still graduate later. In this release 4,375 of the 42,100 graduated launches (10.4%) are also rugged. 115 graduated launches have a null `migrate_dt_s` (no migration or pool sighting was recorded for them).

Since 2026-10-01 two columns make this explicit: `rugged_not_graduated` (1 exactly for the rugged launches that did not graduate) and `rug_branch_inferred` (`drain` on 450,493 of the 1,320,512 rugged rows, `dev_dump_or_recovered` on 870,019: most rugs are creator dumps on small curves, not drained pools). The branch is inferred from the stored terminal state, because the launch table keeps the flag without its branch.

What to do: do not use `rugged` as the opposite of `graduated`; decide which one your question needs, and read `rug_branch_inferred` before calling a rug a drained pool.

## KI-14 creator_text_is_untrusted

Columns: `name`, `symbol`, `uri`.

These fields are text that token creators wrote on-chain. We did not filter or review them, apart from the e-mail addresses removed in KI-17: expect offensive language, advertising and links to scams. In this release: 143 empty names and 162 empty symbols; control characters in 8 names and 6 symbols; line breaks in 725 names and 449 symbols; non-ASCII characters in 55,010 names (2.4%) and 32,509 symbols; a link (http, www or t.me) inside 138 names and 50 symbols; `uri` null on 5,963 rows (0.3%) and empty on 551, otherwise up to 200 characters (schemes: https 2,312,874, ipfs 10,015, http 2,331, data 70, none recognised 691). At least 26 names read as instructions to an AI assistant (found with a simple pattern, so there may be more); for example one of them begins with "IGNORE ALL". The fields also carry third-party identifiers that the creators published themselves: @handles in 709 names and 468 symbols, and an x.com or twitter.com link in 37 names (simple patterns, so the counts are lower bounds); these are kept. 14 names were an e-mail address; they are replaced by `[e-mail removed]` in this copy (KI-17).

What to do: never pass these fields to a language model as instructions or inside a prompt without delimiting them as data; filter or review them and escape them before display; do not fetch `uri` without sandboxing.

## KI-15 curve_account_read_on_2026-09-30

Columns: `curve_complete`, `mayhem` (where the account was read), `quote_asset`, `quote_mint`, `holder_reward`, `creator_fee_bps`, `curve_read_at`.

The curve accounts were read between 2026-09-30 15:07:29 UTC and 2026-10-31 06:51:49 UTC (each row carries its own read time, `curve_read_at`), so these columns describe the state at the read, not at launch. The quote asset, the layout and the mayhem flag do not change after launch; `complete` can change from 0 to 1 later for a curve that was still open at the read. Every launch of this release was at least 3 days old at the read, which leaves few such curves; we have not counted them. 58 rows were not read.

What to do: use `curve_read_at` when you need the time of the read.

## KI-16 two_files_rewritten

The day files of 2026-08-31 and 2026-09-01 store the all-null early-feature columns as the arrow `null` type in the API's copies, which the Hugging Face loader cannot merge with the float columns of the other days. The files in this repository were rewritten with those columns as float64; every value is the same (checked column by column against the API's files). Their sha256 differs from the API's for these two files. The day files of KI-17 differ from the API's too; the other 48 day files are byte for byte the API's.

What to do: nothing.

## KI-17 email_addresses_removed

Column: `name`.

14 `name` values were nothing but an e-mail address. In this copy each of them is replaced by `[e-mail removed]`. This is the one edit made to creator-written text: every other value of these rows, and every other row, is as in the API's day files. The rows (mint, launch day):

- `5P31ydUZQhitm7imucSA2nKgzfFnpQ92pAxWNYLDpump` (launched 2026-09-03)
- `4YzKoZivG5jc2gDLWAS6CHCXiMj1EN3sViUonhaNpump` (launched 2026-09-03)
- `q8n6JSjFBhczgfgH3aw8LRTLuWhxmHX5FHhsKKUpump` (launched 2026-09-05)
- `98EE8oTFxbZCncJEgS5oAudQ7t7wawnq6VJvXhhWpump` (launched 2026-09-05)
- `2Gx3KNFRy3UxdrLSdKQ91hznYz3t9EZUaFJXGrbSpump` (launched 2026-09-05)
- `nEvRFGEdvVWh5vHMXZnZz3RAoorF9kYfNwSJkKSpump` (launched 2026-09-24)
- `9q9je5Vht4QYXVWG2BL8bMNqVtYw2J7itzaig5CKpump` (launched 2026-09-25)
- `7Q6KhiRndufhsbqrc26pGKZXAuqYpKwuLg6pdCiq2JK1` (launched 2026-10-06)
- `FZExt6z7mrDe6tGyZxYJnBejJLkE1iiM9qwnoNKipump` (launched 2026-10-09)
- `Ai1jAKWa9RsajmBQf1wRvNxgxShApN8kJckDMbQzpump` (launched 2026-10-09)
- `DQP4YLSNE9JbqbRcDmDt2LXseBErJfjUgdcpRzw5pump` (launched 2026-10-11)
- `3QqgTGL8AHwRwWABjcXjC2JBwM5obCjhi3XonWgTpump` (launched 2026-10-11)
- `tdapujTHbeVCcNt41QavkgFPEq3LwDvkFdSaexTpump` (launched 2026-10-23)
- `7bpBvokvB86LG9Ws9QCVvLeJrTcuwGpnTzvgyhjmsCCS` (launched 2026-10-23)

The sha256 of the day files 2026-09-03 (2 rows), 2026-09-05 (3 rows), 2026-09-24 (1 row), 2026-09-25 (1 row), 2026-10-06 (1 row), 2026-10-09 (2 rows), 2026-10-11 (2 rows) and 2026-10-23 (2 rows) therefore differs from the API's files; the API's files and the chain keep the original text, so a join by mint with the API's data shows these 14 names as different. The addresses were found with a standard e-mail pattern (`name@domain.tld`); obfuscated forms such as "name at domain dot com" are not caught. `symbol` and `uri` hold no e-mail address in this release.

What to do: nothing; read `[e-mail removed]` as a missing name.

## KI-18 multi_hop_seam_2026-10-08

Columns: `f10_n_buys`, `f10_bundle_wallets`, `f10_insider_share`, `f10_dev_share`, `dev_share`, `dev_buy_sol`.

pump.fun and PumpSwap were redeployed on 2026-10-08 at 16:20 UTC with a multi-hop route: one transaction can trade from one coin to another through a pool and a bonding curve, and the curve leg arrives as a new instruction (`multi_hop_curve_swap`). The recorder did not read it until it was relaunched with a decoder on 2026-10-09 at 16:51:21 UTC. In that window about 2.7% of landed curve trades (142,938 in the 24 hours to 2026-10-09 15:55 UTC, carrying 2,147 SOL) were not booked as trades, so the wallet-level columns of launches in the window undercount buyers and bundles; the reserve path and the outcome labels come from the curve account itself and are unaffected. The pool legs of those routes were not recorded either, which touches `graduation_pools` rows whose pools were open in the window.

What to do: for launches between 2026-10-08 16:20 and 2026-10-09 16:51 UTC, read the wallet-level features as lower bounds, or exclude the window from any study of bundles or insider shares. No column marks the window; split on `t0`.

## graduation_pools

- P-1 coverage window: the recorder's store begins at 2026-09-23 11:10:21 UTC, so pools of earlier graduations have no row, and 2026-09-23 is a partial day (599 pools on 2026-09-23 against 1,085 on 2026-09-24). A pool opened but not followed for its 30 minutes would show `complete` = 0; every row here is 1.
- P-2 `open_reserve_lam` is the SOL reserve after the first trade the recorder saw inside the 30 minutes, not at the migration; `reserve_30m_lam` is the reserve after the last trade inside the window, not a snapshot at minute 30. `price_ratio_30m` is the price at that last trade over the price at the first trade. 12,412 pools opened with under 50 SOL and 342 have fewer than 5 trades; the full-pool filter drops them, and their price ratios are noisy.
- P-3 `pool` is null on 399 rows (1.0%): the migration record had no pool address. We did not establish why.
- P-4 `open_t` changes meaning on 2026-09-29 at 10:56:23 UTC (KI-07). This release ends 2026-10-27.
- P-5 `drain70_t` is set when the reserve first stands at or below 70% of its own running peak, which happens in 21,756 of the 27,096 full pools (80.3%): it is a fact about the reserve path, not a signal. The project's own look at the relation between that flag and later collapse used nine cells and is not validated; do not read it as a forecast.

## Notes for modelling

- The two subsets are two recorder regimes. Use `launches` (decoder complete) for buy-derived features and the inputs of the rug rule; use either subset for launch counts, creators, outcomes and the graduation label; do not pool them without `decoder_complete`.
- Split by time, never at random. There are 521,600 creators; the largest has 15,470 launches, the top 100 creators launched 13.1% of all rows, and 407,697 creators launched once.
- Know which columns are outcomes. Known at or just after launch: `creator`, `t0`, `name`, `symbol`, `uri`, `mayhem`, `quote_asset`, `quote_mint`, `holder_reward`, `creator_fee_bps`, `dev_buy_sol`, `dev_share`. Early features, with their age given: `f10_*`, `f60_*`. Outcomes and later reads, never features: `graduated`, `migrate_dt_s`, `rugged`, `rug_dt_s`, `dev_first_sell_dt_s`, `peak_rs`, `terminal_rs`, `curve_complete`, `curve_read_at`.
- Pick the label for your question: `graduated`, `curve_complete`, `rugged`, `rug_dt_s <= 300` answer different questions (KI-04, KI-09, KI-13).
- Rows with features and rows without them are different populations (KI-01); report both.
- Run the checks of KI-08 and KI-11 before any timing or rug-rate result on the first days of September.

```

## loopholetape/pumpfun-launches / quickstart.py

```
#!/usr/bin/env python3
"""Offline quickstart for "pump.fun launches with outcomes" (loopholetape). Reads the parquet files in this folder; no network. Needs pandas and pyarrow.

    python quickstart.py                  # the folder that holds this script
    python quickstart.py /path/to/folder

The launches come in two subsets by decoder regime: `launches` (days from 2026-09-27, recorded with the complete decoder) and `launches_legacy` (days up to
2026-09-26, before the decoder fix). For each subset that has files it prints the rows, the days and the decoder_complete counts, then the launches by kind
(what the curve is quoted in, mayhem mode) with the graduation and rug shares; at the end the share of graduation pools that lost 90% of their price
within 30 minutes. Definitions are in README.md, the defects of the data in KNOWN_ISSUES.md.
"""
import glob
import os
import sys

import numpy as np
import pandas as pd

root = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
SUBSETS = (("launches", "decoder complete, days from 2026-09-27"), ("launches_legacy", "recorded before the decoder fix, days up to 2026-09-26"))


def load(subset):
    files = sorted(glob.glob(os.path.join(root, "data", subset, "*.parquet")))
    if not files:
        return None
    frames = []
    for f in files:
        frame = pd.read_parquet(f)
        frame["day"] = os.path.basename(f)[:10]
        frames.append(frame)
    df = pd.concat(frames, ignore_index=True)
    for col in ("mayhem", "graduated", "rugged", "curve_complete", "decoder_complete"):
        df[col] = df[col].astype("float64")        # 0/1 flags with nulls become floats, so sums and means skip the nulls
    return df


shown = 0
for name, note in SUBSETS:
    df = load(name)
    if df is None:
        print(f"{name}: no files in this release yet ({note})\n")
        continue
    shown += 1
    complete = int(df["decoder_complete"].sum())
    print(f"{name}: {len(df):,} rows, {df['day'].nunique()} UTC days, {df['day'].min()} to {df['day'].max()}; "
          f"decoder_complete = 1 on {complete:,} rows, 0 on {len(df) - complete:,}")
    # launch kind: what the curve is quoted in, then mayhem mode
    kind = np.select([df["quote_asset"].isna(), df["quote_asset"] != "sol", df["mayhem"] == 1],
                     ["quote unknown", "not SOL-quoted", "mayhem (SOL)"], default="classic (SOL)")
    print(f"\n{'kind':<16}{'rows':>10}{'share':>8}{'graduated':>11}{'graduation rate':>17}{'rugged (of resolved)':>22}")
    for label in ("classic (SOL)", "mayhem (SOL)", "not SOL-quoted", "quote unknown"):
        g = df[kind == label]
        if g.empty:
            continue
        labelled = g["graduated"].notna().sum()        # graduated and rugged are null on a curve not quoted in SOL
        resolved = g["rugged"].notna().sum()
        grad = f"{g['graduated'].mean():.2%}" if labelled else "n/a"
        rug = f"{g['rugged'].mean():.1%}" if resolved else "n/a"
        print(f"{label:<16}{len(g):>10,}{len(g) / len(df):>8.1%}{int(g['graduated'].sum()):>11,}{grad:>17}{rug:>22}")
    print(f"graduation rate over all rows, a null counting as not graduated: {df['graduated'].fillna(0).sum() / len(df):.2%}\n")
if not shown:
    sys.exit("no launch files under data/launches or data/launches_legacy")

# graduation pools: the first 30 minutes of the PumpSwap pools that graduations opened
pools = pd.read_parquet(os.path.join(root, "data", "graduation_pools", "graduation_pools.parquet"))
when = lambda ts: pd.to_datetime(ts, unit="s", utc=True).strftime("%Y-%m-%d %H:%M")   # noqa: E731
full = pools[(pools["complete"] == 1) & (pools["n_trades"] >= 5) & (pools["open_reserve_lam"] >= 50e9)]   # the filter the free stats page uses
lost = full["price_ratio_30m"] <= 0.10          # price at the last trade inside 30 minutes <= a tenth of the price at the first trade
print(f"graduation pools: {len(pools):,} opened {when(pools['open_t'].min())} to {when(pools['open_t'].max())} UTC")
print(f"full pools (open reserve >= 50 SOL, >= 5 trades, no capture gap): {len(full):,}")
print(f"lost 90% of the price within 30 minutes: {int(lost.sum()):,} ({lost.mean():.1%}); "
      f"median seconds from the open to the first price at or below a tenth: {full.loc[lost, 'collapsed_t'].median():.0f}")

```

## jocry/Pumpfun_Memecoin_Corpus / migrations.parquet: errore HTTPException: HTTP Error: HTTP GET error on 'https://huggingface.co/datasets/jocry/Pumpfun_Memecoin_Corpus/resolve/main/migrations.parquet' (HTTP 403)

## jocry/Pumpfun_Memecoin_Corpus / postgard_outcomes.parquet: errore HTTPException: HTTP Error: HTTP GET error on 'https://huggingface.co/datasets/jocry/Pumpfun_Memecoin_Corpus/resolve/main/postgard_outcomes.parquet' (HTTP 403)

## jocry/Pumpfun_Memecoin_Corpus / postgard_snapshots.parquet: errore HTTPException: HTTP Error: HTTP GET error on 'https://huggingface.co/datasets/jocry/Pumpfun_Memecoin_Corpus/resolve/main/postgard_snapshots.parquet' (HTTP 403)

## jocry/Pumpfun_Memecoin_Corpus / snapshots.parquet: errore HTTPException: HTTP Error: HTTP GET error on 'https://huggingface.co/datasets/jocry/Pumpfun_Memecoin_Corpus/resolve/main/snapshots.parquet' (HTTP 403)

## jocry/Pumpfun_Memecoin_Corpus / tokens.parquet: errore HTTPException: HTTP Error: HTTP GET error on 'https://huggingface.co/datasets/jocry/Pumpfun_Memecoin_Corpus/resolve/main/tokens.parquet' (HTTP 403)

## jocry/Pumpfun_Memecoin_Corpus / trades/trades-00000.parquet: errore HTTPException: HTTP Error: HTTP GET error on 'https://huggingface.co/datasets/jocry/Pumpfun_Memecoin_Corpus/resolve/main/trades/trades-00000.parquet' (HTTP 403)

## jocry/Pumpfun_Memecoin_Corpus / wallet_stats.parquet: errore HTTPException: HTTP Error: HTTP GET error on 'https://huggingface.co/datasets/jocry/Pumpfun_Memecoin_Corpus/resolve/main/wallet_stats.parquet' (HTTP 403)

## loopholetape/pumpfun-launches / data/features/2026-09-24.parquet: errore HTTPException: HTTP Error: HTTP GET error on 'https://huggingface.co/datasets/loopholetape/pumpfun-launches/resolve/main/data/features/2026-09-24.parquet' (HTTP 403)

## loopholetape/pumpfun-launches / data/graduation_pools/graduation_pools.parquet: errore HTTPException: HTTP Error: HTTP GET error on 'https://huggingface.co/datasets/loopholetape/pumpfun-launches/resolve/main/data/graduation_pools/graduation_pools.parquet' (HTTP 403)

## loopholetape/pumpfun-launches / data/launches/2026-09-27.parquet: errore HTTPException: HTTP Error: HTTP GET error on 'https://huggingface.co/datasets/loopholetape/pumpfun-launches/resolve/main/data/launches/2026-09-27.parquet' (HTTP 403)

## loopholetape/pumpfun-launches / data/launches_legacy/2026-08-31.parquet: errore HTTPException: HTTP Error: HTTP GET error on 'https://huggingface.co/datasets/loopholetape/pumpfun-launches/resolve/main/data/launches_legacy/2026-08-31.parquet' (HTTP 403)
