# Pipeline Roadmap

## ~~1. Fix Contract Verification~~ ✅ Done

Two issues were resolved:
- **Address mismatch:** DeFiLlama returns internal UUIDs, not `0x` addresses. Fixed by computing real pool addresses from token addresses + fee tier using Uniswap V3's deterministic CREATE2 formula.
- **Etherscan deprecated:** Both V1 and V2 Etherscan API endpoints are broken for free-tier keys. Switched to [Sourcify](https://sourcify.dev), a free open-source alternative with no API key required.

Result: 19 of 20 pools verified, ABIs saved to `pool_abis/`.

---

## ~~2. Store Data in a Database~~ ✅ Done

SQLite database built in `database.ipynb`. No server required — single file at `data/defi_pools.db`.

**Tables:**
- `pools` — 20 rows, one per pool, with `fetched_at` timestamp
- `pool_history` — rows covering May 2021 → present (see Step 2b and Issue #1)

Re-running is safe: `pools` uses `INSERT OR REPLACE`, `pool_history` uses `INSERT OR IGNORE` to prevent duplicates.

---

## ~~2b. Fetch Historical Pool Data~~ ✅ Done

Historical TVL, APY, and impermanent loss fetched in `historical_data.ipynb` via the DeFiLlama Chart API (`yields.llama.fi/chart/{pool_id}`).

**Output:** `data/pool_history.parquet` — one row per pool per day, with fields:
- `date`, `tvl_usd`, `apy`, `apy_base`, `apy_base_7d`, `il_7d`

---

## ~~3. Schedule the Pipeline to Run Automatically~~ ❌ Replaced by Step 2b

> **Revised:** Running the pipeline daily to collect data going forward would take weeks to build up meaningful history. Instead, we use DeFiLlama's historical chart API which provides daily data going back to **March 2022** (~1,400 data points per pool) — available immediately. Extended to May 2021 via Dune Analytics (see Issue #1).

---

## ~~4. Expand Pool Coverage to L2s~~ ✅ Done

Multi-chain support added to `defi_pipeline.ipynb`. Now fetches the top 20 Uniswap V3 pools across:
- Ethereum, Arbitrum, Optimism, Base, Polygon

A `chain` column is included in `top_pools.parquet`. Chain-specific factory addresses are used for correct CREATE2 pool address derivation.

---

## ~~5. Pull On-Chain Data Using the ABIs~~ ✅ Done

`onchain_data.ipynb` built using `web3.py` with Infura/Alchemy RPC endpoints.

**Queries per pool:**
- `slot0()` — current price (as sqrtPriceX96) and active tick
- `liquidity()` — active liquidity amount
- `fee()` — confirms fee tier on-chain

**Output:** `data/pool_onchain.parquet` — live snapshot per pool.

Polygon RPC reliability issues were resolved with retry backoff and token decimal normalization (Issue #4).

---

## ~~6. Add Analytics and Visualization~~ ✅ Done

`analytics.ipynb` computes and charts key metrics across all pools and chains:

| Chart | Description |
|-------|-------------|
| TVL by chain (bar, log, indexed, subplots) | Chain-level TVL distribution and growth |
| TVL vs. volume scatter | Capital efficiency per pool |
| TVL concentration | % of total TVL in top 5 pools |
| Fee revenue estimate | `volume × fee_tier / 1,000,000` |
| APY comparison & volatility | APY distribution and standard deviation per pool |
| IL over time | Impermanent loss trends |
| On-chain liquidity | Live liquidity snapshot from `pool_onchain.parquet` |

All charts saved to `data/*.png`.

---

## 7. Build a Simple Dashboard

Package the analysis into a shareable, interactive interface.

**Options:**
- **Streamlit** — quickest to build, runs locally, easy to share
- **Dash (Plotly)** — more control over layout
- Display the top pools table, charts, and last-updated timestamp
- Can be deployed for free on Streamlit Community Cloud

---

## 8. Document the Data Model

Good data warehouse practice includes schema documentation.

**What to do:**
- Write a data dictionary describing every field (type, source, unit)
- Draw an ER diagram covering `pools`, `pool_history`, and `pool_onchain`
- Note data freshness (DeFiLlama updates TVL roughly every hour)

---

## Open Issues

### ~~Issue #1 — Extend Historical Data Back to May 2021~~ ✅ Done

Used Dune Analytics to backfill `pool_history` from May 2021 to March 2022 (the DeFiLlama hard limit). Merged with existing DeFiLlama data using `(address, date)` as deduplication key. Core pools (WBTC/WETH, USDC/WETH, etc.) now have ~5 years of daily data.

---

### ~~Issue #2 — Migrate Data Storage from CSV to Parquet~~ ✅ Done

All pipeline outputs now use Parquet format via `pyarrow`:
- `data/top_pools.parquet`
- `data/pool_history.parquet`
- `data/pool_onchain.parquet`

SQLite (`data/defi_pools.db`) is retained for ad-hoc SQL queries. Parquet delivers 60–80% smaller file sizes and faster column reads.

---

### ~~Issue #4 — Pull On-Chain Data Using Pool ABIs~~ ✅ Done

`onchain_data.ipynb` built to query live Uniswap V3 pool state across all 5 chains using the saved ABIs in `pool_abis/`.

**Calls per pool:** `slot0()` (sqrtPriceX96 + current tick), `liquidity()` (active in-range liquidity), `fee()` (fee tier in pips).

**Output:** `data/pool_onchain.parquet` — one row per pool per run.

**Issues resolved in follow-up commit:**
- Polygon 401 → switched to `rpc.ankr.com/polygon`
- Base/Ethereum 429 rate limiting → added retry backoff
- `price_raw` decimal adjustment → token decimals fetched via `decimals()` on each token contract

Sanity check passed: all on-chain fee tiers match DeFiLlama data.

---

### Issue #3 — Support Additional DeFi Protocols (Optional)

**Status:** Open
**Priority:** Low / Optional

The pipeline is currently hardcoded to Uniswap V3. Candidate protocols: Uniswap V2, Curve Finance, Balancer V2, Aerodrome, PancakeSwap V3.

**What to do:**
- Parameterize the protocol filter via a `PROTOCOL` config variable
- Add a `protocol` column to `top_pools` and `pool_history`
- Note: CREATE2 address derivation is Uniswap V3-specific — other protocols need separate factory/init-code logic
- Test with Curve first (stable DeFiLlama coverage)
