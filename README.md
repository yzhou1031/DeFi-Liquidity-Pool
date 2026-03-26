# DeFi Liquidity Pool Pipeline
**FinTech 590 — Data Wrangling Project**

Automated pipeline that fetches the top 20 Uniswap V3 liquidity pools by TVL across **Ethereum, Arbitrum, Optimism, Base, and Polygon**, verifies each contract on Sourcify, and exports the results to Parquet and JSON.

---

## Repo Structure

```
DeFi-Liquidity-Pool/
├── defi_pipeline.ipynb      # Main pipeline — run this
├── README.md
├── .gitignore
│
├── data/
│   ├── top_pools.parquet    # Output: pool data with TVL, volume, verification status
│   ├── pool_history.parquet # Output: daily TVL/APY history per pool
│   └── pool_abis/           # Output: one ABI JSON file per verified pool
│
└── docs/
    ├── NEXT_STEPS.md        # Project roadmap
    └── prompt.md            # Original prompt and build context
```

---

## How It Works

The pipeline runs in 4 sequential notebook cells:

### Cell 0 — Install Dependencies
Auto-installs `requests`, `pandas`, `python-dotenv`, and `web3` if not already present. Safe to re-run.

### Cell 1 — Config
Sets up output paths and API constants. No API key required — all data sources are free.

### Cell 2 — Fetch Top Uniswap V3 Pools
Pulls pool data from the [DeFiLlama Yields API](https://yields.llama.fi/docs) (free, no key needed), filters to:
- Protocol: Uniswap V3
- Chains: Ethereum, Arbitrum, Optimism, Base, Polygon
- TVL > $1,000,000

Sorts by TVL descending and keeps the top 20. Since DeFiLlama returns internal UUIDs instead of on-chain addresses, real pool addresses are computed using Uniswap V3's deterministic **CREATE2** formula from each pool's token addresses and fee tier.

> **Why DeFiLlama and not The Graph?**
> The Graph shut down their free hosted service in 2024. DeFiLlama provides equivalent data for free with no API key.

### Cell 3 — Verify Contracts on Sourcify
For each pool address, checks [Sourcify](https://sourcify.dev) — a free open-source contract verification service — for verification status and downloads the full ABI to `data/pool_abis/{address}.json`.

> **Why Sourcify and not Etherscan?**
> Etherscan V1 was shut down in 2024 and V2 rejects free-tier keys. Sourcify requires no API key and has all Uniswap V3 pool contracts verified.

### Cell 4 — Save Results
Writes `data/top_pools.parquet` (Parquet format, engine: pyarrow) with columns:

| Column | Description |
|--------|-------------|
| `address` | Pool contract address |
| `token0` | First token symbol |
| `token1` | Second token symbol |
| `fee_tier` | Fee in pips (e.g. 500 = 0.05%) |
| `tvl_usd` | Total value locked in USD |
| `volume_usd` | 24h trading volume in USD |
| `etherscan_verified` | Whether the contract source is verified on Sourcify |

`historical_data.ipynb` writes `data/pool_history.parquet` with daily TVL, APY, and impermanent loss per pool. Parquet offers 60–80% smaller file sizes and faster column reads compared to CSV.

---

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/yzhou1031/DeFi-Liquidity-Pool.git
cd DeFi-Liquidity-Pool
```

**2. Run the notebooks in order** in Jupyter or VS Code, top to bottom:

| Step | Notebook | Output |
|------|----------|--------|
| 1 | `defi_pipeline.ipynb` | `data/top_pools.parquet` |
| 2 | `historical_data.ipynb` | `data/pool_history.parquet` |
| 3 | `database.ipynb` | `data/defi_pools.db` |

No API keys or manual `pip install` needed — Cell 0 handles dependencies automatically.

---

## Requirements

- Python 3.10+
- `requests`, `pandas`, `python-dotenv`, `web3`, `pyarrow` (auto-installed by Cell 0)
