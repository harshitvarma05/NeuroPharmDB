import streamlit as st
from database.db_connection import init_db, list_drugs, list_interactions, list_neuro_effects, list_recent_alerts

def show_home():
    st.markdown(
        """
        <div class="apple-card">
          <div class="apple-title">NeuroPharmDB</div>
          <div class="apple-subtitle">Drugs • interactions • neuro effects • history • alerts</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.write("")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="apple-card"><b>Drug Database</b><div class="apple-subtitle">Browse drugs, classes, mechanisms</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="apple-card"><b>Interaction Checker</b><div class="apple-subtitle">Check drug pairs and severity</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="apple-card"><b>Timeline & History</b><div class="apple-subtitle">Track medicines taken over time</div></div>', unsafe_allow_html=True)

    st.write("")

    # Stats
    try:
        init_db()
        total_drugs = len(list_drugs())
        total_interactions = len(list_interactions())
        total_effects = len(list_neuro_effects())
        # Alerts are per-user; show recent total for logged-in user if present
        user_id = st.session_state.get("user_id")
        total_alerts = len(list_recent_alerts(user_id, limit=50)) if user_id else 0
    except Exception:
        total_drugs = 0
        total_interactions = 0
        total_effects = 0
        total_alerts = 0

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Total Drugs", total_drugs)
    s2.metric("Interactions", total_interactions)
    s3.metric("Neuro Effects", total_effects)
    s4.metric("Alerts", total_alerts)

    st.write("")
    st.markdown('<div class="apple-card"><b>Tip</b><div class="apple-subtitle">Use the sidebar to navigate modules.</div></div>', unsafe_allow_html=True)
