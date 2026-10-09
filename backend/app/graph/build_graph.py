"""
GraphShield - NetworkX & PyG Graph Builder
Constructs heterogeneous financial relationship graphs connecting:
Accounts <-> Transactions <-> Devices <-> IPs <-> Merchants <-> PaymentMethods
"""

import networkx as nx
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session

from backend.app.core.data_loader import normalize_dataframe


# Color mapping for Pyvis visualization & node classification
NODE_COLORS = {
    "account": "#1E88E5",        # Blue
    "transaction": "#8E24AA",    # Purple
    "transaction_fraud": "#E53935",    # Red
    "transaction_mid": "#FB8C00",      # Orange
    "transaction_genuine": "#43A047",  # Green
    "device": "#FF7043",         # Coral / Orange-Red
    "ip": "#FDD835",             # Amber / Yellow
    "merchant": "#26A69A",       # Cyan / Teal
    "payment_method": "#78909C", # Blue-Grey
}


def build_networkx_graph_from_df(df: pd.DataFrame) -> nx.Graph:
    """
    Builds a NetworkX graph from a transactions DataFrame.
    """
    G = nx.Graph()
    df = normalize_dataframe(df)  # accepts both legacy and current CSV column names

    for _, row in df.iterrows():
        tx_id = str(row["transaction_id"])
        acct_id = str(row["account_id"])
        dev_id = str(row["device_id"])
        ip_addr = str(row["ip_address"])
        merch_id = str(row["merchant_id"])
        pm_id = str(row.get("payment_method", "UPI"))
        amount = float(row.get("amount", 0.0))
        is_fraud = int(row.get("is_fraud", 0))

        # Add Nodes
        # 1. Transaction Node
        G.add_node(
            tx_id,
            node_type="transaction",
            label=f"TXN: {tx_id[:8]}",
            amount=amount,
            is_fraud=is_fraud,
            color=NODE_COLORS["transaction_fraud"] if is_fraud else NODE_COLORS["transaction_genuine"],
        )

        # 2. Account Node
        if acct_id not in G:
            G.add_node(acct_id, node_type="account", label=f"ACC: {acct_id}", color=NODE_COLORS["account"])

        # 3. Device Node
        if dev_id not in G:
            G.add_node(dev_id, node_type="device", label=f"DEV: {dev_id}", color=NODE_COLORS["device"])

        # 4. IP Node
        if ip_addr not in G:
            G.add_node(ip_addr, node_type="ip", label=f"IP: {ip_addr}", color=NODE_COLORS["ip"])

        # 5. Merchant Node
        if merch_id not in G:
            G.add_node(merch_id, node_type="merchant", label=f"MERCH: {merch_id}", color=NODE_COLORS["merchant"])

        # 6. Payment Method Node
        if pm_id not in G:
            G.add_node(pm_id, node_type="payment_method", label=f"PM: {pm_id}", color=NODE_COLORS["payment_method"])

        # Add Edges
        G.add_edge(acct_id, tx_id, relation="TRANSACTED")
        G.add_edge(tx_id, dev_id, relation="USED_DEVICE")
        G.add_edge(tx_id, ip_addr, relation="FROM_IP")
        G.add_edge(tx_id, merch_id, relation="TO_MERCHANT")
        G.add_edge(tx_id, pm_id, relation="PAID_WITH")

    return G


def convert_nx_to_pyg_data(G: nx.Graph) -> Tuple[Any, Dict[str, int]]:
    """
    Transforms NetworkX graph to a PyTorch Geometric Data object with node features.
    """
    # torch / PyG are imported lazily so the API can run without them (graph explorer only needs the DB)
    import torch
    from torch_geometric.data import Data

    node_list = list(G.nodes())
    node_to_idx = {node: idx for idx, node in enumerate(node_list)}
    num_nodes = len(node_list)

    # Calculate graph topological metrics
    degree_dict = dict(G.degree())

    # Build node feature vectors (8 dimensions)
    # [is_tx, is_acct, is_dev, is_ip, is_merch, is_pm, normalized_degree, normalized_amount]
    node_features = np.zeros((num_nodes, 8), dtype=np.float32)
    labels = np.zeros(num_nodes, dtype=np.int64)
    train_mask = np.zeros(num_nodes, dtype=bool)

    max_deg = max(degree_dict.values()) if degree_dict else 1.0

    for idx, node in enumerate(node_list):
        n_data = G.nodes[node]
        n_type = n_data.get("node_type", "unknown")
        deg = degree_dict.get(node, 0) / max_deg
        amt = float(n_data.get("amount", 0.0)) / 10000.0  # normalized

        if n_type == "transaction":
            node_features[idx, 0] = 1.0
            node_features[idx, 7] = amt
            labels[idx] = n_data.get("is_fraud", 0)
            train_mask[idx] = True
        elif n_type == "account":
            node_features[idx, 1] = 1.0
        elif n_type == "device":
            node_features[idx, 2] = 1.0
        elif n_type == "ip":
            node_features[idx, 3] = 1.0
        elif n_type == "merchant":
            node_features[idx, 4] = 1.0
        elif n_type == "payment_method":
            node_features[idx, 5] = 1.0

        node_features[idx, 6] = deg

    # Build Edge Index (bidirectional)
    edge_list = []
    for u, v in G.edges():
        u_idx = node_to_idx[u]
        v_idx = node_to_idx[v]
        edge_list.append([u_idx, v_idx])
        edge_list.append([v_idx, u_idx])

    if edge_list:
        edge_index = torch.tensor(edge_list, dtype=torch.long).t().contiguous()
    else:
        edge_index = torch.empty((2, 0), dtype=torch.long)

    x = torch.tensor(node_features, dtype=torch.float)
    y = torch.tensor(labels, dtype=torch.long)
    mask = torch.tensor(train_mask, dtype=torch.bool)

    pyg_data = Data(x=x, edge_index=edge_index, y=y, train_mask=mask)
    return pyg_data, node_to_idx


