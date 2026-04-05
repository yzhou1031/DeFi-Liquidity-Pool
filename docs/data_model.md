# Data Model

## Overview

Three data stores capture different layers of the pipeline:

| Store | Format | Updated |
|-------|--------|---------|
| `data/defi_pools.db` (SQLite) | Relational — two tables | On each pipeline run |
| `data/pool_onchain.parquet` | Columnar | On each `onchain_data.ipynb` run |
| `data/top_pools.parquet` | Columnar | On each `defi_pipeline.ipynb` run |

DeFiLlama refreshes TVL and APY data roughly every hour. Historical data (`pool_history`) is fetched once per pipeline run and deduplicated on `(address, date)`.

---

## ER Diagram

```
┌─────────────────────────────────┐
│             pools               │
│─────────────────────────────────│
│ address (PK)       TEXT         │
│ chain              TEXT         │
│ token0             TEXT         │
│ token1             TEXT         │
│ fee_tier           INTEGER      │
│ tvl_usd            REAL         │
│ volume_usd         REAL         │
│ etherscan_verified INTEGER      │
│ fetched_at         TEXT         │
└──────────────┬──────────────────┘
               │ 1
               │ address
               │ N
┌──────────────┴──────────────────┐
│          pool_history           │
│─────────────────────────────────│
│ address (FK → pools)  TEXT      │
│ chain                 TEXT      │
│ date (YYYY-MM-DD)     TEXT      │
│ tvl_usd               REAL      │
│ apy                   REAL      │
│ apy_base              REAL      │
│ apy_base_7d           REAL      │
│ il_7d                 REAL      │
└─────────────────────────────────┘

(separate file — joined on address)
┌─────────────────────────────────┐
│        pool_onchain             │
│─────────────────────────────────│
│ address (FK → pools)  TEXT      │
│ chain                 TEXT      │
│ token0                TEXT      │
│ token1                TEXT      │
│ sqrt_price_x96        TEXT      │
│ tick                  INT64     │
│ liquidity             TEXT      │
│ fee                   INT64     │
│ dec0                  INT64     │
│ dec1                  INT64     │
│ price                 FLOAT64   │
│ fetched_at            TEXT      │
└─────────────────────────────────┘
```

Primary key for `pool_history` is `(address, date)` — `INSERT OR IGNORE` prevents duplicates.

---

## Table: `pools`

Sourced from DeFiLlama at fetch time. One row per unique pool.

| Column | Type | Source | Unit / Notes |
|--------|------|--------|--------------|
| `address` | TEXT | Computed via CREATE2 from token addresses + fee tier | `0x` hex string; PK |
| `chain` | TEXT | DeFiLlama `chain` field | One of: Ethereum, Arbitrum, Optimism, Base, Polygon |
| `token0` | TEXT | DeFiLlama `symbol` field (first token) | Ticker string, e.g. `USDC` |
| `token1` | TEXT | DeFiLlama `symbol` field (second token) | Ticker string, e.g. `WETH` |
| `fee_tier` | INTEGER | DeFiLlama `feeTier` | Pips (1 pip = 0.0001%). Common values: 100, 500, 3000, 10000 |
| `tvl_usd` | REAL | DeFiLlama `tvlUsd` | USD; total value locked at fetch time |
| `volume_usd` | REAL | DeFiLlama `volumeUsd1d` | USD; 24-hour trading volume at fetch time |
| `etherscan_verified` | INTEGER | Sourcify verification check | 1 = verified, 0 = not verified |
| `fetched_at` | TEXT | Set at pipeline runtime | ISO 8601 datetime string (UTC) |

---

## Table: `pool_history`

Daily time series per pool. Sourced from DeFiLlama Chart API and Dune Analytics backfill.

| Column | Type | Source | Unit / Notes |
|--------|------|--------|--------------|
| `address` | TEXT | FK → `pools.address` | `0x` hex string |
| `chain` | TEXT | Copied from `pools` | Chain name string |
| `date` | TEXT | DeFiLlama chart `timestamp` | `YYYY-MM-DD`; composite PK with `address` |
| `tvl_usd` | REAL | DeFiLlama `tvlUsd` | USD; daily TVL snapshot |
| `apy` | REAL | DeFiLlama `apy` | Percent annualized; includes base + reward APY |
| `apy_base` | REAL | DeFiLlama `apyBase` | Percent annualized; fee-only APY (no rewards) |
| `apy_base_7d` | REAL | DeFiLlama `apyBase7d` | Percent annualized; 7-day rolling average of base APY |
| `il_7d` | REAL | DeFiLlama `il7d` | Percent; 7-day impermanent loss relative to holding |

**Coverage:** May 2021 → present for core Ethereum pools (backfilled via Dune Analytics). March 2022 → present for most other pools (DeFiLlama hard limit). ~40,000 rows total.

---

## File: `pool_onchain.parquet`

Live on-chain state queried via `web3.py` using Uniswap V3 pool ABIs. One row per pool per run.

| Column | Type | Source | Unit / Notes |
|--------|------|--------|--------------|
| `address` | object (str) | Pool contract address | FK → `pools.address` |
| `chain` | object (str) | Chain name | Matches `pools.chain` |
| `token0` | object (str) | `token0()` on-chain call | Token ticker |
| `token1` | object (str) | `token1()` on-chain call | Token ticker |
| `sqrt_price_x96` | object (str) | `slot0()` → `sqrtPriceX96` | Q64.96 fixed-point integer (stored as string to avoid overflow) |
| `tick` | int64 | `slot0()` → `tick` | Current active tick index |
| `liquidity` | object (str) | `liquidity()` | Active in-range liquidity (uint128, stored as string) |
| `fee` | int64 | `fee()` | Fee tier in pips (matches `pools.fee_tier`) |
| `dec0` | int64 | `decimals()` on token0 contract | Token decimals (e.g. 6 for USDC, 18 for WETH, 8 for WBTC) |
| `dec1` | int64 | `decimals()` on token1 contract | Token decimals |
| `price` | float64 | Derived: `(sqrtPriceX96 / 2^96)^2 × 10^(dec0-dec1)` | token1 per token0 (human-readable) |
| `fetched_at` | object (str) | Set at query runtime | ISO 8601 datetime string (UTC) |

**RPC endpoints used:** Infura (Ethereum), Alchemy (Arbitrum, Optimism, Base), Ankr (Polygon). Retry backoff is applied to handle 429/rate-limit responses.

---

## Data Freshness

| Dataset | Granularity | Lag | How to refresh |
|---------|-------------|-----|----------------|
| `pools` | Snapshot | ~1 hour (DeFiLlama) | Re-run `defi_pipeline.ipynb` |
| `pool_history` | Daily | 1 day | Re-run `historical_data.ipynb` |
| `pool_onchain` | Snapshot | Real-time (block-level) | Re-run `onchain_data.ipynb` |
