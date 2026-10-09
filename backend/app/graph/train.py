"""
GraphShield - GraphSAGE GNN Training Script
Run from the project root:   python -m backend.app.graph.train

Trains FraudGraphSAGE model on synthetic transaction graph,
evaluates fraud detection accuracy, and exports checkpoint to processed/.
"""

import os
import json
import torch
import torch.nn as nn
import torch.optim as optim
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

from backend.app.core.config import settings
from backend.app.core.data_loader import load_transactions_df
from backend.app.graph.gnn_model import FraudGraphSAGE
from backend.app.graph.build_graph import build_networkx_graph_from_df, convert_nx_to_pyg_data


def train_gnn_model(
    epochs: int = 50,
    learning_rate: float = 0.01,
    weight_decay: float = 5e-4,
):
    print("=" * 65)
    print("GraphShield - GraphSAGE Fraud Classifier Training")
    print("Smart India Hackathon 2026 (SIH26199) - Team GraphSentinelz")
    print("=" * 65)

    csv_path = settings.DATASET_CSV_PATH
    print(f"[1/5] Loading labeled transaction data from: {csv_path}")
    df = load_transactions_df(csv_path)  # generates / normalizes the CSV if needed
    total_tx = len(df)
    fraud_tx = int(df["is_fraud"].sum())
    fraud_rate = (fraud_tx / total_tx) * 100
    print(f"       Total Transactions: {total_tx:,} | Fraud Ring Cases: {fraud_tx:,} ({fraud_rate:.2f}%)")

    # Step 2: Build Multi-Entity Graph
    print("[2/5] Building NetworkX multi-entity graph and PyTorch Geometric tensors...")
    G = build_networkx_graph_from_df(df)
    print(f"       Graph Topology: {G.number_of_nodes():,} nodes | {G.number_of_edges():,} edges")

    pyg_data, node_to_idx = convert_nx_to_pyg_data(G)

    # Step 3: Train/Test Split on Transaction Nodes
    tx_indices = [idx for idx, val in enumerate(pyg_data.train_mask) if val.item() is True]
    tx_labels = pyg_data.y[tx_indices].numpy()

    train_idx, test_idx = train_test_split(
        tx_indices,
        test_size=0.25,
        random_state=42,
        stratify=tx_labels,
    )

    train_mask = torch.zeros(pyg_data.num_nodes, dtype=torch.bool)
    test_mask = torch.zeros(pyg_data.num_nodes, dtype=torch.bool)
    train_mask[train_idx] = True
    test_mask[test_idx] = True

    # Handle class imbalance with weighted loss
    fraud_weight = (len(train_idx) - sum(tx_labels)) / max(1, sum(tx_labels))
    class_weights = torch.tensor([1.0, float(fraud_weight)], dtype=torch.float)

    # Step 4: Model Initialization
    in_features = pyg_data.x.shape[1]
    model = FraudGraphSAGE(in_channels=in_features, hidden_channels=64, out_channels=32)
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = optim.Adam(model.parameters(), lr=learning_rate, weight_decay=weight_decay)

    print(f"[3/5] Starting GraphSAGE optimization for {epochs} epochs...")
    model.train()
    for epoch in range(1, epochs + 1):
        optimizer.zero_grad()
        logits = model(pyg_data.x, pyg_data.edge_index)
        loss = criterion(logits[train_mask], pyg_data.y[train_mask])
        loss.backward()
        optimizer.step()

        if epoch % 10 == 0 or epoch == 1:
            preds = logits[train_mask].argmax(dim=-1).cpu().numpy()
            targets = pyg_data.y[train_mask].cpu().numpy()
            train_acc = accuracy_score(targets, preds) * 100
            print(f"       Epoch {epoch:02d}/{epochs:02d} - Loss: {loss.item():.4f} - Train Acc: {train_acc:.2f}%")

    # Step 5: Evaluation on Held-Out Test Set
    print("[4/5] Evaluating FraudGraphSAGE model on test set...")
    model.eval()
    with torch.no_grad():
        test_logits = model(pyg_data.x, pyg_data.edge_index)
        test_probs = torch.softmax(test_logits, dim=-1)[:, 1][test_mask].cpu().numpy()
        test_preds = test_logits[test_mask].argmax(dim=-1).cpu().numpy()
        test_targets = pyg_data.y[test_mask].cpu().numpy()

    acc = accuracy_score(test_targets, test_preds) * 100
    prec = precision_score(test_targets, test_preds, zero_division=0) * 100
    rec = recall_score(test_targets, test_preds, zero_division=0) * 100
    f1 = f1_score(test_targets, test_preds, zero_division=0) * 100
    try:
        auc = roc_auc_score(test_targets, test_probs) * 100
    except Exception:
        auc = 0.0

    print("-" * 65)
    print(f"       Test Accuracy:  {acc:.2f}%")
    print(f"       Precision:      {prec:.2f}%")
    print(f"       Recall:         {rec:.2f}%")
    print(f"       F1-Score:       {f1:.2f}%")
    print(f"       ROC-AUC:        {auc:.2f}%")
    print("-" * 65)

    # Step 6: Save Model Checkpoint & Metadata
    os.makedirs(settings.PROCESSED_DATA_DIR, exist_ok=True)
    checkpoint_path = settings.MODEL_CHECKPOINT_PATH
    torch.save(model.state_dict(), checkpoint_path)
    print(f"[5/5] Model checkpoint successfully saved to:\n       -> {checkpoint_path}")

    metadata = {
        "model_name": "FraudGraphSAGE",
        "in_channels": in_features,
        "hidden_channels": 64,
        "out_channels": 32,
        "test_accuracy": round(acc, 2),
        "test_precision": round(prec, 2),
        "test_recall": round(rec, 2),
        "test_f1": round(f1, 2),
        "test_roc_auc": round(auc, 2),
        "risk_thresholds": {
            "FRAUD": settings.RISK_THRESHOLD_FRAUD,
            "MID_LEVEL": settings.RISK_THRESHOLD_MID,
            "GENUINE": f"<{settings.RISK_THRESHOLD_MID}",
        },
    }
    with open(settings.MODEL_METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)

    print("GNN Training and Model Checkpoint export complete!")
    return metadata


if __name__ == "__main__":
    train_gnn_model()