def get_entity_subgraph_data(
    entity_id: str,
    depth: int = 2,
    max_neighbors: int = 60,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """
    Extracts real relationship data from DB transactions centered around entity_id.
    Constructs an ego subgraph formatted for Pyvis visualization.
    """
    from backend.app.models.db_models import Transaction
    from sqlalchemy import or_

    if db is None:
        from backend.app.core.db import SessionLocal
        db = SessionLocal()
        should_close = True
    else:
        should_close = False

    try:
        # Step 1: Find 1st-hop transactions directly touching entity_id
        q1 = (
            db.query(Transaction)
            .filter(
                or_(
                    Transaction.account_id == entity_id,
                    Transaction.device_id == entity_id,
                    Transaction.ip_address == entity_id,
                    Transaction.merchant_id == entity_id,
                    Transaction.transaction_id == entity_id,
                )
            )
            .limit(max_neighbors)
            .all()
        )

        if not q1:
            return {"nodes": [], "edges": [], "summary": {}}

        transactions = list(q1)

        # Step 2: If depth >= 2, find secondary transactions sharing the same devices or IPs
        if depth >= 2 and len(transactions) < max_neighbors:
            devices_in_1st_hop = {tx.device_id for tx in transactions}
            ips_in_1st_hop = {tx.ip_address for tx in transactions}
            accounts_in_1st_hop = {tx.account_id for tx in transactions}

            q2 = (
                db.query(Transaction)
                .filter(
                    or_(
                        Transaction.device_id.in_(devices_in_1st_hop),
                        Transaction.ip_address.in_(ips_in_1st_hop),
                        Transaction.account_id.in_(accounts_in_1st_hop),
                    )
                )
                .limit(max_neighbors)
                .all()
            )
            existing_tx_ids = {tx.transaction_id for tx in transactions}
            for tx in q2:
                if tx.transaction_id not in existing_tx_ids and len(transactions) < max_neighbors:
                    transactions.append(tx)
                    existing_tx_ids.add(tx.transaction_id)

        # Build nodes and edges dictionaries
        nodes_dict = {}
        edges_list = []

        def add_node(n_id: str, n_type: str, label: str, color: str, title: str, size: int = 18):
            if n_id not in nodes_dict:
                is_target = (n_id.strip() == entity_id.strip())
                nodes_dict[n_id] = {
                    "id": n_id,
                    "label": label,
                    "group": n_type,
                    "color": "#D50000" if is_target else color,
                    "shape": "diamond" if is_target else ("dot" if n_type != "transaction" else "box"),
                    "size": 32 if is_target else size,
                    "title": title + (" [TARGET ENTITY]" if is_target else ""),
                }

        account_set = set()
        device_set = set()
        ip_set = set()
        fraud_tx_count = 0

        for tx in transactions:
            tx_id = tx.transaction_id
            acct_id = tx.account_id
            dev_id = tx.device_id
            ip_id = tx.ip_address
            merch_id = tx.merchant_id

            account_set.add(acct_id)
            device_set.add(dev_id)
            ip_set.add(ip_id)

            if tx.decision == "FRAUD":
                tx_color = NODE_COLORS["transaction_fraud"]
                fraud_tx_count += 1
            elif tx.decision == "MID_LEVEL":
                tx_color = NODE_COLORS["transaction_mid"]
            else:
                tx_color = NODE_COLORS["transaction_genuine"]

            # Add entity nodes
            add_node(
                tx_id,
                "transaction",
                f"TXN\n₹{tx.amount:.0f}",
                tx_color,
                f"Transaction ID: {tx_id}<br>Amount: {tx.currency} {tx.amount}<br>Decision: {tx.decision}<br>Score: {tx.risk_score:.2f}",
                size=22,
            )
            add_node(
                acct_id,
                "account",
                f"ACC\n{acct_id[-6:]}",
                NODE_COLORS["account"],
                f"Account: {acct_id}",
                size=20,
            )
            add_node(
                dev_id,
                "device",
                f"DEV\n{dev_id[-6:]}",
                NODE_COLORS["device"],
                f"Device: {dev_id}",
                size=18,
            )
            add_node(
                ip_id,
                "ip",
                f"IP\n{ip_id}",
                NODE_COLORS["ip"],
                f"IP Address: {ip_id}",
                size=16,
            )
            add_node(
                merch_id,
                "merchant",
                f"MERCH\n{merch_id[-6:]}",
                NODE_COLORS["merchant"],
                f"Merchant: {merch_id} ({tx.sector})",
                size=18,
            )

            # Add connecting edges
            edges_list.append({"from": acct_id, "to": tx_id, "label": "TRANSACTED", "color": "#90CAF9"})
            edges_list.append({"from": tx_id, "to": dev_id, "label": "USED_DEVICE", "color": "#FFAB91"})
            edges_list.append({"from": tx_id, "to": ip_id, "label": "FROM_IP", "color": "#FFF59D"})
            edges_list.append({"from": tx_id, "to": merch_id, "label": "TO_MERCHANT", "color": "#80CBC4"})

        return {
            "entity_id": entity_id,
            "nodes": list(nodes_dict.values()),
            "edges": edges_list,
            "summary": {
                "total_nodes": len(nodes_dict),
                "total_edges": len(edges_list),
                "connected_accounts": len(account_set),
                "connected_devices": len(device_set),
                "connected_ips": len(ip_set),
                "fraud_transactions_in_cluster": fraud_tx_count,
            },
        }
    finally:
        if should_close:
            db.close()
