"""
GraphShield - Synthetic Transaction Dataset Generator
Smart India Hackathon 2026 (SIH26199) - Team GraphSentinelz

Generates ~5,000 realistic transactions with ~8% fraud rate.
Features syndicated fraud rings: ~5 accounts sharing single device_id and ip_address.
Legitimate accounts have distinct devices and IPs across Finance, Retail, Entertainment, Travel.
"""

import os
import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# Set fixed seed for reproducibility
random.seed(42)
np.random.seed(42)

SECTORS = ["Finance", "Retail", "Entertainment", "Travel", "Electronics", "Groceries"]
PAYMENT_METHODS = ["UPI", "CreditCard", "DebitCard", "NetBanking"]
CURRENCIES = ["INR"]

MERCHANTS = [
    {"id": "MERCH-AMAZ-01", "name": "Amazon India", "sector": "Retail"},
    {"id": "MERCH-FLIP-02", "name": "Flipkart Retail", "sector": "Retail"},
    {"id": "MERCH-SWIG-03", "name": "Swiggy Foods", "sector": "Retail"},
    {"id": "MERCH-ZOMA-04", "name": "Zomato Dine", "sector": "Retail"},
    {"id": "MERCH-BOOK-05", "name": "BookMyShow", "sector": "Entertainment"},
    {"id": "MERCH-NETF-06", "name": "Netflix Digital", "sector": "Entertainment"},
    {"id": "MERCH-MMTR-07", "name": "MakeMyTrip Flights", "sector": "Travel"},
    {"id": "MERCH-IRCT-08", "name": "IRCTC Rail", "sector": "Travel"},
    {"id": "MERCH-ZEROD-09", "name": "Zerodha Broking", "sector": "Finance"},
    {"id": "MERCH-GROWW-10", "name": "Groww Mutual Funds", "sector": "Finance"},
    {"id": "MERCH-CROMA-11", "name": "Croma Electronics", "sector": "Electronics"},
    {"id": "MERCH-RELI-12", "name": "Reliance Digital", "sector": "Electronics"},
]


def generate_synthetic_transactions(
    total_transactions: int = 5000,
    fraud_rate: float = 0.08,  # ~8% fraud rate
    output_path: str = None,
) -> pd.DataFrame:
    """
    Generates synthetic transaction dataset with deliberate graph syndicate fraud rings.
    """
    print(f"Generating synthetic financial dataset ({total_transactions} transactions)...")
    
    num_fraud = int(total_transactions * fraud_rate)
    num_genuine = total_transactions - num_fraud
    
    # 1. Build Fraud Rings (rings of ~5 accounts sharing 1 device and 1 IP)
    accounts_per_ring = 5
    num_rings = max(1, num_fraud // (accounts_per_ring * 3))  # each account does 3 fraud txs
    fraud_rings = []
    
    for r in range(num_rings):
        ring_dev_id = f"DEV-FRAUD-RING-{r+1:02d}"
        ring_ip = f"198.51.100.{10 + r}"
        ring_accounts = [f"ACC-FRAUD-RING-{r+1:02d}-{a+1}" for a in range(accounts_per_ring)]
        fraud_rings.append({
            "device_id": ring_dev_id,
            "ip_address": ring_ip,
            "accounts": ring_accounts,
        })
    
    records = []
    base_time = datetime.utcnow() - timedelta(days=30)
    tx_counter = 1

    # --- Generate Fraud Transactions (Syndicated Rings) ---
    for _ in range(num_fraud):
        ring = random.choice(fraud_rings)
        account_id = random.choice(ring["accounts"])
        device_id = ring["device_id"]
        ip_addr = ring["ip_address"]
        merchant = random.choice(MERCHANTS)
        
        # Fraud transactions tend to have high or repetitive amounts
        if random.random() < 0.65:
            amount = round(random.uniform(15000.0, 75000.0), 2)
        else:
            amount = round(random.uniform(4999.0, 12000.0), 2)
            
        timestamp = base_time + timedelta(
            minutes=random.randint(1, 30 * 24 * 60),
            seconds=random.randint(0, 59),
        )
        
        # Realistic fraud risk score in the FRAUD corridor [0.70 - 0.98]
        risk_score = round(random.uniform(0.72, 0.96), 4)

        records.append({
            "transaction_id": f"TXN-F{tx_counter:06d}",
            "user_id": f"USR-{account_id}",
            "account_id": account_id,
            "amount": amount,
            "currency": "INR",
            "merchant_id": merchant["id"],
            "merchant_name": merchant["name"],
            "sector": merchant["sector"],
            "device_id": device_id,
            "ip_address": ip_addr,
            "payment_method": random.choice(PAYMENT_METHODS),
            "timestamp": timestamp.isoformat(),
            "risk_score": risk_score,
            "is_fraud": 1,
        })
        tx_counter += 1

    # --- Generate Legitimate Transactions (Unique Devices & IPs) ---
    # Create ~1,200 unique accounts with 1-8 transactions each
    num_legit_accounts = 1200
    legit_entities = []
    for a in range(num_legit_accounts):
        acct_id = f"ACC-GEN-{a+1:04d}"
        dev_id = f"DEV-GEN-{a+1:04d}"
        ip_addr = f"10.0.{random.randint(1, 250)}.{random.randint(2, 254)}"
        legit_entities.append({"account_id": acct_id, "device_id": dev_id, "ip_address": ip_addr})

    for _ in range(num_genuine):
        entity = random.choice(legit_entities)
        merchant = random.choice(MERCHANTS)

        # Standard everyday spending distribution
        if random.random() < 0.85:
            amount = round(random.uniform(50.0, 3500.0), 2)
        else:
            amount = round(random.uniform(3500.0, 15000.0), 2)

        timestamp = base_time + timedelta(
            minutes=random.randint(1, 30 * 24 * 60),
            seconds=random.randint(0, 59),
        )

        # 95% genuine (<0.30), 5% borderline mid-level [0.30 - 0.65] for step-up verification
        if random.random() < 0.93:
            risk_score = round(random.uniform(0.01, 0.25), 4)
        else:
            risk_score = round(random.uniform(0.32, 0.62), 4)

        records.append({
            "transaction_id": f"TXN-G{tx_counter:06d}",
            "user_id": f"USR-{entity['account_id']}",
            "account_id": entity["account_id"],
            "amount": amount,
            "currency": "INR",
            "merchant_id": merchant["id"],
            "merchant_name": merchant["name"],
            "sector": merchant["sector"],
            "device_id": entity["device_id"],
            "ip_address": entity["ip_address"],
            "payment_method": random.choice(PAYMENT_METHODS),
            "timestamp": timestamp.isoformat(),
            "risk_score": risk_score,
            "is_fraud": 0,
        })
        tx_counter += 1

    df = pd.DataFrame(records)
    # Shuffle dataframe
    df = df.sample(frac=1.0, random_state=42).reset_index(drop=True)

    # Determine default destination paths
    if output_path is None:
        base_dir = Path(__file__).resolve().parent.parent.parent
        processed_dir = base_dir / "data" / "processed"
        os.makedirs(processed_dir, exist_ok=True)
        output_path = str(processed_dir / "transactions_labeled.csv")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Generated {len(df)} transactions -> Saved to: {output_path}")
    print(f"Fraud Rate: {df['is_fraud'].sum()} / {len(df)} ({df['is_fraud'].mean()*100:.2f}%)")

    return df


if __name__ == "__main__":
    generate_synthetic_transactions()
