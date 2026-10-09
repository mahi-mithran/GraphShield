"""
GraphShield - Operational Fraud Dashboard
Page 1: 1_Dashboard.py
Requirements:
  - Total transactions
  - Count and % for each of FRAUD / MID_LEVEL / GENUINE
  - Bar chart of decision distribution
  - Bar chart of transactions by sector
  - Table of recent transactions with tiers color-coded (red: FRAUD, orange: MID_LEVEL, green: GENUINE)
  - Graceful connection error handling: 'Could not reach backend API. Is it running?'
"""

import sys
from pathlib import Path

# Make the project root importable so `from frontend.components...` works
# no matter where / how Streamlit is launched (fixes ModuleNotFoundError: No module named 'frontend').
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd
from frontend.components.api_client import api_client, render_api_error_if_any

st.set_page_config(page_title="GraphShield - Fraud Dashboard", page_icon="📊", layout="wide")

st.title("📊 Financial Fraud Operations Dashboard")
st.caption("Live monitoring of transaction flow, risk tiers, and sector exposure.")

# Fetch Aggregated Stats from FastAPI backend
stats_data, error = api_client.get_dashboard_stats()

if error:
    render_api_error_if_any(error)
    st.stop()

if not stats_data or stats_data.get("total_transactions", 0) == 0:
    st.warning("No transaction data available yet. Please generate the dataset or run transaction checks.")
    st.stop()

# 1. Top KPI Metric Cards (Total, Count & % for each tier)
total_tx = stats_data["total_transactions"]
fraud_count = stats_data["fraud_count"]
fraud_pct = stats_data["fraud_percent"]
mid_count = stats_data["mid_level_count"]
mid_pct = stats_data["mid_level_percent"]
genuine_count = stats_data["genuine_count"]
genuine_pct = stats_data["genuine_percent"]

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric(
        label="Total Monitored Transactions",
        value=f"{total_tx:,}",
        help="All historical and live transactions evaluated by GraphShield",
    )

with c2:
    st.metric(
        label="🔴 FRAUD (High Risk)",
        value=f"{fraud_count:,}",
        delta=f"{fraud_pct}% of total",
        delta_color="inverse",
        help="Score >= 0.70 (Transactions automatically blocked)",
    )

with c3:
    st.metric(
        label="🟠 MID_LEVEL (Step-Up / Review)",
        value=f"{mid_count:,}",
        delta=f"{mid_pct}% of total",
        delta_color="off",
        help="0.30 <= Score < 0.70 (Step-up 2FA/OTP or analyst verification required)",
    )

with c4:
    st.metric(
        label="🟢 GENUINE (Low Risk)",
        value=f"{genuine_count:,}",
        delta=f"{genuine_pct}% of total",
        delta_color="normal",
        help="Score < 0.30 (Instant frictionless approval)",
    )

st.markdown("---")

# 2. Charts Section: Decision Distribution & Sector Breakdown
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.subheader("🎯 3-Tier Decision Distribution")
    decision_dist = stats_data.get("decision_distribution", {})
    df_decision = pd.DataFrame(
        [
            {"Decision Tier": "FRAUD", "Count": decision_dist.get("FRAUD", 0)},
            {"Decision Tier": "MID_LEVEL", "Count": decision_dist.get("MID_LEVEL", 0)},
            {"Decision Tier": "GENUINE", "Count": decision_dist.get("GENUINE", 0)},
        ]
    )
    st.bar_chart(
        df_decision.set_index("Decision Tier"),
        color="#1E88E5",
        use_container_width=True,
    )

with col_chart2:
    st.subheader("🏢 Transactions by Industry Sector")
    sector_dist = stats_data.get("sector_distribution", {})
    if sector_dist:
        df_sector = pd.DataFrame(
            [{"Sector": k, "Volume": v} for k, v in sector_dist.items()]
        ).sort_values(by="Volume", ascending=False)
        st.bar_chart(
            df_sector.set_index("Sector"),
            color="#26A69A",
            use_container_width=True,
        )
    else:
        st.info("No sector data available.")

st.markdown("---")

# 3. Recent Transactions Table with Color-Coded Tiers
st.subheader("📋 Recent Transaction Stream")

# Filter controls
col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
with col_f1:
    tier_filter = st.selectbox(
        "Filter by Decision Tier",
        ["ALL", "FRAUD", "MID_LEVEL", "GENUINE"],
    )
with col_f2:
    sector_filter = st.selectbox(
        "Filter by Sector",
        ["ALL"] + list(stats_data.get("sector_distribution", {}).keys()),
    )
with col_f3:
    limit_filter = st.slider("Display Limit", min_value=10, max_value=200, value=50, step=10)

selected_decision = None if tier_filter == "ALL" else tier_filter
selected_sector = None if sector_filter == "ALL" else sector_filter

tx_data, tx_err = api_client.get_transactions(
    limit=limit_filter,
    decision=selected_decision,
    sector=selected_sector,
)

if tx_err:
    render_api_error_if_any(tx_err)
elif not tx_data:
    st.info("No matching transactions found for the specified filters.")
else:
    df_tx = pd.DataFrame(tx_data)
    
    # Format and select columns
    columns_to_show = [
        "transaction_id",
        "account_id",
        "amount",
        "currency",
        "sector",
        "device_id",
        "ip_address",
        "risk_score",
        "decision",
        "status",
        "timestamp",
    ]
    df_view = df_tx[[c for c in columns_to_show if c in df_tx.columns]].copy()
    
    # Styling function for 3-tier colors: red for FRAUD, orange for MID_LEVEL, green for GENUINE
    def highlight_decision_tier(row):
        tier = str(row.get("decision", "")).upper()
        if tier == "FRAUD":
            return ["background-color: rgba(239, 68, 68, 0.22); color: #B91C1C; font-weight: bold;"] * len(row)
        elif tier == "MID_LEVEL":
            return ["background-color: rgba(249, 115, 22, 0.22); color: #C2410C; font-weight: bold;"] * len(row)
        elif tier == "GENUINE":
            return ["background-color: rgba(34, 197, 94, 0.18); color: #15803D; font-weight: bold;"] * len(row)
        return [""] * len(row)

    styled_df = df_view.style.apply(highlight_decision_tier, axis=1).format({
        "amount": "{:,.2f}",
        "risk_score": "{:.3f}",
    })

    st.dataframe(styled_df, use_container_width=True, height=450)
    st.caption("🔴 Red: **FRAUD** | 🟠 Orange: **MID_LEVEL** | 🟢 Green: **GENUINE**")
