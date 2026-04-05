"""
DeFi Liquidity Pool Dashboard — FinTech 590
Run: streamlit run dashboard.py
"""

import pathlib
import warnings
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

warnings.filterwarnings("ignore")

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DeFi Liquidity Pool Dashboard",
    page_icon="💧",
    layout="wide",
)

DATA_DIR = pathlib.Path("data")

CHAIN_COLORS = {
    "Ethereum": "#627EEA",
    "Arbitrum": "#28A0F0",
    "Optimism": "#FF0420",
    "Base":     "#0052FF",
    "Polygon":  "#8247E5",
}


# ── Data loading ─────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    pools = pd.read_parquet(DATA_DIR / "top_pools.parquet")
    history = pd.read_parquet(DATA_DIR / "pool_history.parquet")
    onchain = pd.read_parquet(DATA_DIR / "pool_onchain.parquet")

    # Labels
    pools["label"] = (
        pools["token0"] + "/" + pools["token1"]
        + " " + (pools["fee_tier"] / 1e4).map("{:.2f}%".format)
        + " (" + pools["chain"] + ")"
    )
    history["label"] = (
        history["token0"] + "/" + history["token1"]
        + " " + (history["fee_tier"] / 1e4).map("{:.2f}%".format)
    )
    onchain["label"] = (
        onchain["token0"] + "/" + onchain["token1"]
        + " " + (onchain["fee"] / 1e4).map("{:.2f}%".format)
        + " (" + onchain["chain"] + ")"
    )

    # Derived columns
    pools["fee_rate"] = pools["fee_tier"] / 1e6
    pools["cap_efficiency"] = pools["volume_usd"] / pools["tvl_usd"]
    pools["fee_revenue"] = pools["volume_usd"] * pools["fee_rate"]

    history["date"] = pd.to_datetime(history["date"])
    onchain["liquidity"] = onchain["liquidity"].astype(float)

    return pools, history, onchain


pools, history, onchain = load_data()

# ── Sidebar filters ───────────────────────────────────────────────────────────
st.sidebar.title("Filters")

all_chains = sorted(pools["chain"].unique())
selected_chains = st.sidebar.multiselect("Chains", all_chains, default=all_chains)

search = st.sidebar.text_input("Search pool (e.g. USDC, WETH)", "")

history_days = st.sidebar.slider("History window (days)", 30, 365 * 5, 365, step=30)

# Apply filters
pools_f = pools[pools["chain"].isin(selected_chains)].copy()
if search:
    mask = (
        pools_f["token0"].str.contains(search, case=False)
        | pools_f["token1"].str.contains(search, case=False)
    )
    pools_f = pools_f[mask]

history_f = history[history["chain"].isin(selected_chains)].copy()
cutoff = history_f["date"].max() - pd.Timedelta(days=history_days)
history_window = history_f[history_f["date"] >= cutoff]

onchain_f = onchain[onchain["chain"].isin(selected_chains)].copy()

# ── Header ────────────────────────────────────────────────────────────────────
st.title("💧 DeFi Liquidity Pool Dashboard")
st.caption(
    f"Uniswap V3 · {', '.join(selected_chains)} · "
    f"Pool snapshot: {pools['fetched_at'].max().date() if 'fetched_at' in pools.columns else 'N/A'} · "
    f"On-chain data: {onchain['fetched_at'].iloc[0] if 'fetched_at' in onchain.columns else 'N/A'}"
)

# ── KPI row ───────────────────────────────────────────────────────────────────
total_tvl = pools_f["tvl_usd"].sum()
total_vol = pools_f["volume_usd"].sum()
total_fees = pools_f["fee_revenue"].sum()
median_apy = (
    history_window.groupby("address")["apy_base"].median().median()
)
n_pools = len(pools_f)

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total TVL", f"${total_tvl/1e9:.2f}B")
k2.metric("24h Volume", f"${total_vol/1e6:.0f}M")
k3.metric("Est. Daily Fees", f"${total_fees/1e3:.0f}K")
k4.metric("Median APY (window)", f"{median_apy:.1f}%" if pd.notna(median_apy) else "N/A")
k5.metric("Pools", n_pools)

st.divider()

# ── Section 1: Current Snapshot ───────────────────────────────────────────────
st.subheader("1 · Current Pool Snapshot")

tab_tvl, tab_vol, tab_efficiency = st.tabs(["TVL", "Volume & Fee Revenue", "Capital Efficiency"])

with tab_tvl:
    top15 = pools_f.sort_values("tvl_usd", ascending=False).head(15)
    fig = px.bar(
        top15.sort_values("tvl_usd"),
        x="tvl_usd", y="label", orientation="h",
        color="chain", color_discrete_map=CHAIN_COLORS,
        labels={"tvl_usd": "TVL (USD)", "label": ""},
        title="TVL by Pool (Top 15)",
    )
    fig.update_xaxes(tickprefix="$", tickformat=",.0f")
    fig.update_layout(height=500, showlegend=True)
    st.plotly_chart(fig, use_container_width=True)

