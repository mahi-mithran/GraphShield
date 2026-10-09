"""
GraphShield - SQLAlchemy Database Models
Models: User, Account, Device, Merchant, PaymentMethod, Transaction, AnalystFeedback
"""

from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Text,
    Index,
)
from sqlalchemy.orm import relationship
from backend.app.core.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(128), nullable=True)
    email = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(String(64), unique=True, index=True, nullable=False)
    user_id = Column(String(64), ForeignKey("users.user_id"), nullable=True)
    account_number = Column(String(64), nullable=True)
    balance = Column(Float, default=10000.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account")


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(64), unique=True, index=True, nullable=False)
    device_type = Column(String(64), default="Smartphone")
    os = Column(String(64), default="Android")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    transactions = relationship("Transaction", back_populates="device")


class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(String(64), unique=True, index=True, nullable=False)
    merchant_name = Column(String(128), nullable=False)
    sector = Column(String(64), default="Retail")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    transactions = relationship("Transaction", back_populates="merchant")


class PaymentMethod(Base):
    __tablename__ = "payment_methods"

    id = Column(Integer, primary_key=True, index=True)
    payment_method_id = Column(String(64), unique=True, index=True, nullable=False)
    method_type = Column(String(64), default="UPI")  # UPI, Credit Card, NetBanking, Debit Card
    details = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    transactions = relationship("Transaction", back_populates="payment_method")


class Transaction(Base):
    """
    Financial transaction entity.
    Stores exact 3-tier risk decision: FRAUD, MID_LEVEL, GENUINE.
    """
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String(64), unique=True, index=True, nullable=False)
    account_id = Column(String(64), ForeignKey("accounts.account_id"), index=True, nullable=False)
    merchant_id = Column(String(64), ForeignKey("merchants.merchant_id"), index=True, nullable=False)
    device_id = Column(String(64), ForeignKey("devices.device_id"), index=True, nullable=False)
    ip_address = Column(String(64), index=True, nullable=False)
    payment_method_id = Column(String(64), ForeignKey("payment_methods.payment_method_id"), nullable=False)

    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="INR")
    sector = Column(String(64), default="Retail", index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # MANDATORY THREE-TIER RISK CLASSIFICATION
    # Value MUST be one of: "FRAUD", "MID_LEVEL", "GENUINE"
    risk_score = Column(Float, nullable=False, default=0.0)
    decision = Column(String(20), index=True, nullable=False)  # FRAUD / MID_LEVEL / GENUINE

    # Status tracking for Analyst Review workflow:
    # "AUTO_ALLOWED", "PENDING_REVIEW", "CONFIRMED_FRAUD", "VERIFIED_USER", "REJECTED_ALERT"
    status = Column(String(32), default="PENDING_REVIEW", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    account = relationship("Account", back_populates="transactions")
    merchant = relationship("Merchant", back_populates="transactions")
    device = relationship("Device", back_populates="transactions")
    payment_method = relationship("PaymentMethod", back_populates="transactions")
    feedbacks = relationship("AnalystFeedback", back_populates="transaction", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_tx_decision_status", "decision", "status"),
        Index("idx_tx_account_time", "account_id", "timestamp"),
    )


class AnalystFeedback(Base):
    """
    Audit log of analyst reviews and investigations on flagged transactions.
    """
    __tablename__ = "analyst_feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String(64), ForeignKey("transactions.transaction_id"), index=True, nullable=False)
    analyst_id = Column(String(64), default="analyst_agent_1")
    # Action: "CONFIRM_FRAUD", "VERIFY_USER", "REJECT_ALERT"
    action = Column(String(32), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    transaction = relationship("Transaction", back_populates="feedbacks")
