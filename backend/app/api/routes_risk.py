"""
GraphShield - Risk Engine API Routes
POST /risk/predict -> Runs GNN model/fallback, saves to DB, returns 3-tier classification.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from backend.app.core.db import get_db
from backend.app.models.schema import TransactionPredictRequest, TransactionPredictionResponse
from backend.app.models.db_models import Transaction, Account, Device, Merchant, PaymentMethod
from backend.app.services.risk_engine import evaluate_transaction_risk

router = APIRouter()


@router.post(
    "/predict",
    response_model=TransactionPredictionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Predict transaction fraud risk and persist result to database",
)
def predict_transaction_risk(
    payload: TransactionPredictRequest,
    db: Session = Depends(get_db),
):
    """
    Evaluates a transaction using the GraphSAGE GNN model (or graph heuristic fallback),
    classifies it into exactly one of ['FRAUD', 'MID_LEVEL', 'GENUINE'],
    and MANDATORILY persists the record to the database.
    """
    try:
        # Generate transaction ID if not provided
        tx_id = payload.transaction_id or f"TXN-{uuid.uuid4().hex[:10].upper()}"
        tx_timestamp = payload.timestamp or datetime.utcnow()

        # Run Risk Evaluation (GNN Model or Graph Heuristic fallback)
        risk_score, decision, reasons = evaluate_transaction_risk(
            payload=payload,
            db=db,
        )

        # Determine initial transaction status based on exact 3-tier decision
        if decision == "FRAUD":
            tx_status = "PENDING_REVIEW"
        elif decision == "MID_LEVEL":
            tx_status = "PENDING_REVIEW"
        else:  # "GENUINE"
            tx_status = "AUTO_ALLOWED"

        # Ensure related entities exist in DB for graph relationship navigation
        # 1. Account
        account = db.query(Account).filter(Account.account_id == payload.account_id).first()
        if not account:
            account = Account(
                account_id=payload.account_id,
                user_id=payload.user_id or f"USR-{payload.account_id}",
                account_number=f"ACCT-{payload.account_id}",
            )
            db.add(account)

        # 2. Device
        device = db.query(Device).filter(Device.device_id == payload.device_id).first()
        if not device:
            device = Device(
                device_id=payload.device_id,
                device_type="Mobile/Web",
                os="Android/iOS/Windows",
            )
            db.add(device)

        # 3. Merchant
        merchant = db.query(Merchant).filter(Merchant.merchant_id == payload.merchant_id).first()
        if not merchant:
            merchant = Merchant(
                merchant_id=payload.merchant_id,
                merchant_name=payload.merchant_name or f"Merchant {payload.merchant_id}",
                sector=payload.sector,
            )
            db.add(merchant)

        # 4. Payment Method
        pm = db.query(PaymentMethod).filter(PaymentMethod.payment_method_id == payload.payment_method).first()
        if not pm:
            pm = PaymentMethod(
                payment_method_id=payload.payment_method,
                method_type=payload.payment_method,
            )
            db.add(pm)

        # Save Transaction Record to DB (MANDATORY REQUIREMENT)
        existing_tx = db.query(Transaction).filter(Transaction.transaction_id == tx_id).first()
        if existing_tx:
            # Update existing if re-scored
            existing_tx.risk_score = risk_score
            existing_tx.decision = decision
            existing_tx.status = tx_status
            existing_tx.amount = payload.amount
            existing_tx.currency = payload.currency
            existing_tx.sector = payload.sector
            existing_tx.device_id = payload.device_id
            existing_tx.ip_address = payload.ip_address
            existing_tx.merchant_id = payload.merchant_id
            existing_tx.payment_method_id = payload.payment_method
            db_tx = existing_tx
        else:
            db_tx = Transaction(
                transaction_id=tx_id,
                account_id=payload.account_id,
                merchant_id=payload.merchant_id,
                device_id=payload.device_id,
                ip_address=payload.ip_address,
                payment_method_id=payload.payment_method,
                amount=payload.amount,
                currency=payload.currency,
                sector=payload.sector,
                timestamp=tx_timestamp,
                risk_score=risk_score,
                decision=decision,  # Exactly one of: FRAUD, MID_LEVEL, GENUINE
                status=tx_status,
            )
            db.add(db_tx)

        db.commit()
        db.refresh(db_tx)

        return TransactionPredictionResponse(
            transaction_id=db_tx.transaction_id,
            account_id=db_tx.account_id,
            amount=db_tx.amount,
            currency=db_tx.currency,
            sector=db_tx.sector,
            risk_score=round(risk_score, 4),
            decision=decision,  # MUST be FRAUD, MID_LEVEL, or GENUINE
            reasons=reasons,
            status=db_tx.status,
            timestamp=db_tx.timestamp,
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to evaluate and persist transaction: {str(e)}",
        )
