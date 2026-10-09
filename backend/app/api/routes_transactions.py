"""
GraphShield - Transactions & Analyst Feedback API Routes
Endpoints:
  GET /transactions/         - List transactions with pagination & filtering
  GET /transactions/flagged  - List only FRAUD and MID_LEVEL transactions
  POST /transactions/feedback - Submit analyst review actions
  GET /transactions/stats    - Aggregated 3-tier metrics and sector distributions
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional

from backend.app.core.db import get_db
from backend.app.models.db_models import Transaction, AnalystFeedback
from backend.app.models.schema import (
    TransactionListItem,
    AnalystFeedbackRequest,
    AnalystFeedbackResponse,
    DashboardStatsResponse,
)
from backend.app.services.feedback import process_analyst_feedback

router = APIRouter()


@router.get(
    "/",
    response_model=List[TransactionListItem],
    summary="Get paginated list of transactions with optional filters",
)
def get_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    decision: Optional[str] = Query(None, description="Filter by exact tier: FRAUD, MID_LEVEL, or GENUINE"),
    sector: Optional[str] = Query(None, description="Filter by sector"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    db: Session = Depends(get_db),
):
    """Retrieve transactions ordered by timestamp descending."""
    query = db.query(Transaction)

    if decision:
        decision_upper = decision.upper()
        if decision_upper not in ["FRAUD", "MID_LEVEL", "GENUINE"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Decision filter must be one of: 'FRAUD', 'MID_LEVEL', 'GENUINE'",
            )
        query = query.filter(Transaction.decision == decision_upper)

    if sector:
        query = query.filter(Transaction.sector.ilike(f"%{sector}%"))

    if status_filter:
        query = query.filter(Transaction.status == status_filter)

    transactions = query.order_by(desc(Transaction.timestamp)).offset(skip).limit(limit).all()
    return transactions


@router.get(
    "/flagged",
    response_model=List[TransactionListItem],
    summary="Get transactions requiring review (FRAUD and MID_LEVEL)",
)
def get_flagged_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    """
    Returns only transactions classified as 'FRAUD' or 'MID_LEVEL'.
    Sorted so highest risk scores and unresolved alerts appear first.
    """
    query = db.query(Transaction).filter(Transaction.decision.in_(["FRAUD", "MID_LEVEL"]))

    if status_filter:
        query = query.filter(Transaction.status == status_filter)

    flagged = (
        query.order_by(desc(Transaction.risk_score), desc(Transaction.timestamp))
        .offset(skip)
        .limit(limit)
        .all()
    )
    return flagged


@router.get(
    "/stats",
    response_model=DashboardStatsResponse,
    summary="Get aggregated statistics: totals, 3-tier counts/percentages, and sector breakdown",
)
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Computes exact 3-tier metrics and sector distributions for the frontend dashboard."""
    total_tx = db.query(func.count(Transaction.id)).scalar() or 0

    if total_tx == 0:
        return DashboardStatsResponse(
            total_transactions=0,
            fraud_count=0,
            fraud_percent=0.0,
            mid_level_count=0,
            mid_level_percent=0.0,
            genuine_count=0,
            genuine_percent=0.0,
            sector_distribution={},
            decision_distribution={"FRAUD": 0, "MID_LEVEL": 0, "GENUINE": 0},
        )

    # 3-Tier Counts
    fraud_count = db.query(func.count(Transaction.id)).filter(Transaction.decision == "FRAUD").scalar() or 0
    mid_count = db.query(func.count(Transaction.id)).filter(Transaction.decision == "MID_LEVEL").scalar() or 0
    genuine_count = db.query(func.count(Transaction.id)).filter(Transaction.decision == "GENUINE").scalar() or 0

    fraud_pct = round((fraud_count / total_tx) * 100, 2)
    mid_pct = round((mid_count / total_tx) * 100, 2)
    genuine_pct = round((genuine_count / total_tx) * 100, 2)

    # Sector Breakdown
    sector_rows = (
        db.query(Transaction.sector, func.count(Transaction.id))
        .group_by(Transaction.sector)
        .all()
    )
    sector_dist = {str(row[0] or "Unknown"): int(row[1]) for row in sector_rows}

    return DashboardStatsResponse(
        total_transactions=total_tx,
        fraud_count=fraud_count,
        fraud_percent=fraud_pct,
        mid_level_count=mid_count,
        mid_level_percent=mid_pct,
        genuine_count=genuine_count,
        genuine_percent=genuine_pct,
        sector_distribution=sector_dist,
        decision_distribution={
            "FRAUD": fraud_count,
            "MID_LEVEL": mid_count,
            "GENUINE": genuine_count,
        },
    )


@router.post(
    "/feedback",
    response_model=AnalystFeedbackResponse,
    status_code=status.HTTP_200_OK,
    summary="Record analyst action on flagged transaction",
)
def submit_feedback(
    payload: AnalystFeedbackRequest,
    db: Session = Depends(get_db),
):
    """
    Records an analyst action ('Confirm Fraud', 'Verify User', 'Reject Alert'),
    updates the transaction status accordingly, and logs an audit record.
    """
    result = process_analyst_feedback(
        transaction_id=payload.transaction_id,
        action=payload.action,
        analyst_id=payload.analyst_id,
        notes=payload.notes,
        db=db,
    )
    return result
