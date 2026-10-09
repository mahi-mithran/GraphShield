"""
GraphShield - Real-Time Transaction Risk Evaluation
Page 2: 2_Transaction_Check.py
Requirements:
  - Form to submit a transaction
  - Displays risk score, prominent decision tier (FRAUD/MID_LEVEL/GENUINE) with matching color
  - Displays explainability reasons as bullet points
  - Graceful connection error handling: 'Could not reach backend API. Is it running?'
"""

import sys
from pathlib import Path

# Make the project root importable so `from frontend.components...` works
# no matter where / how Streamlit is launched (fixes ModuleNotFoundError: No module named 'frontend').
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from datetime import datetime
from frontend.components.api_client import api_client, render_api_error_if_any

st.set_page_config(page_title="GraphShield - Real-Time Risk Evaluator", page_icon="⚡", layout="wide")

st.title("⚡ Real-Time Transaction Risk Evaluator")
st.caption("Submit transactions to the GraphSAGE neural model and inspect explainable graph decisions.")

# Preset Scenarios for quick testing and SIH Hackathon demonstration
scenarios = {
    "Custom Input": {
        "account_id": "ACC-GEN-0100",
        "amount": 2450.00,
        "currency": "INR",
        "merchant_id": "MERCH-AMAZ-01",
        "merchant_name": "Amazon India",
        "sector": "Retail",
        "device_id": "DEV-GEN-0100",
        "ip_address": "10.0.12.44",
        "payment_method": "UPI",
    },
    "🚨 Fraud Ring Syndicate (Known Device & IP Reuse)": {
        "account_id": "ACC-FRAUD-RING-01-2",
        "amount": 48500.00,
        "currency": "INR",
        "merchant_id": "MERCH-CROMA-11",
        "merchant_name": "Croma Electronics",
        "sector": "Electronics",
        "device_id": "DEV-FRAUD-RING-01",
        "ip_address": "198.51.100.10",
        "payment_method": "CreditCard",
    },
    "⚠️ Mid-Level Velocity Outlier (Step-Up Review Required)": {
        "account_id": "ACC-GEN-0842",
        "amount": 16500.00,
        "currency": "INR",
        "merchant_id": "MERCH-MMTR-07",
        "merchant_name": "MakeMyTrip Flights",
        "sector": "Travel",
        "device_id": "DEV-GEN-0842",
        "ip_address": "10.0.88.19",
        "payment_method": "NetBanking",
    },
    "✅ Legitimate Grocery Purchase (Clean Topology)": {
        "account_id": "ACC-GEN-0025",
        "amount": 420.00,
        "currency": "INR",
        "merchant_id": "MERCH-SWIG-03",
        "merchant_name": "Swiggy Foods",
        "sector": "Retail",
        "device_id": "DEV-GEN-0025",
        "ip_address": "10.0.25.101",
        "payment_method": "UPI",
    },
}

st.subheader("1. Select Demo Scenario or Enter Custom Data")
selected_preset = st.selectbox("Load Pre-Configured Test Profile", list(scenarios.keys()))
default_vals = scenarios[selected_preset]

# Transaction Submission Form
with st.form("tx_prediction_form"):
    col1, col2 = st.columns(2)

    with col1:
        account_id = st.text_input("Account Identifier", value=default_vals["account_id"])
        amount = st.number_input("Amount", min_value=1.0, max_value=1000000.0, value=float(default_vals["amount"]), step=50.0)
        currency = st.selectbox("Currency", ["INR", "USD"], index=0)
        payment_method = st.selectbox(
            "Payment Method",
            ["UPI", "CreditCard", "DebitCard", "NetBanking"],
            index=["UPI", "CreditCard", "DebitCard", "NetBanking"].index(default_vals["payment_method"]),
        )

    with col2:
        merchant_id = st.text_input("Merchant ID", value=default_vals["merchant_id"])
        sector = st.selectbox(
            "Industry Sector",
            ["Retail", "Finance", "Entertainment", "Travel", "Electronics", "Groceries"],
            index=["Retail", "Finance", "Entertainment", "Travel", "Electronics", "Groceries"].index(default_vals["sector"]),
        )
        device_id = st.text_input("Device Fingerprint ID", value=default_vals["device_id"])
        ip_address = st.text_input("Client IP Address", value=default_vals["ip_address"])

    submit_button = st.form_submit_button("🔍 Run GraphShield Risk Analysis", use_container_width=True)

# Process Submission
if submit_button:
    payload = {
        "account_id": account_id.strip(),
        "amount": float(amount),
        "currency": currency,
        "merchant_id": merchant_id.strip(),
        "merchant_name": merchant_id.strip(),
        "sector": sector,
        "device_id": device_id.strip(),
        "ip_address": ip_address.strip(),
        "payment_method": payment_method,
        "timestamp": datetime.utcnow().isoformat(),
    }

    with st.spinner("Analyzing graph structure and neighborhood embeddings..."):
        result, error = api_client.predict_risk(payload)

    if error:
        render_api_error_if_any(error)
    elif result:
        st.markdown("---")
        st.subheader("2. Evaluation Verdict & Risk Assessment")

        decision = result.get("decision", "GENUINE")
        risk_score = result.get("risk_score", 0.0)
        reasons = result.get("reasons", [])
        tx_id = result.get("transaction_id", "N/A")

        # Color-coded prominent display banner
        if decision == "FRAUD":
            banner_color = "#DC2626"   # Red
            badge_bg = "#FEE2E2"
            badge_text = "#991B1B"
            action_desc = "🔴 **HIGH RISK — IMMEDIATE ACTION REQUIRED:** Transaction automatically blocked. Flagged for fraud syndicate investigation."
        elif decision == "MID_LEVEL":
            banner_color = "#EA580C"   # Orange
            badge_bg = "#FFEDD5"
            badge_text = "#9A3412"
            action_desc = "🟠 **MEDIUM RISK — STEP-UP VERIFICATION NEEDED:** Challenge user with 2FA / biometric OTP or route to analyst review."
        else:  # GENUINE
            banner_color = "#16A34A"   # Green
            badge_bg = "#DCFCE7"
            badge_text = "#166534"
            action_desc = "🟢 **LOW RISK — AUTOMATICALLY APPROVED:** Normal baseline transaction. Instant frictionless authorization."

        res_col1, res_col2 = st.columns([1, 2])

        with res_col1:
            # Metric & Badge
            st.metric(label="Calculated Risk Score", value=f"{risk_score:.4f}", help="Scale 0.0 to 1.0")
            st.markdown(
                f"""
                <div style="background-color: {badge_bg}; color: {badge_text}; border: 2px solid {banner_color}; 
                            padding: 14px; border-radius: 8px; text-align: center; font-size: 22px; font-weight: 800; margin-top: 10px;">
                    TIER: {decision}
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.caption(f"Persisted Transaction ID: `{tx_id}`")

        with res_col2:
            st.markdown(
                f"""
                <div style="background-color: #F8FAFC; border-left: 5px solid {banner_color}; padding: 15px; border-radius: 6px;">
                    {action_desc}
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown("#### 🧠 GNN Graph Reasoning & Explainability")
            if reasons:
                for idx, r in enumerate(reasons, 1):
                    st.markdown(f"• **{r}**")
            else:
                st.write("• No anomalous neighborhood patterns detected.")

        st.success(f"✅ Transaction record `{tx_id}` and risk score `{risk_score:.4f}` have been persisted to the database.")
