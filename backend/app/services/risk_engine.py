"""
GraphShield - Risk Engine & Decision Service
Maps risk scores to exact 3 tiers: FRAUD (>=0.7), MID_LEVEL (0.3-0.69), GENUINE (<0.3).
Provides GNN model inference with seamless mock/heuristic fallback before model is trained.
"""

import os
import numpy as np
from typing import Tuple, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.core.config import settings
from backend.app.models.schema import TransactionPredictRequest
from backend.app.models.db_models import Transaction
from backend.app.graph.explain import generate_graph_explanations, count_accounts_sharing


def decide(risk_score: float) -> str:
    """
    MANDATORY 3-TIER DECISION RULE:
      risk_score >= 0.70          -> "FRAUD"
      0.30 <= risk_score < 0.70   -> "MID_LEVEL"
      risk_score < 0.30           -> "GENUINE"
    Never returns any other string or binary classification.
    """
    if risk_score >= settings.RISK_THRESHOLD_FRAUD:
        return settings.TIER_FRAUD
    elif risk_score >= settings.RISK_THRESHOLD_MID:
        return settings.TIER_MID_LEVEL
    else:
        return settings.TIER_GENUINE


def mock_score_transaction(
    payload: TransactionPredictRequest,
    db: Optional[Session] = None,
) -> Tuple[float, str, List[str]]:
    """
    Heuristic graph-aware scoring fallback used before the GNN model is trained.
    Calculates structural risk based on device reuse, IP sharing, and sector anomalies.
    """
    score = 0.05  # Base benign baseline

    if db is not None:
        # Distinct accounts on this device / IP (including the account being scored)
        dev_count = count_accounts_sharing(db, Transaction.device_id, payload.device_id, payload.account_id)
        if dev_count >= 3:
            score += 0.50
        elif dev_count == 2:
            score += 0.25

        ip_count = count_accounts_sharing(db, Transaction.ip_address, payload.ip_address, payload.account_id)
        if ip_count >= 4:
            score += 0.30
        elif ip_count >= 2:
            score += 0.15

        # Prior fraud on device or IP
        prior_fraud = (
            db.query(func.count(Transaction.id))
            .filter(
                (Transaction.device_id == payload.device_id) | (Transaction.ip_address == payload.ip_address),
                Transaction.decision == "FRAUD",
            )
            .scalar()
            or 0
        )
        if prior_fraud > 0:
            score += 0.35

    # Sector amount check
    if payload.amount > 50000:
        score += 0.20
    elif payload.amount > 20000:
        score += 0.10

    # Bound score in [0.0, 0.99]
    score = max(0.01, min(0.98, float(score)))
    decision = decide(score)

    reasons = generate_graph_explanations(
        account_id=payload.account_id,
        device_id=payload.device_id,
        ip_address=payload.ip_address,
        amount=payload.amount,
        sector=payload.sector,
        risk_score=score,
        db=db,
    )

    return score, decision, reasons


def evaluate_transaction_risk(
    payload: TransactionPredictRequest,
    db: Session,
) -> Tuple[float, str, List[str]]:
    """
    Main evaluation pipeline:
    Attempts to run the trained PyG FraudGraphSAGE model checkpoint.
    Falls back gracefully to mock_score_transaction if the model file is not yet generated.
    """
    checkpoint_path = settings.MODEL_CHECKPOINT_PATH

    if not os.path.exists(checkpoint_path):
        return mock_score_transaction(payload=payload, db=db)

    try:
        # Imported lazily so the API still starts (heuristic fallback) if torch / PyG are missing
        import torch
        from backend.app.graph.gnn_model import FraudGraphSAGE

        # Load trained weights
        model = FraudGraphSAGE(in_channels=8, hidden_channels=64, out_channels=32)
        model.load_state_dict(torch.load(checkpoint_path, map_location=torch.device("cpu"), weights_only=True))
        model.eval()

        # Construct localized inference graph feature vector for this transaction
        # [is_tx, is_acct, is_dev, is_ip, is_merch, is_pm, normalized_degree, normalized_amount]
        dev_sharing = count_accounts_sharing(db, Transaction.device_id, payload.device_id, payload.account_id)
        ip_sharing = count_accounts_sharing(db, Transaction.ip_address, payload.ip_address, payload.account_id)

        # Degree approximation based on active connections
        estimated_degree = float(dev_sharing + ip_sharing + 2) / 20.0
        normalized_amount = float(payload.amount) / 10000.0  # same scaling as training graph

        # Mini star-graph around transaction
        # Node 0: Transaction, Node 1: Account, Node 2: Device, Node 3: IP, Node 4: Merchant
        node_features = np.zeros((5, 8), dtype=np.float32)
        # Tx node
        node_features[0, 0] = 1.0
        node_features[0, 6] = estimated_degree
        node_features[0, 7] = normalized_amount
        # Acct node
        node_features[1, 1] = 1.0
        # Dev node
        node_features[2, 2] = 1.0
        node_features[2, 6] = float(dev_sharing) / 10.0
        # IP node
        node_features[3, 3] = 1.0
        node_features[3, 6] = float(ip_sharing) / 10.0
        # Merchant node
        node_features[4, 4] = 1.0

        edge_list = [
            [0, 1], [1, 0],
            [0, 2], [2, 0],
            [0, 3], [3, 0],
            [0, 4], [4, 0],
        ]

        x_tensor = torch.tensor(node_features, dtype=torch.float)
        edge_tensor = torch.tensor(edge_list, dtype=torch.long).t().contiguous()

        with torch.no_grad():
            probs = model.predict_proba(x_tensor, edge_tensor)
            model_score = float(probs[0].item())

        # The mini star-graph built above is only an approximation of the full training graph, so the raw
        # GNN probability is not trusted on its own. It is blended with the database graph-evidence score
        # (shared devices / IPs, prior fraud neighbours, amount), which keeps the result stable and explainable.
        evidence_score, _, _ = mock_score_transaction(payload=payload, db=db)
        model_score = 0.85 * evidence_score + 0.15 * model_score

        model_score = max(0.02, min(0.98, model_score))
        decision = decide(model_score)

        reasons = generate_graph_explanations(
            account_id=payload.account_id,
            device_id=payload.device_id,
            ip_address=payload.ip_address,
            amount=payload.amount,
            sector=payload.sector,
            risk_score=model_score,
            db=db,
        )

        return model_score, decision, reasons

    except Exception as e:
        print(f"[Warning] GNN inference fallback triggered due to: {e}")
        return mock_score_transaction(payload=payload, db=db)
