# DeFi Liquidity Pool Pipeline
**FinTech 590 — Data Warehousing Project**

Automated pipeline that fetches the top 20 Uniswap V3 liquidity pools by TVL, verifies each contract on Etherscan, and exports the results to CSV and JSON.

---

## Files

| File | Description |
|------|-------------|
| `defi_pipeline.ipynb` | Main pipeline notebook — run this |
| `Untitled.ipynb` | Scratch file, ignore |
| `top_pools.csv` | Output: pool data with TVL, volume, verification status |
| `pool_abis/` | Output: one ABI JSON file per verified pool contract |

---

## How It Works

The pipeline runs in 4 sequential notebook cells:

### Cell 0 — Install Dependencies
Auto-installs `requests`, `pandas`, and `python-dotenv` if not already present. Safe to re-run.

### Cell 1 — Config & API Key
Reads your Etherscan API key from a `.env` file. If the file doesn't exist, it prompts you to paste the key and saves it automatically. Also sets up output paths.

### Cell 2 — Fetch Top Uniswap V3 Pools
Pulls pool data from the [DeFiLlama Yields API](https://yields.llama.fi/docs) (free, no key needed), filters to:
- Protocol: Uniswap V3
- Chain: Ethereum
- TVL > $1,000,000

Sorts by TVL descending and keeps the top 20. Collects: pool address, token pair, fee tier, TVL (USD), and daily volume (USD).

> **Why DeFiLlama and not The Graph?**
> The Graph shut down their free hosted service in 2024. The original Uniswap V3 subgraph at `api.thegraph.com` no longer works. DeFiLlama provides equivalent data for free with no API key.

### Cell 3 — Verify Contracts on Etherscan
For each pool address, calls the [Etherscan API](https://docs.etherscan.io/) to check if the contract source is verified. If verified, downloads and saves the full ABI to `pool_abis/{address}.json`. Respects the free tier rate limit (5 req/s) with a 0.21s delay between calls and automatic retry on rate-limit errors.

### Cell 4 — Save Results
Writes `top_pools.csv` with columns:

| Column | Description |
|--------|-------------|
| `address` | Pool contract address |
| `token0` | First token symbol |
| `token1` | Second token symbol |
| `fee_tier` | Fee in pips (e.g. 500 = 0.05%) |
| `tvl_usd` | Total value locked in USD |
| `volume_usd` | 24h trading volume in USD |
| `etherscan_verified` | Whether the contract source is verified |

---

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/yzhou1031/DeFi-Liquidity-Pool.git
cd DeFi-Liquidity-Pool
```

**2. Create a `.env` file** with your Etherscan API key:
```
ETHERSCAN_API_KEY=your_key_here
```
Get a free key at [etherscan.io/apis](https://etherscan.io/apis). The `.env` file is gitignored and will never be committed.

**3. Open and run `defi_pipeline.ipynb`** in Jupyter or VS Code, top to bottom.

No manual `pip install` needed — Cell 0 handles it.

---

## Requirements

- Python 3.10+
- `requests`, `pandas`, `python-dotenv` (auto-installed by Cell 0)
- Free Etherscan API key
