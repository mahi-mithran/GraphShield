"""
GraphShield - Analyst Triage & Feedback Console
Page 4: 4_Analyst_Review.py
Requirements:
  - Lists ONLY FRAUD and MID_LEVEL transactions needing review
  - Provides Confirm Fraud / Verify User / Reject Alert action buttons per row
  - Persists analyst feedback to backend & updates status in real-time
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
import pandas as pd
from frontend.components.api_client import api_client, render_api_error_if_any

st.set_page_config(page_title="GraphShield - Analyst Review", page_icon="🛡️", layout="wide")

st.title("🛡️ Analyst Review & Case Resolution")
st.caption("Investigate flagged FRAUD (≥ 0.70) and MID_LEVEL (0.30 - 0.69) alerts. Confirm fraud rings or verify users.")

# Filter by Status
col_s1, col_s2 = st.columns([1, 3])
with col_s1:
    status_filter = st.selectbox(
        "Alert Workflow Status",
        ["All Flagged", "PENDING_REVIEW", "CONFIRMED_FRAUD", "VERIFIED_USER", "REJECTED_ALERT"],
        index=1,
    )

api_status_param = None if status_filter == "All Flagged" else status_filter

with st.spinner("Fetching flagged alerts from backend database..."):
    flagged_tx, error = api_client.get_flagged_transactions(limit=60, status=api_status_param)

if error:
    render_api_error_if_any(error)
    st.stop()

if not flagged_tx:
    st.success("🎉 No transactions currently pending review in this status queue!")
    st.stop()

st.info(f"Showing **{len(flagged_tx)}** transactions classified as **FRAUD** or **MID_LEVEL**.")

# Iterate and render each flagged alert in an actionable card
for idx, tx in enumerate(flagged_tx):
    tx_id = tx["transaction_id"]
    tier = tx["decision"]
    score = tx["risk_score"]
    status_curr = tx.get("status", "PENDING_REVIEW")

    # Tier Color Badge
    if tier == "FRAUD":
        badge_style = "background-color: #FEE2E2; color: #991B1B; border: 1px solid #DC2626;"
        tier_icon = "🔴"
    else:  # MID_LEVEL
        badge_style = "background-color: #FFEDD5; color: #9A3412; border: 1px solid #EA580C;"
        tier_icon = "🟠"

    with st.container():
        st.markdown(
            f"""
            <div style="border: 1px solid #E2E8F0; border-radius: 8px; padding: 14px 18px; margin-bottom: 12px; background-color: #FFFFFF;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="font-size: 16px; font-weight: 700; color: #1E293B;">
                        Transaction: <code>{tx_id}</code> &nbsp;|&nbsp; Account: <code>{tx['account_id']}</code>
                    </div>
                    <div>
                        <span style="{badge_style} padding: 4px 12px; border-radius: 6px; font-weight: 700; font-size: 13px;">
                            {tier_icon} {tier} ({score:.2f})
                        </span>
                        &nbsp;
                        <span style="background-color: #F1F5F9; color: #475569; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 600;">
                            Status: {status_curr}
                        </span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_d1, col_d2, col_d3 = st.columns([2, 2, 3])

        with col_d1:
            st.write(f"**Amount:** {tx['currency']} {tx['amount']:,.2f}")
            st.write(f"**Sector:** {tx['sector']}")
            st.write(f"**Merchant ID:** `{tx['merchant_id']}`")

        with col_d2:
            st.write(f"**Device ID:** `{tx['device_id']}`")
            st.write(f"**IP Address:** `{tx['ip_address']}`")
            st.write(f"**Payment Method:** {tx['payment_method_id']}")

        with col_d3:
            st.markdown("**Analyst Decision Action:**")
            btn_col1, btn_col2, btn_col3 = st.columns(3)

            with btn_col1:
                if st.button("🚨 Confirm Fraud", key=f"fraud_{tx_id}", use_container_width=True):
                    res, err = api_client.submit_feedback({
                        "transaction_id": tx_id,
                        "action": "Confirm Fraud",
                        "analyst_id": "analyst_agent_lead",
                        "notes": "Confirmed syndicate fraud ring participation via GraphShield console.",
                    })
                    if err:
                        render_api_error_if_any(err)
                    else:
                        st.toast(f"✅ {tx_id} marked as CONFIRMED_FRAUD!", icon="🚨")
                        st.rerun()

            with btn_col2:
                if st.button("🛡️ Verify User", key=f"verify_{tx_id}", use_container_width=True):
                    res, err = api_client.submit_feedback({
                        "transaction_id": tx_id,
                        "action": "Verify User",
                        "analyst_id": "analyst_agent_lead",
                        "notes": "Customer passed step-up verification / OTP challenge.",
                    })
                    if err:
                        render_api_error_if_any(err)
                    else:
                        st.toast(f"✅ {tx_id} marked as VERIFIED_USER!", icon="🛡️")
                        st.rerun()

            with btn_col3:
                if st.button("❌ Reject Alert", key=f"reject_{tx_id}", use_container_width=True):
                    res, err = api_client.submit_feedback({
                        "transaction_id": tx_id,
                        "action": "Reject Alert",
                        "analyst_id": "analyst_agent_lead",
                        "notes": "Determined to be a false positive alert.",
                    })
                    if err:
                        render_api_error_if_any(err)
                    else:
                        st.toast(f"✅ {tx_id} marked as REJECTED_ALERT!", icon="ℹ️")
                        st.rerun()

        st.markdown("<hr style='margin: 8px 0 16px 0; border: none; border-top: 1px dashed #CBD5E1;'>", unsafe_allow_html=True)
