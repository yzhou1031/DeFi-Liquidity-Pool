# Project Prompt & Conversation Context

This file documents the original prompt and key decisions made during the build of this pipeline.

---

## Original Prompt

> You are helping me build a DeFi data pipeline for a university project. I need you to complete the following tasks end to end:
>
> **1. Fetch top Uniswap V3 pools from The Graph**
> - Query the Uniswap V3 subgraph at https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3
> - Get the top 20 pools ordered by totalValueLockedUSD descending, filtered to TVL > $1M
> - For each pool, collect: address, token0 symbol, token1 symbol, fee tier, TVL (USD), volume (USD)
>
> **2. Verify each pool contract on Etherscan**
> - Use the free Etherscan API to confirm each pool contract is verified
> - Retrieve and store the ABI for each verified pool
> - Respect the free tier rate limit (max 5 requests/second)
>
> **3. Save the results**
> - Save a `top_pools.csv` with columns: address, token0, token1, fee_tier, tvl_usd, volume_usd, etherscan_verified
> - Save a `pool_abis/` folder with one JSON file per verified pool named `{address}.json`
>
> **Setup:** Use Python with requests, pandas, and python-dotenv. Install any missing dependencies automatically. Store secrets in a .env file and never hardcode API keys.

---

## Issues Encountered & How They Were Resolved

### 1. The Graph hosted service shut down
The original subgraph endpoint `api.thegraph.com/subgraphs/name/uniswap/uniswap-v3` was removed in 2024.

**Fix:** Switched to the [DeFiLlama Yields API](https://yields.llama.fi/pools) — free, no API key required, covers Uniswap V3 on Ethereum and all major L2s.

### 2. DeFiLlama returns UUIDs, not Ethereum addresses
DeFiLlama's `pool` field is an internal UUID (e.g. `665dc8bc-c79d-4800-97f7-304bf368e547`), not a real `0x` contract address — so Etherscan returned "not verified" for every pool.

**Fix:** Computed the real on-chain pool address using Uniswap V3's deterministic **CREATE2** formula:
- Inputs: token0 address, token1 address, fee tier (from DeFiLlama's `underlyingTokens` and `poolMeta` fields)
- Factory: `0x1F98431c8aD98523631AE4a59f267346ea31F984`
- Init code hash: `0xe34f199b19b2b4f47f68442619d555527d244f78a3297ea89325f843f87b8b54`

Verified against known pool addresses (e.g. USDC/WETH 0.05% = `0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640` ✓).

### 3. Etherscan API fully deprecated
- **V1** (`api.etherscan.io/api`) was shut down — returns "deprecated endpoint" for all requests regardless of API key
- **V2** (`api.etherscan.io/v2/api`) rejected free-tier keys with "Invalid API Key"

**Fix:** Switched to [Sourcify](https://sourcify.dev) — a free, open-source contract verification service with no API key required. Uniswap V3 pool contracts are verified there by the Uniswap team.

---

## Final Architecture

| Step | Data Source | Auth |
|------|-------------|------|
| Fetch pools | DeFiLlama Yields API | None |
| Compute addresses | Uniswap V3 CREATE2 formula | None |
| Verify contracts + get ABI | Sourcify | None |

---

## Key Design Decisions

- **Notebooks over scripts:** All code lives in `defi_pipeline.ipynb` for step-by-step execution and inline output visibility.
- **No hardcoded secrets:** API keys (Etherscan, GitHub) are stored in `.env` which is gitignored.
- **Unverified pool kept:** 1 of 20 pools is not on Sourcify. It's kept in the dataset with `etherscan_verified = False` rather than dropped — the flag itself is useful data.
- **`web3.py` added as dependency:** Required for the keccak256 hashing in the CREATE2 address computation.
