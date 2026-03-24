# Open Issues

Tracked improvements for the DeFi Liquidity Pool pipeline.

---

## Issue #1 — Extend Historical Data Back to 2021

**Status:** Open
**Priority:** High

**Problem:**
`pool_history` currently starts at **March 2022** (~1,400 data points per pool). DeFiLlama's chart API (`yields.llama.fi/chart/{pool_id}`) may return data going back to **2021** for pools that existed then, but the pipeline never checks how far back the data actually goes.

**What to do:**
- Re-run `historical_data.ipynb` and inspect the earliest `date` returned per pool
- Check which pools have pre-2022 history (most major WETH/USDC/USDT pools launched mid-2021)
- Remove any artificial date floor in the fetch logic if one exists
- On re-ingest, use `INSERT OR IGNORE` so existing rows are not duplicated
- Update the `pool_history` table / CSV to include the newly fetched rows
- Validate: `SELECT MIN(date) FROM pool_history` should return a 2021 date for at least the major pools

**Expected outcome:**
~800–900 additional daily rows per pool (roughly May 2021 → March 2022), giving ~2,200+ data points per pool and enabling longer-horizon trend analysis.

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
