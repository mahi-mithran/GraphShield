"""
GraphShield - Pydantic Request & Response Schemas
Enforces strict 3-tier decision validation: ['FRAUD', 'MID_LEVEL', 'GENUINE']
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Literal
from datetime import datetime


DecisionTier = Literal["FRAUD", "MID_LEVEL", "GENUINE"]


class TransactionPredictRequest(BaseModel):
    """Payload for real-time transaction risk evaluation."""
    transaction_id: Optional[str] = Field(None, description="Optional unique transaction ID")
    account_id: str = Field(..., description="Source account identifier, e.g. ACC-1002")
    user_id: Optional[str] = Field(None, description="User identifier, e.g. USR-1002")
    amount: float = Field(..., gt=0, description="Transaction amount")
    currency: str = Field("INR", description="Currency code (e.g. INR, USD)")
    merchant_id: str = Field(..., description="Merchant identifier, e.g. MERCH-RETAIL-01")
    merchant_name: Optional[str] = Field(None, description="Merchant display name")
    sector: str = Field("Retail", description="Business sector: Finance, Retail, Entertainment, Travel, Tech")
    device_id: str = Field(..., description="Device unique fingerprint ID, e.g. DEV-ANDROID-9871")
    ip_address: str = Field(..., description="Client IP address, e.g. 192.168.1.45")
    payment_method: str = Field("UPI", description="Payment method: UPI, CreditCard, NetBanking, DebitCard")
    timestamp: Optional[datetime] = Field(None, description="Transaction timestamp (UTC)")


class TransactionPredictionResponse(BaseModel):
    """
    Response schema for POST /risk/predict.
    Decision field strictly limited to: FRAUD, MID_LEVEL, GENUINE.
    """
    transaction_id: str
    account_id: str
    amount: float
    currency: str
    sector: str
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Risk probability [0.0 - 1.0]")
    decision: DecisionTier = Field(
        ...,
        description="Strict 3-tier classification: 'FRAUD' (>=0.7), 'MID_LEVEL' (0.3-0.69), or 'GENUINE' (<0.3)",
    )
    reasons: List[str] = Field(
        default_factory=list,
        description="Plain-language explainability bullet points from GNNExplainer / risk engine",
    )
    status: str = Field("PENDING_REVIEW", description="Workflow audit status")
    timestamp: datetime

    @field_validator("decision")
    @classmethod
    def validate_decision_tier(cls, v: str) -> str:
        valid_tiers = {"FRAUD", "MID_LEVEL", "GENUINE"}
        if v not in valid_tiers:
            raise ValueError(f"Decision must be one of {valid_tiers}, got: {v}")
        return v


class TransactionListItem(BaseModel):
    """Schema for transaction listings and flagged alert tables."""
    id: int
    transaction_id: str
    account_id: str
    merchant_id: str
    device_id: str
    ip_address: str
    payment_method_id: str
    amount: float
    currency: str
    sector: str
    timestamp: datetime
    risk_score: float
    decision: DecisionTier
    status: str

    class Config:
        from_attributes = True


class AnalystFeedbackRequest(BaseModel):
    """Request payload for analyst review action."""
    transaction_id: str
    action: Literal["Confirm Fraud", "Verify User", "Reject Alert"]
    analyst_id: Optional[str] = "analyst_agent_1"
    notes: Optional[str] = "Reviewed via GraphShield Analyst Console"


class AnalystFeedbackResponse(BaseModel):
    """Response payload for analyst review submission."""
    success: bool
    transaction_id: str
    action: str
    new_status: str
    decision: str
    message: str


class DashboardStatsResponse(BaseModel):
    """Aggregated statistics for 1_Dashboard."""
    total_transactions: int
    fraud_count: int
    fraud_percent: float
    mid_level_count: int
    mid_level_percent: float
    genuine_count: int
    genuine_percent: float
    sector_distribution: Dict[str, int]
    decision_distribution: Dict[str, int]