with tab_vol:
    top15 = pools_f.sort_values("volume_usd", ascending=False).head(15)
    fig = px.bar(
        top15.sort_values("fee_revenue"),
        x="fee_revenue", y="label", orientation="h",
        color="chain", color_discrete_map=CHAIN_COLORS,
        labels={"fee_revenue": "Est. Daily Fee Revenue (USD)", "label": ""},
        title="Estimated Daily Fee Revenue by Pool (Top 15)",
    )
    fig.update_xaxes(tickprefix="$", tickformat=",.0f")
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)

with tab_efficiency:
    fig = px.scatter(
        pools_f.dropna(subset=["cap_efficiency"]),
        x="tvl_usd", y="volume_usd",
        size="fee_revenue", color="chain",
        color_discrete_map=CHAIN_COLORS,
        hover_name="label",
        log_x=True, log_y=True,
        labels={"tvl_usd": "TVL (USD, log)", "volume_usd": "24h Volume (USD, log)"},
        title="TVL vs. Volume — Capital Efficiency (bubble = fee revenue)",
    )
    fig.update_xaxes(tickprefix="$")
    fig.update_yaxes(tickprefix="$")
    st.plotly_chart(fig, use_container_width=True)

# Full table (collapsible)
with st.expander("Full pool table"):
    display_cols = ["label", "chain", "tvl_usd", "volume_usd", "cap_efficiency", "fee_revenue"]
    display_cols = [c for c in display_cols if c in pools_f.columns]
    st.dataframe(
        pools_f[display_cols]
        .sort_values("tvl_usd", ascending=False)
        .reset_index(drop=True)
        .style.format({
            "tvl_usd": "${:,.0f}",
            "volume_usd": "${:,.0f}",
            "cap_efficiency": "{:.3f}",
            "fee_revenue": "${:,.0f}",
        }),
        use_container_width=True,
    )

st.divider()

# ── Section 2: Historical TVL ─────────────────────────────────────────────────
st.subheader("2 · Historical TVL Trends")

tab_total, tab_chain, tab_indexed = st.tabs(["Total", "By Chain", "Indexed Growth"])

with tab_total:
    daily_total = history_window.groupby("date")["tvl_usd"].sum().reset_index()
    fig = px.area(
        daily_total, x="date", y="tvl_usd",
        labels={"tvl_usd": "Total TVL (USD)", "date": ""},
        title="Total TVL Over Time — All Tracked Pools",
    )
    fig.update_yaxes(tickprefix="$", tickformat=".2s")
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

with tab_chain:
    daily_chain = (
        history_window.groupby(["date", "chain"])["tvl_usd"].sum().reset_index()
    )
    fig = px.line(
        daily_chain, x="date", y="tvl_usd", color="chain",
        color_discrete_map=CHAIN_COLORS,
        log_y=True,
        labels={"tvl_usd": "TVL (USD, log scale)", "date": "", "chain": "Chain"},
        title="TVL Over Time by Chain (Log Scale)",
    )
    fig.update_yaxes(tickprefix="$", tickformat=".2s")
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

with tab_indexed:
    daily_chain = (
        history_window.groupby(["date", "chain"])["tvl_usd"].sum().reset_index()
    )
    traces = []
    for chain, grp in daily_chain.groupby("chain"):
        grp = grp.sort_values("date")
        first = grp["tvl_usd"].iloc[0]
        if first > 0:
            grp = grp.copy()
            grp["indexed"] = grp["tvl_usd"] / first * 100
            traces.append(grp.assign(chain=chain))
    if traces:
        indexed_df = pd.concat(traces)
        fig = px.line(
            indexed_df, x="date", y="indexed", color="chain",
            color_discrete_map=CHAIN_COLORS,
            labels={"indexed": "TVL Index (start = 100)", "date": "", "chain": "Chain"},
            title="TVL Growth Indexed to Window Start",
        )
        fig.add_hline(y=100, line_dash="dash", line_color="gray", opacity=0.5)
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Section 3: APY Analysis ───────────────────────────────────────────────────
st.subheader("3 · APY Analysis")

tab_median, tab_vol_apy, tab_pool_ts = st.tabs(
    ["Median APY (window)", "APY Volatility", "Pool APY Over Time"]
)

