"""
GraphShield - Analyst Feedback Service
Processes analyst review decisions, persists feedback audit logs, and updates transaction states.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from backend.app.models.db_models import Transaction, AnalystFeedback
from backend.app.models.schema import AnalystFeedbackResponse


def process_analyst_feedback(
    transaction_id: str,
    action: str,
    analyst_id: str,
    notes: str,
    db: Session,
) -> AnalystFeedbackResponse:
    """
    Applies analyst verdict to a transaction:
      - 'Confirm Fraud': Marks status 'CONFIRMED_FRAUD', confirms malicious syndicate activity
      - 'Verify User': Marks status 'VERIFIED_USER', clears step-up verification for user
      - 'Reject Alert': Marks status 'REJECTED_ALERT', flagged as false positive
    """
    tx = db.query(Transaction).filter(Transaction.transaction_id == transaction_id).first()

    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with ID '{transaction_id}' was not found.",
        )

    # Determine updated state based on analyst review
    if action == "Confirm Fraud":
        new_status = "CONFIRMED_FRAUD"
        tx.risk_score = max(tx.risk_score, 0.95)
        # Keep decision consistent with the score (>= 0.70 is always FRAUD)
        tx.decision = "FRAUD"
    elif action == "Verify User":
        new_status = "VERIFIED_USER"
    elif action == "Reject Alert":
        new_status = "REJECTED_ALERT"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action '{action}'. Permitted: 'Confirm Fraud', 'Verify User', 'Reject Alert'",
        )

    tx.status = new_status

    # Record Analyst Feedback in audit log
    feedback_record = AnalystFeedback(
        transaction_id=tx.transaction_id,
        analyst_id=analyst_id or "analyst_agent_1",
        action=action,
        notes=notes or f"Updated status to {new_status}",
        created_at=datetime.utcnow(),
    )
    db.add(feedback_record)
    db.commit()
    db.refresh(tx)

    return AnalystFeedbackResponse(
        success=True,
        transaction_id=tx.transaction_id,
        action=action,
        new_status=new_status,
        decision=tx.decision,  # FRAUD, MID_LEVEL, or GENUINE
        message=f"Transaction {tx.transaction_id} successfully updated to {new_status}.",
    )
