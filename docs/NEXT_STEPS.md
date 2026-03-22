# Next Steps

## ~~1. Fix Contract Verification~~ ✅ Done

Two issues were resolved:
- **Address mismatch:** DeFiLlama returns internal UUIDs, not `0x` addresses. Fixed by computing real pool addresses from token addresses + fee tier using Uniswap V3's deterministic CREATE2 formula.
- **Etherscan deprecated:** Both V1 and V2 Etherscan API endpoints are broken for free-tier keys. Switched to [Sourcify](https://sourcify.dev), a free open-source alternative with no API key required.

Result: 19 of 20 pools verified, ABIs saved to `pool_abis/`.

---

## 2. Store Data in a Database
Right now results only live in a CSV. Moving to a database enables historical tracking, queries, and joins.

**What to do:**
- Set up a local SQLite database (no server needed) or PostgreSQL
- Create a `pools` table and an `abi_registry` table
- Insert each pipeline run with a `fetched_at` timestamp so you can track how TVL and volume change over time
- Use `pandas.to_sql()` to load the DataFrame directly into the DB

---

## 3. Schedule the Pipeline to Run Automatically
A one-time snapshot has limited value for a data warehouse. Repeated runs build a time series.

**What to do:**
- Use Windows Task Scheduler (or a cron job) to run the notebook daily
- Alternatively use `schedule` or `APScheduler` in Python to automate execution
- Append new rows to the database on each run instead of overwriting the CSV

---

## 4. Expand Pool Coverage
The current pipeline is limited to Ethereum mainnet. Uniswap V3 is also deployed on several L2s with significant liquidity.

**What to do:**
- Add chains: Arbitrum, Optimism, Base, Polygon
- Filter by chain in DeFiLlama by changing `chain == "Ethereum"` to include others
- Add a `chain` column to the CSV and database schema

---

## 5. Pull On-Chain Data Using the ABIs
The saved ABIs unlock direct smart contract interaction — you can query live pool state without relying on a third-party API.

**What to do:**
- Use `web3.py` with an Infura or Alchemy RPC endpoint (both have free tiers)
- Call `slot0()` to get current price and tick
- Call `liquidity()` to get the active liquidity amount
- Call `fee()` to confirm the fee tier on-chain

---

## 6. Add Analytics and Visualization
Turn the raw data into insights.

**Suggested metrics to compute:**
- Capital efficiency: volume / TVL (higher = more active pool)
- Fee revenue estimate: volume × (fee_tier / 1,000,000)
- TVL concentration: what % of total TVL is in the top 5 pools

**Visualization ideas:**
- Bar chart: TVL by pool
- Scatter plot: TVL vs. daily volume (log scale)
- Time series: TVL trend over multiple pipeline runs
- Use `matplotlib` or `plotly` directly in the notebook

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
- Draw an ER diagram if you add multiple tables
- Note data freshness (DeFiLlama updates TVL roughly every hour)
