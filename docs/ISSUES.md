# Open Issues

Tracked improvements for the DeFi Liquidity Pool pipeline.

---

## Issue #1 — Extend Historical Data Back to May 2021 via Dune Analytics

**Status:** Closed
**Priority:** High

**Problem:**
`pool_history` currently starts at **March 2022** — the hard limit of DeFiLlama's yields API. Uniswap V3 launched **May 5, 2021**, so ~10 months of data are missing for the core pools. DeFiLlama does not have yield/TVL data before March 2022 and cannot be used to close this gap.

**Why Dune Analytics:**
Dune has pre-processed Uniswap V3 event tables (Swap, Mint, Burn) on Ethereum going back to the V3 launch block. Free tier includes 2,500 credits/month — sufficient for a one-time historical backfill. No complex on-chain RPC pagination required.

**What to do:**
- Sign up for a free Dune Analytics account and generate an API key
- Query the `uniswap_v3_ethereum.Pool_evt_Swap` (and Mint/Burn) tables for each pool address, filtered to `2021-05-01` through `2022-03-26` (the gap period)
- Aggregate to daily TVL and volume to match the existing `pool_history` schema
- Merge the Dune results with the existing DeFiLlama data — use date + address as the deduplication key
- Note: only pools that existed in May 2021 will have data (WBTC/WETH, USDC/WETH, UNI/WETH, LINK/WETH, etc.) — newer pools like AUSD/USDC or OHM/SUSDS won't be affected
- Validate: `SELECT MIN(date) FROM pool_history` should return a May 2021 date for the legacy pools

**Expected outcome:**
~300 additional daily rows per eligible pool (May 2021 → March 2022), extending the panel from ~4 years to ~5 years for the core pools.

---

## Issue #2 — Migrate Data Storage from CSV/SQLite to Parquet

**Status:** Open
**Priority:** High

**Problem:**
Current outputs are `top_pools.csv`, `pool_history.csv`, and `data/defi_pools.db` (SQLite). For a dataset growing to 40,000+ rows across 20 pools, Parquet offers better compression, faster column-level reads, and native support in pandas, DuckDB, and most analytics tools.

**What to do:**
- Add `pyarrow` (or `fastparquet`) to the Cell 0 auto-install block
- In `historical_data.ipynb`, replace the CSV write with:
  ```python
  df.to_parquet("data/pool_history.parquet", index=False, engine="pyarrow")
  ```
- In `defi_pipeline.ipynb`, replace the CSV write with:
  ```python
  df.to_parquet("data/top_pools.parquet", index=False, engine="pyarrow")
  ```
- Decide whether to keep SQLite in parallel or drop it — SQLite is still useful for ad-hoc SQL queries, so keeping both is reasonable
- Update `.gitignore` to exclude `*.parquet` if files grow large
- Update `README.md` to reflect the new output format and column descriptions

**Expected outcome:**
`pool_history.parquet` should be 60–80% smaller than the equivalent CSV, with faster read times in downstream analysis notebooks.

---

## Issue #3 — Support Additional DeFi Protocols (Optional)

**Status:** Open
**Priority:** Low / Optional

**Problem:**
The pipeline is currently hardcoded to **Uniswap V3 on Ethereum mainnet**. Other major AMM protocols represent significant TVL and offer complementary data.

**Candidate protocols (all supported by DeFiLlama):**

| Protocol | Type | Notes |
|---|---|---|
| Uniswap V2 | AMM | Older constant-product model, still high TVL |
| Curve Finance | Stable AMM | Optimized for stablecoin/like-asset pairs |
| Balancer V2 | Weighted AMM | Multi-token pools with custom weights |
| Aerodrome | AMM (Base L2) | Largest DEX on Base by TVL |
| PancakeSwap V3 | AMM (BSC/Base) | Uniswap V3 fork, different fee tiers |

**What to do:**
- Parameterize the protocol filter: replace the hardcoded `"uniswap-v3"` string with a `PROTOCOL` config variable
- Add a `protocol` column to `top_pools` and `pool_history` so data from multiple protocols can coexist in the same Parquet file
- Note: CREATE2 address computation is Uniswap V3-specific — other protocols use different factory addresses and init code hashes, so that logic will need to be protocol-aware or skipped
- Contract verification via Sourcify still works for any EVM address — no changes needed there
- Test with Curve first since DeFiLlama has deep Curve coverage and the pool IDs are stable

**Expected outcome:**
A multi-protocol dataset that enables cross-protocol TVL and APY comparisons, making the project significantly more useful for research and the final writeup.

---

## Notes

- Issues #1 and #2 are independent and can be worked in parallel
- Issue #2 (Parquet) should be completed before Issue #3 so the expanded multi-protocol data lands in the right format from the start
- The DeFiLlama chart API has no rate limit documentation — add a `time.sleep(0.5)` between requests if fetching data for many pools across multiple protocols
