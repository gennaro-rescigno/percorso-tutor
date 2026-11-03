# AratiKamat/red-pump-2026

licenza: cc-by-4.0 · gated: False · file: 8 · dimensione totale: 0.18 GB

## File
- .gitattributes (0.0 MB)
- CITATION.cff (0.0 MB)
- LICENSE.txt (0.0 MB)
- README.md (0.0 MB)
- SHA256SUMS (0.0 MB)
- reconstructed_mint_observation_windows_v1.parquet (91.8 MB)
- red_pump_2026_v1_launches.jsonl.gz (47.9 MB)
- red_pump_2026_v1_outcomes.csv.gz (43.6 MB)

## Scheda

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

