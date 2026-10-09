"""
GraphShield - Streamlit Multi-Page Main Entrypoint
Smart India Hackathon 2026 (SIH26199) - Team GraphSentinelz
"""

import sys
from pathlib import Path

# Make the project root importable so `from frontend.components...` works
# no matter where / how Streamlit is launched (fixes ModuleNotFoundError: No module named 'frontend').
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from frontend.components.api_client import api_client, render_api_error_if_any

# Set page configuration
st.set_page_config(
    page_title="GraphShield - Fraud Detection",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0px;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #475569;
        margin-bottom: 25px;
    }
    .badge-fraud {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
    }
    .badge-mid {
        background-color: #FFEDD5;
        color: #9A3412;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
    }
    .badge-genuine {
        background-color: #DCFCE7;
        color: #166534;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Sidebar System Health Status
with st.sidebar:
    st.markdown("## 🛡️ **GraphShield**")
    st.caption("Smart India Hackathon 2026 (SIH26199)\nTeam: **GraphSentinelz**")
    st.markdown("---")

    st.subheader("🔌 System Status")
    health_data, error = api_client.check_health()
    if error:
        st.error("🔴 **Backend API: Offline**")
        st.caption("Could not reach backend API. Is it running?")
    else:
        st.success("🟢 **Backend API: Online**")
        if health_data:
            model_loaded = health_data.get("gnn_model_loaded", False)
            st.info(f"🧠 **GNN Model:** {'Loaded (GraphSAGE)' if model_loaded else 'Fallback Active'}")

    st.markdown("---")
    st.markdown("### 📌 Navigation")
    st.markdown(
        """
        - **1_Dashboard**: System KPIs & Tier Distributions
        - **2_Transaction_Check**: Real-time GNN Risk Evaluator
        - **3_Graph_Explorer**: Multi-Entity Fraud Ring Visualizer
        - **4_Analyst_Review**: Alert Queue & Case Resolutions
        """
    )
    st.markdown("---")
    st.markdown(
        """
        **Risk Tier Rules:**
        - 🔴 **`FRAUD`** (Score ≥ 0.70)
        - 🟠 **`MID_LEVEL`** (0.30 ≤ Score < 0.70)
        - 🟢 **`GENUINE`** (Score < 0.30)
        """
    )

# Main Page Content
st.markdown('<div class="main-header">🛡️ GraphShield: Graph-Based Fraud Detection</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Heterogeneous Graph Neural Network Intelligence for Syndicated Fraud Ring Interception</div>',
    unsafe_allow_html=True,
)

if error:
    render_api_error_if_any(error)
    st.warning(
        """
        **Backend service is currently not detected on `http://127.0.0.1:8000`.**  
        To start the backend, execute:
        ```powershell
        python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
        ```
        Or run `start_all.bat` from the root folder.
        """
    )
else:
    # Quick KPI summary preview
    stats, stats_err = api_client.get_dashboard_stats()
    if stats and not stats_err:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Transactions", f"{stats['total_transactions']:,}")
        c2.metric("🔴 FRAUD Tiers", f"{stats['fraud_count']:,}", f"{stats['fraud_percent']}%")
        c3.metric("🟠 MID_LEVEL Tiers", f"{stats['mid_level_count']:,}", f"{stats['mid_level_percent']}%")
        c4.metric("🟢 GENUINE Tiers", f"{stats['genuine_count']:,}", f"{stats['genuine_percent']}%")

st.markdown("### 🔍 System Architecture Overview")
col_arch1, col_arch2 = st.columns([1.2, 1])

with col_arch1:
    st.markdown(
        """
        **GraphShield** addresses organized financial crime and syndicated account takeovers that evade conventional rules:

        1. **Graph Entity Construction**: Maps accounts, devices, IP subnets, merchants, and transactions into a multi-relational NetworkX graph.
        2. **GraphSAGE Deep Learning**: Evaluates neighborhood embeddings across 2 convolutional hops to uncover accounts sharing device IDs and IP rings.
        3. **Strict 3-Tier Classification**: Categorizes transactions into **`FRAUD`**, **`MID_LEVEL`**, or **`GENUINE`**.
        4. **GNNExplainer Engine**: Translates high-dimensional node aggregations into plain-language bullet points for fraud analysts.
        5. **Human-in-the-Loop Feedback**: Empowers fraud operations teams to confirm syndicate rings or clear false alerts with real-time audit persistence.
        """
    )

with col_arch2:
    st.info(
        """
        **Quick Action Links:**
        - Go to **`1_Dashboard`** to inspect transaction volume, sector distributions, and live tier summaries.
        - Go to **`2_Transaction_Check`** to run a real-time risk check with sample fraud ring payloads.
        - Go to **`3_Graph_Explorer`** to visually inspect device and IP sharing rings.
        - Go to **`4_Analyst_Review`** to triage and resolve flagged alerts.
        """
    )
