"""
GraphShield - Pyvis Graph Renderer Component
Color-codes heterogeneous nodes: Accounts, Transactions, Devices, IPs, Merchants.
Renders interactive physics network into Streamlit iframe.
"""

import streamlit as st
import streamlit.components.v1 as components
from pyvis.network import Network


def render_pyvis_network(graph_data: dict, height: str = "560px"):
    """
    Builds and renders an interactive Pyvis Network graph from backend graph response.
    """
    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])

    if not nodes:
        st.info("No graph nodes found for this entity.")
        return

    # Initialize Pyvis Network
    # cdn_resources="in_line" embeds vis-network JS in the HTML; the default "local" mode
    # points to relative lib/ files that cannot load inside Streamlit's iframe (blank graph).
    net = Network(
        height=height,
        width="100%",
        bgcolor="#0F172A",
        font_color="#F8FAFC",
        cdn_resources="in_line",
    )
    
    # Configure smooth physics & interactive controls
    net.force_atlas_2based(
        gravity=-55,
        central_gravity=0.015,
        spring_length=110,
        spring_strength=0.08,
        damping=0.92,
        overlap=0.4,
    )

    # Add Nodes
    for n in nodes:
        net.add_node(
            n_id=n["id"],
            label=n.get("label", n["id"]),
            color=n.get("color", "#94A3B8"),
            shape=n.get("shape", "dot"),
            size=n.get("size", 18),
            title=n.get("title", n["id"]),
        )

    # Add Edges
    for e in edges:
        net.add_edge(
            source=e["from"],
            to=e["to"],
            label=e.get("label", ""),
            color=e.get("color", "#475569"),
            font={"size": 10, "color": "#94A3B8", "align": "top"},
            arrows="to",
        )

    # Build the HTML in memory. (net.save_graph() writes the file with the OS default encoding, which
    # crashes on Windows for non-cp1252 characters, and "local" mode also litters a lib/ folder.)
    html_content = net.generate_html()

    # Display Pyvis interactive graph in Streamlit
    components.html(html_content, height=int(str(height).replace("px", "")) + 20, scrolling=False)


def render_graph_legend():
    """Renders visual color legend for graph entity types."""
    st.markdown(
        """
        <div style="display: flex; flex-wrap: wrap; gap: 15px; background-color: #1E293B; padding: 12px 18px; border-radius: 8px; margin-bottom: 15px; font-size: 13px; color: white;">
            <div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background-color:#1E88E5;margin-right:6px;"></span><b>Account</b></div>
            <div><span style="display:inline-block;width:12px;height:12px;border-radius:2px;background-color:#E53935;margin-right:6px;"></span><b>FRAUD Txn</b></div>
            <div><span style="display:inline-block;width:12px;height:12px;border-radius:2px;background-color:#FB8C00;margin-right:6px;"></span><b>MID_LEVEL Txn</b></div>
            <div><span style="display:inline-block;width:12px;height:12px;border-radius:2px;background-color:#43A047;margin-right:6px;"></span><b>GENUINE Txn</b></div>
            <div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background-color:#FF7043;margin-right:6px;"></span><b>Device</b></div>
            <div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background-color:#FDD835;margin-right:6px;"></span><b>IP Address</b></div>
            <div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background-color:#26A69A;margin-right:6px;"></span><b>Merchant</b></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
