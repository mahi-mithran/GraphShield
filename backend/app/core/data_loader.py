"""
GraphShield - Dataset Loader
Guarantees that the transaction CSV exists and uses the column names the backend expects:

    transaction_id, account_id, merchant_id, device_id, ip_address, amount,
    currency, sector, payment_method, timestamp, is_fraud

An older version of the project shipped a CSV that used different column names
(txn_id, device_fingerprint, payment_type). That file made database seeding and
graph building crash with KeyError, so the DB stayed empty. This module:
  1. renames legacy columns to the current names, and
  2. regenerates the dataset (keeping a backup) when a legacy CSV is found,
     so entity IDs match the demo scenarios (DEV-FRAUD-RING-01, ACC-GEN-0025, ...).
"""

import shutil
from pathlib import Path
from typing import Optional, Union

import pandas as pd

from backend.app.core.config import settings

LEGACY_COLUMN_MAP = {
    "txn_id": "transaction_id",
    "device_fingerprint": "device_id",
    "payment_type": "payment_method",
}

REQUIRED_COLUMNS = [
    "transaction_id",
    "account_id",
    "merchant_id",
    "device_id",
    "ip_address",
    "amount",
]


def is_legacy_schema(columns) -> bool:
    """True if the CSV still uses the old column names."""
    return any(col in columns for col in LEGACY_COLUMN_MAP)


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Rename legacy columns and fill optional columns with safe defaults."""
    df = df.rename(columns=LEGACY_COLUMN_MAP).copy()

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Dataset is missing required columns: {missing}")

    defaults = {
        "currency": "INR",
        "sector": "Retail",
        "payment_method": "UPI",
        "is_fraud": 0,
    }
    for col, value in defaults.items():
        if col not in df.columns:
            df[col] = value

    if "merchant_name" not in df.columns:
        df["merchant_name"] = df["merchant_id"]
    if "user_id" not in df.columns:
        df["user_id"] = "USR-" + df["account_id"].astype(str)
    return df


def ensure_dataset(csv_path: Optional[Union[str, Path]] = None) -> Path:
    """Make sure a valid CSV exists at csv_path (generate it if missing or legacy)."""
    csv_path = Path(csv_path or settings.DATASET_CSV_PATH)
    regenerate = False

    if not csv_path.exists():
        print(f"[Data] Dataset not found at {csv_path}. Generating synthetic dataset...")
        regenerate = True
    else:
        try:
            columns = list(pd.read_csv(csv_path, nrows=0).columns)
            if is_legacy_schema(columns):
                backup = csv_path.with_name(f"{csv_path.stem}_legacy_backup{csv_path.suffix}")
                if not backup.exists():
                    shutil.copy2(csv_path, backup)
                print(f"[Data] Legacy CSV schema detected. Backed up to {backup.name} and regenerating...")
                regenerate = True
        except Exception as exc:  # unreadable / corrupt file
            print(f"[Data] Could not read {csv_path} ({exc}). Regenerating...")
            regenerate = True

    if regenerate:
        from backend.data.raw.generate_dataset import generate_synthetic_transactions

        csv_path.parent.mkdir(parents=True, exist_ok=True)
        generate_synthetic_transactions(output_path=str(csv_path))

    return csv_path


def load_transactions_df(csv_path: Optional[Union[str, Path]] = None) -> pd.DataFrame:
    """Load the dataset with guaranteed, normalized column names."""
    path = ensure_dataset(csv_path)
    return normalize_dataframe(pd.read_csv(path))
