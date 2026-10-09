import streamlit as st
import time
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from frontend.components.api_client import api_client, render_api_error_if_any

st.set_page_config(
    page_title="Live Payment Gateway | GraphShield",
    page_icon="💳",
    layout="wide"
)

# Backend tiers -> checkout actions shown to the customer
TIER_TO_ACTION = {"GENUINE": "ALLOW", "MID_LEVEL": "STEP_UP", "FRAUD": "BLOCK"}

# Radio label -> value sent to the backend `payment_method` field
PAYMENT_LABELS = [
    ("UPI (Google Pay / PhonePe / Paytm)", "UPI"),
    ("Credit / Debit Card", "CreditCard"),
    ("NetBanking", "NetBanking"),
    ("Crypto / Digital Voucher", "Crypto"),
]


def fetch_live_entities() -> dict:
    """Pick real entities from the database for the FRAUD-ring and Step-Up demo presets."""
    found = {}

    # A real member of a fraud ring (device / IP / account shared by several accounts)
    rows, err = api_client.get_transactions(limit=1, decision="FRAUD")
    if not err and rows:
        found["FRAUD"] = rows[0]

    # A real legitimate customer's device, which the Step-Up demo account will "borrow".
    # skip=1000 keeps us away from the newest rows (which may be earlier demo runs).
    for skip in (1000, 0):
        rows, err = api_client.get_transactions(skip=skip, limit=1, decision="GENUINE")
        if not err and rows:
            found["GENUINE"] = rows[0]
            break
    return found


def build_presets(live: dict) -> dict:
    """
    Demo scenarios. Every case keeps its OWN fixed demo account, so running a demo never changes
    the result of another demo. Case 2 / Case 3 reuse real devices from the database so the graph
    signals (shared device / shared IP / neighbouring FRAUD) fire for the right reasons.
    Falls back to synthetic-dataset IDs if the backend has no data yet.
    """
    g = live.get("GENUINE", {})
    f = live.get("FRAUD", {})
    return {
        # Brand-new customer with a private device + IP -> GENUINE
        "case1": {
            "scenario_title": "🟢 Normal Genuine Customer",
            "item_name": "Noise Cancelling Wireless Headphones",
            "merchant": "MERCH-AMAZ-01",
            "sector": "Retail",
            "account_id": "ACC-GEN-DEMO-01",
            "amount": 1499.0,
            "payment_type": "UPI",
            "device_id": "DEV-GEN-DEMO-01",
            "ip_address": "10.0.250.1",
        },
        # Demo account using a device that already belongs to another customer + unusually large amount -> MID_LEVEL
        "case2": {
            "scenario_title": "🟠 Shared Device + Unusual Amount",
            "item_name": "High-End Gaming Laptop",
            "merchant": "MERCH-FLIP-02",
            "sector": "Retail",
            "account_id": "ACC-GEN-DEMO-02",
            "amount": 78999.0,
            "payment_type": "CreditCard",
            "device_id": g.get("device_id", "DEV-GEN-0842"),
            "ip_address": "10.0.250.2",
        },
        # Real fraud-ring device / IP / account from the database -> FRAUD
        "case3": {
            "scenario_title": "🔴 Coordinated Device-Farm Syndicate",
            "item_name": "Electronics Bulk Order (Instant Cashout)",
            "merchant": f.get("merchant_id", "MERCH-CROMA-11"),
            "sector": f.get("sector", "Electronics"),
            "account_id": f.get("account_id", "ACC-FRAUD-RING-01-2"),
            "amount": 42000.0,
            "payment_type": "CreditCard",
            "device_id": f.get("device_id", "DEV-FRAUD-RING-01"),
            "ip_address": f.get("ip_address", "198.51.100.10"),
        },
    }


# Load real entities once per browser session (retry on the next rerun if the backend was offline)
if not st.session_state.get("live_entities"):
    st.session_state.live_entities = fetch_live_entities()
PRESETS = build_presets(st.session_state.live_entities)

# Header & Hackathon Judge Banner
st.markdown("""
<div style="background: linear-gradient(90deg, #1e3a8a 0%, #0f172a 100%); padding: 18px 24px; border-radius: 10px; margin-bottom: 20px; color: white;">
    <h2 style="margin: 0; color: #60a5fa;">💳 GraphShield Live Payment Gateway Demo</h2>
    <p style="margin: 5px 0 0 0; opacity: 0.85; font-size: 14px;">
        <b>Smart India Hackathon 2026</b> | Problem Statement: <b>SIH26199</b> | Team: <b>GraphSentinelz</b><br>
        <i>Interactive checkout portal demonstrating real-time Graph Neural Network (GNN) fraud interception.</i>
    </p>
</div>
""", unsafe_allow_html=True)

# Preset Demo Controls for Presenting to Judges
st.subheader("🎯 Choose a Demonstration Scenario for Judges:")

judge_c1, judge_c2, judge_c3 = st.columns(3)

if "payment_data" not in st.session_state or "device_id" not in st.session_state.payment_data:
    st.session_state.payment_data = dict(PRESETS["case1"])

with judge_c1:
    if st.button("🟢 Case 1: Legitimate Customer (Allow)", use_container_width=True):
        st.session_state.payment_data = dict(PRESETS["case1"])
        st.session_state.pop("last_payment_result", None)
        st.rerun()

with judge_c2:
    if st.button("🟠 Case 2: Shared Device + Big Amount (Step-Up)", use_container_width=True):
        st.session_state.payment_data = dict(PRESETS["case2"])
        st.session_state.pop("last_payment_result", None)
        st.rerun()

