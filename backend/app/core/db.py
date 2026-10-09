"""
GraphShield - Database Connection & Session Management
SQLAlchemy engine, session factory, table initialization, and automatic seeder.
"""

import os
import shutil
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.app.core.config import settings

# Engine configuration (supporting SQLite with multi-threading)
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency to yield database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _schema_is_outdated() -> bool:
    """
    True if the database already has tables whose columns do not match the current models
    (e.g. a graphshield.db created by an older version of the project).
    SQLAlchemy's create_all() never alters existing tables, so an old file makes every query fail
    with 'no such column: transactions.transaction_id'.
    """
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue
        existing_cols = {col["name"] for col in inspector.get_columns(table.name)}
        expected_cols = {col.name for col in table.columns}
        if not expected_cols.issubset(existing_cols):
            return True
    return False


def init_db():
    """Create all registered database tables (rebuilding them if an old schema is detected)."""
    # Ensure processed data directory exists
    os.makedirs(settings.PROCESSED_DATA_DIR, exist_ok=True)
    # Import models here to register metadata
    from backend.app.models import db_models  # noqa

    if _schema_is_outdated():
        print("[DB] Outdated database schema detected - rebuilding tables (old data is not compatible).")
        if engine.url.get_backend_name() == "sqlite" and engine.url.database:
            db_file = engine.url.database
            engine.dispose()
            if os.path.exists(db_file):
                backup_file = f"{db_file}.old_schema.bak"
                shutil.copy2(db_file, backup_file)
                print(f"[DB] Backup of old database saved to: {backup_file}")
        Base.metadata.drop_all(bind=engine)

    Base.metadata.create_all(bind=engine)
    print(f"[DB] Initialized database tables at: {settings.DATABASE_URL}")


def seed_initial_data_if_empty():
    """
    Checks if transactions table is empty. If empty, automatically seeds
    initial transactions from transactions_labeled.csv (or generates it if absent).
    """
    from backend.app.models.db_models import (
        Transaction,
        Account,
        Device,
        Merchant,
        PaymentMethod,
        User,
    )
    from backend.app.services.risk_engine import decide

    db = SessionLocal()
    try:
        count = db.query(Transaction).count()
        if count > 0:
            print(f"[DB] Database already seeded ({count} transactions found).")
            return

        # Loads the CSV (generating it, or replacing a legacy-schema CSV, if needed)
        # and normalizes column names so seeding can never fail on a KeyError.
        from backend.app.core.data_loader import load_transactions_df

        csv_path = settings.DATASET_CSV_PATH
        print(f"[DB] Seeding transactions from {csv_path}...")
        df = load_transactions_df(csv_path)

        # Cache existing entities to avoid duplicate insertion overhead
        seen_accounts = set()
        seen_devices = set()
        seen_merchants = set()
        seen_payment_methods = set()

        batch_tx = []
        for _, row in df.iterrows():
            acct_id = str(row["account_id"])
            dev_id = str(row["device_id"])
            merch_id = str(row["merchant_id"])
            pm_id = str(row["payment_method"])
            tx_id = str(row["transaction_id"])

            if acct_id not in seen_accounts:
                db.add(Account(
                    account_id=acct_id,
                    user_id=str(row.get("user_id", f"USR-{acct_id}")),
                    account_number=f"ACC-{acct_id}",
                ))
                seen_accounts.add(acct_id)

            if dev_id not in seen_devices:
                db.add(Device(
                    device_id=dev_id,
                    device_type="Smartphone/PC",
                    os="Android/iOS/Windows",
                ))
                seen_devices.add(dev_id)

            if merch_id not in seen_merchants:
                db.add(Merchant(
                    merchant_id=merch_id,
                    merchant_name=str(row.get("merchant_name", merch_id)),
                    sector=str(row.get("sector", "Retail")),
                ))
                seen_merchants.add(merch_id)

            if pm_id not in seen_payment_methods:
                db.add(PaymentMethod(
                    payment_method_id=pm_id,
                    method_type=pm_id,
                ))
                seen_payment_methods.add(pm_id)

            # Map raw labels/scores to exact 3 tiers: FRAUD, MID_LEVEL, GENUINE
            is_fraud = int(row.get("is_fraud", 0))
            if is_fraud == 1:
                # Simulated fraud score in high range
                risk_score = float(row.get("risk_score", 0.88))
            else:
                # Normal or borderline
                risk_score = float(row.get("risk_score", 0.08))

            decision = decide(risk_score)
            status = "PENDING_REVIEW" if decision in ["FRAUD", "MID_LEVEL"] else "AUTO_ALLOWED"

            ts_str = str(row.get("timestamp", datetime.utcnow().isoformat()))
            try:
                tx_ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            except Exception:
                tx_ts = datetime.utcnow()

            batch_tx.append(Transaction(
                transaction_id=tx_id,
                account_id=acct_id,
                merchant_id=merch_id,
                device_id=dev_id,
                ip_address=str(row.get("ip_address", "192.168.1.1")),
                payment_method_id=pm_id,
                amount=float(row.get("amount", 100.0)),
                currency=str(row.get("currency", "INR")),
                sector=str(row.get("sector", "Retail")),
                timestamp=tx_ts,
                risk_score=risk_score,
                decision=decision,
                status=status,
            ))

            # Commit periodically
            if len(batch_tx) >= 1000:
                db.flush()
                db.bulk_save_objects(batch_tx)
                db.commit()
                batch_tx = []

        if batch_tx:
            db.flush()
            db.bulk_save_objects(batch_tx)
            db.commit()

        print(f"[DB] Successfully seeded {len(df)} transactions into database.")
    except Exception as e:
        db.rollback()
        print(f"[DB Error] Failed to seed initial database: {e}")
    finally:
        db.close()
