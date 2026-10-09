"""
GraphShield - Graph Neural Network Architecture
FraudGraphSAGE: 2-layer GraphSAGE (SAGEConv) + MLP classifier for transaction fraud scoring.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import SAGEConv


class FraudGraphSAGE(nn.Module):
    """
    2-Layer GraphSAGE model for detecting syndicated fraud rings and suspicious transaction patterns.
    Uses neighborhood aggregation to capture graph topology (device sharing, IP clustering).
    """

    def __init__(self, in_channels: int = 8, hidden_channels: int = 64, out_channels: int = 32, dropout: float = 0.2):
        super(FraudGraphSAGE, self).__init__()
        # Layer 1: First-hop neighborhood aggregation
        self.conv1 = SAGEConv(in_channels, hidden_channels, aggr="mean")
        self.bn1 = nn.BatchNorm1d(hidden_channels)

        # Layer 2: Second-hop ring/syndicate aggregation
        self.conv2 = SAGEConv(hidden_channels, out_channels, aggr="mean")
        self.bn2 = nn.BatchNorm1d(out_channels)

        # Classifier MLP Head
        self.fc1 = nn.Linear(out_channels, 16)
        self.fc2 = nn.Linear(16, 2)  # Logits for [Genuine (0), Fraud (1)]
        self.dropout = nn.Dropout(p=dropout)

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        """
        Forward pass returning unnormalized log-probabilities.
        """
        # Graph Convolution 1
        x = self.conv1(x, edge_index)
        x = self.bn1(x)
        x = F.relu(x)
        x = self.dropout(x)

        # Graph Convolution 2
        x = self.conv2(x, edge_index)
        x = self.bn2(x)
        x = F.relu(x)
        x = self.dropout(x)

        # MLP Classifier
        x = F.relu(self.fc1(x))
        x = self.dropout(x)
        logits = self.fc2(x)
        return logits

    def predict_proba(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        """
        Returns softmax fraud probability [0.0 - 1.0] for class 1 (Fraud).
        """
        self.eval()
        with torch.no_grad():
            logits = self.forward(x, edge_index)
            probs = F.softmax(logits, dim=-1)
            fraud_probs = probs[:, 1]  # Index 1 is Fraud
        return fraud_probs