with tab_median:
    median_apy_df = (
        history_window.groupby(["address", "label"])["apy_base"]
        .median()
        .reset_index()
        .sort_values("apy_base", ascending=False)
        .dropna()
        .head(15)
    )
    fig = px.bar(
        median_apy_df.sort_values("apy_base"),
        x="apy_base", y="label", orientation="h",
        color="apy_base", color_continuous_scale="Greens",
        labels={"apy_base": "Median Base APY (%)", "label": ""},
        title=f"Top 15 Pools by Median Base APY (Last {history_days} Days)",
    )
    fig.update_xaxes(ticksuffix="%")
    fig.update_layout(height=500, coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)

with tab_vol_apy:
    apy_vol_df = (
        history_window.groupby(["address", "label"])["apy_base"]
        .std()
        .reset_index()
        .rename(columns={"apy_base": "apy_std"})
        .dropna()
        .sort_values("apy_std", ascending=False)
        .head(15)
    )
    fig = px.bar(
        apy_vol_df.sort_values("apy_std"),
        x="apy_std", y="label", orientation="h",
        color="apy_std", color_continuous_scale="Reds",
        labels={"apy_std": "APY Std Dev (%)", "label": ""},
        title=f"Top 15 Pools by APY Volatility (Last {history_days} Days)",
    )
    fig.update_xaxes(ticksuffix="%")
    fig.update_layout(height=500, coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)

with tab_pool_ts:
    # Let user pick up to 5 pools to compare
    pool_options = sorted(history_window["label"].dropna().unique())
    default_picks = pool_options[:3] if len(pool_options) >= 3 else pool_options
    selected_pools = st.multiselect("Select pools", pool_options, default=default_picks, key="apy_pools")
    if selected_pools:
        ts_data = history_window[history_window["label"].isin(selected_pools)]
        fig = px.line(
            ts_data, x="date", y="apy_base", color="label",
            labels={"apy_base": "Base APY (%)", "date": "", "label": "Pool"},
            title="Base APY Over Time — Selected Pools",
        )
        fig.update_yaxes(ticksuffix="%")
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Section 4: Risk Metrics ────────────────────────────────────────────────────
st.subheader("4 · Risk Metrics")

tab_il, tab_concentration = st.tabs(["Impermanent Loss", "TVL Concentration"])

with tab_il:
    il_data = history_window.dropna(subset=["il_7d"])
    daily_il = il_data.groupby("date")["il_7d"].median().reset_index()
    fig = px.area(
        daily_il, x="date", y="il_7d",
        labels={"il_7d": "Median 7-Day IL (%)", "date": ""},
        title="Median Impermanent Loss Over Time (All Pools)",
        color_discrete_sequence=["tomato"],
    )
    fig.update_yaxes(tickformat=".3f", ticksuffix="%")
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

with tab_concentration:
    tvl_sorted = pools_f.sort_values("tvl_usd", ascending=False).reset_index(drop=True)
    tvl_sorted["cumulative_pct"] = tvl_sorted["tvl_usd"].cumsum() / tvl_sorted["tvl_usd"].sum() * 100
    top5_pct = tvl_sorted.head(5)["tvl_usd"].sum() / tvl_sorted["tvl_usd"].sum() * 100

    fig = px.bar(
        tvl_sorted.head(15),
        x="label", y="tvl_usd",
        color="chain", color_discrete_map=CHAIN_COLORS,
        labels={"tvl_usd": "TVL (USD)", "label": ""},
        title=f"TVL Concentration — Top 5 pools hold {top5_pct:.1f}% of total TVL",
    )
    fig.update_yaxes(tickprefix="$", tickformat=",.0f")
    fig.update_xaxes(tickangle=45)
    fig.update_layout(height=450)
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Section 5: On-Chain Live State ────────────────────────────────────────────
st.subheader("5 · On-Chain Live State")

if onchain_f.empty:
    st.info("No on-chain data for selected chains.")
else:
    top_liq = onchain_f.nlargest(15, "liquidity")
    fig = px.bar(
        top_liq.sort_values("liquidity"),
        x="liquidity", y="label", orientation="h",
        color="chain", color_discrete_map=CHAIN_COLORS,
        labels={"liquidity": "Active Liquidity (raw units)", "label": ""},
        title="Live Active Liquidity by Pool (Top 15)",
    )
    fig.update_xaxes(tickformat=".2e")
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Full on-chain table"):
        display_cols = [c for c in ["label", "chain", "price", "tick", "liquidity", "fetched_at"] if c in onchain_f.columns]
        st.dataframe(
            onchain_f[display_cols]
            .sort_values("liquidity", ascending=False)
            .reset_index(drop=True)
            .style.format({"liquidity": "{:.2e}", "price": "{:.6f}"}),
            use_container_width=True,
        )

st.divider()
st.caption("Data: DeFiLlama · Dune Analytics · Uniswap V3 on-chain ABIs · Built with Streamlit")