with judge_c3:
    if st.button("🔴 Case 3: Fraud Ring Syndicate (Block)", use_container_width=True):
        st.session_state.payment_data = dict(PRESETS["case3"])
        st.session_state.pop("last_payment_result", None)
        st.rerun()

st.markdown("---")

# Main 2-Column Checkout Layout
checkout_col, security_col = st.columns([1.1, 1.2])

data = st.session_state.payment_data

with checkout_col:
    st.markdown("### 🛒 E-Commerce Checkout Screen")
    st.info(f"**Active Demo Scenario:** {data['scenario_title']}")

    with st.container(border=True):
        st.markdown(f"#### Order Summary ({data['merchant']})")
        st.write(f"**Item:** {data['item_name']}")
        st.write(f"**Sector:** `{data['sector']}`")
        st.write(f"**Order Total:** **₹{data['amount']:,.2f} INR**")

        st.markdown("---")
        st.markdown("#### Payment Method")
        payment_labels = [label for label, _ in PAYMENT_LABELS]
        payment_values = [value for _, value in PAYMENT_LABELS]
        default_idx = payment_values.index(data["payment_type"]) if data["payment_type"] in payment_values else 0
        payment_method = st.radio(
            "Select Payment Instrument",
            payment_labels,
            index=default_idx,
            key=f"pm_radio_{data['scenario_title']}",
        )

        st.caption(f"Connected Account: `{data['account_id']}`")
        pay_btn = st.button(f"🔒 Pay ₹{data['amount']:,.2f} Now", type="primary", use_container_width=True)

with security_col:
    st.markdown("### 🛡️ Real-Time GraphShield GNN Telemetry")

    with st.container(border=True):
        st.markdown("#### Device & Network Telemetry Captured by SDK:")
        t_c1, t_c2 = st.columns(2)
        with t_c1:
            st.write(f"**Account ID:** `{data['account_id']}`")
            st.write(f"**Device Fingerprint:** `{data['device_id']}`")
        with t_c2:
            st.write(f"**Originating IP:** `{data['ip_address']}`")
            st.write(f"**Payment Channel:** `{data['payment_type']}`")

    if pay_btn:
        with st.spinner("⚡ GraphShield GNN analyzing 2-hop topological ring relationships..."):
            # Map the selected radio label to the value the backend expects
            pm_mapped = dict(PAYMENT_LABELS).get(payment_method, "UPI")

            payload = {
                "account_id": data["account_id"],
                "merchant_id": data["merchant"],
                "device_id": data["device_id"],          # backend field name is device_id
                "ip_address": data["ip_address"],
                "amount": float(data["amount"]),
                "currency": "INR",
                "sector": data["sector"],
                "payment_method": pm_mapped,             # backend field name is payment_method
            }

            # api_client returns a (data, error) tuple - unpack it
            result, error = api_client.predict_risk(payload)
            st.session_state.last_payment_result = {"result": result, "error": error}

    # Display Payment Result if available
    stored = st.session_state.get("last_payment_result")
    if stored:
        res = stored.get("result")
        if stored.get("error") or not res:
            render_api_error_if_any(stored.get("error") or "No response received from backend.")
        else:
            tier = res.get("decision", "GENUINE")                 # FRAUD / MID_LEVEL / GENUINE
            action = TIER_TO_ACTION.get(tier, "STEP_UP")           # BLOCK / STEP_UP / ALLOW
            risk_score = float(res.get("risk_score", 0.0))
            reasons = res.get("reasons", [])
            tx_ref = res.get("transaction_id", "N/A")

            st.markdown("---")
            if action == "ALLOW":
                st.success("### ✅ Payment Approved & Completed!")
                st.markdown(f"""
                - **Tier:** `{tier}` → **Action:** `ALLOW` (Zero customer friction)
                - **Risk Score:** **{risk_score:.3f}** / 1.00
                - **Transaction ID:** `{tx_ref}`
                """)
                st.balloons()
            elif action == "STEP_UP":
                st.warning("### ⚠️ Step-Up Verification Required!")
                st.markdown(f"""
                - **Tier:** `{tier}` → **Action:** `STEP_UP` (Payment temporarily paused)
                - **Risk Score:** **{risk_score:.3f}** / 1.00
                - **Action:** OTP / Biometric challenge dispatched to user device.
                - **Transaction ID:** `{tx_ref}`
                """)
            else:
                st.error("### 🛑 Transaction Blocked & Prevented!")
                st.markdown(f"""
                - **Tier:** `{tier}` → **Action:** `BLOCK` (High probability Fraud Ring Detected)
                - **Risk Score:** **{risk_score:.3f}** / 1.00
                - **Action:** Funds protected. Entity quarantined for SOC analyst investigation.
                - **Transaction ID:** `{tx_ref}`
                """)

            st.markdown("#### 🔍 GNN Explainability Evidence:")
            if reasons:
                for r in reasons:
                    if any(k in r for k in ("Syndicate", "Device Sharing", "Contagion", "Structural Anomaly")):
                        st.error(f"🚨 **{r}**")
                    elif any(k in r for k in ("Anomaly", "Elevated", "Mid-Level", "Borderline")):
                        st.warning(f"⚠️ **{r}**")
                    else:
                        st.info(f"ℹ️ {r}")
            else:
                st.info("ℹ️ No anomalous neighborhood patterns detected.")

            st.markdown("---")
            st.caption(
                f"👉 Paste `{data['device_id']}` into **3_Graph_Explorer** to visualize this entity's multi-hop network, "
                "or open **4_Analyst_Review** to inspect the SOC queue!"
            )
