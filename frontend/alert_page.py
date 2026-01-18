import streamlit as st
import pandas as pd
from database.db_connection import list_recent_alerts, mark_alerts_read_for_user, get_alert_explanation
from frontend.layout import severity_badge

def show_alert_page():
    st.markdown(
        """
        <div class="apple-card">
          <div class="apple-title">🔔 Alerts</div>
          <div class="apple-subtitle">Notifications created automatically for high severity interactions</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.write("")

    user_id = st.session_state.get("user_id")
    if not user_id:
        st.error("Not logged in.")
        return

    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("Recent Alerts")
    with c2:
        if st.button("Mark all as read", key="alerts_mark_all_read"):
            mark_alerts_read_for_user(user_id)
            st.success("Marked as read.")
            st.rerun()

    alerts = list_recent_alerts(user_id, limit=100)
    if not alerts:
        st.info("No alerts yet. Add drugs to Timeline that have a high-risk interaction.")
        return

    df = pd.DataFrame(alerts)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Why was I alerted?")

    alert_ids = [a["alert_id"] for a in alerts]
    picked = st.selectbox("Select an alert", ["—"] + alert_ids, key="alert_pick")
    if picked != "—":
        info = get_alert_explanation(picked)
        if not info:
            st.error("Alert not found.")
        else:
            st.markdown(
                f"""
                <div class="apple-card">
                  <div class="apple-title">🧾 Explanation</div>
                  <div class="apple-subtitle">Reasoning for this alert</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            st.write("")
            st.markdown(f"**Status:** `{info['status']}`")
            st.markdown(f"**Created:** `{info['created_at']}`")
            st.markdown(f"**Severity:** {severity_badge(info.get('severity_score'))}", unsafe_allow_html=True)

            st.markdown("### Drugs involved")
            st.write(f"**Drug 1:** {info['drug1_name']} ({info['drug1_id']}) — {info.get('drug1_class') or ''}")
            st.write(f"**Drug 2:** {info['drug2_name']} ({info['drug2_id']}) — {info.get('drug2_class') or ''}")

            st.markdown("### Effect")
            st.write(f"**Effect:** {info.get('effect_name') or '—'}")
            st.write(f"**Category:** {info.get('effect_category') or '—'}")

            st.markdown("### Mechanism (Why this happens)")
            st.write(info.get("interaction_mechanism") or "—")

            st.markdown("### Alert message")
            st.info(info.get("message") or "")
