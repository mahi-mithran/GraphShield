"""
GraphShield - Multi-Entity Graph Visualizer
Page 3: 3_Graph_Explorer.py
Requirements:
  - Input an entity ID (Account, Device, IP, Transaction, Merchant)
  - Render its real relationship graph from the DB/graph using Pyvis
  - Color-coded node types, interactive zoom/drag
  - Real data reflection (not static mock data)
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
from frontend.components.graph_viz import render_pyvis_network, render_graph_legend

st.set_page_config(page_title="GraphShield - Graph Explorer", page_icon="🕸️", layout="wide")

st.title("🕸️ Graph Intelligence & Syndicate Explorer")
st.caption("Visually trace fraud rings, multi-account device sharing, and IP clustering from the live database graph.")

# Sample entity identifiers for testing
sample_entities = [
    "DEV-FRAUD-RING-01",
    "ACC-FRAUD-RING-01-1",
    "198.51.100.10",
    "ACC-GEN-0025",
    "MERCH-CROMA-11",
]

col_in1, col_in2, col_in3 = st.columns([2, 1, 1])

with col_in1:
    entity_input = st.text_input(
        "Enter Entity Identifier (Account, Device, IP, or Merchant)",
        value="DEV-FRAUD-RING-01",
        help="Paste any entity ID from transactions to explore its relational subgraph",
    )

with col_in2:
    depth = st.selectbox("Graph Depth (Hops)", [1, 2, 3], index=1)

with col_in3:
    max_nodes = st.slider("Max Neighbors", min_value=10, max_value=120, value=60, step=10)

st.caption("💡 Quick-fill suggestions: " + " | ".join([f"`{e}`" for e in sample_entities]))

if st.button("🔎 Explore Entity Graph", type="primary", use_container_width=True):
    clean_id = entity_input.strip()
    if not clean_id:
        st.warning("Please enter a valid entity identifier.")
        st.stop()

    with st.spinner(f"Extracting relational subgraph for '{clean_id}' from database..."):
        graph_data, error = api_client.get_graph(clean_id, depth=depth, max_neighbors=max_nodes)

    if error:
        render_api_error_if_any(error)
    elif not graph_data or not graph_data.get("nodes"):
        st.warning(f"No transactions or relationships found connected to '{clean_id}'.")
    else:
        summary = graph_data.get("summary", {})

        # Display Graph Summary Metrics
        st.markdown("### 📊 Subgraph Metrics & Topology")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Total Nodes", summary.get("total_nodes", 0))
        m2.metric("Connected Edges", summary.get("total_edges", 0))
        m3.metric("Distinct Accounts", summary.get("connected_accounts", 0))
        m4.metric("Shared Devices", summary.get("connected_devices", 0))
        m5.metric("🚨 Fraud Tiers in Cluster", summary.get("fraud_transactions_in_cluster", 0))

        if summary.get("connected_accounts", 0) >= 3 and summary.get("connected_devices", 0) <= 2:
            st.error("⚠️ **SYNDICATE ALERT:** Multiple distinct accounts converge onto shared hardware/IP infrastructure (Synthetic Fraud Ring signature).")

        # Visual Legend
        render_graph_legend()

        # Render Interactive Pyvis Network
        render_pyvis_network(graph_data, height="600px")

        # Tabular View of Graph Nodes
        with st.expander("📋 View Subgraph Entities & Attributes"):
            node_rows = [
                {
                    "Node ID": n["id"],
                    "Entity Type": n["group"].upper(),
                    "Display Label": n["label"].replace("\n", " "),
                }
                for n in graph_data.get("nodes", [])
            ]
            st.dataframe(pd.DataFrame(node_rows), use_container_width=True)
