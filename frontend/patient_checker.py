import streamlit as st

from database.db_connection import list_drugs, evaluate_pair_and_alert


def _severity_badge(sev: float) -> str:
    """Simple badge that works even if your layout.py doesn't expose severity_badge."""
    if sev is None:
        return ""
    try:
        sev_f = float(sev)
    except Exception:
        return str(sev)

    if sev_f >= 7:
        color = "#ff453a"  # red
        label = "HIGH"
    elif sev_f >= 4:
        color = "#ff9f0a"  # amber
        label = "MODERATE"
    else:
        color = "#32d74b"  # green
        label = "LOW"

    return (
        f"<span style='display:inline-block;padding:4px 10px;border-radius:999px;"
        f"background:{color};color:#000;font-weight:700;font-size:12px;'>"
        f"{label} · {sev_f:.1f}/10</span>"
    )


def show_patient_checker():
    """Patient-only page: select two drugs and auto-detect interaction/effect."""
    st.markdown(
        """
        <div style="padding:16px;border:1px solid rgba(255,255,255,0.08);border-radius:18px;\
                    background:rgba(255,255,255,0.04);margin-bottom:14px;">
            <div style="font-size:20px;font-weight:700;">Drug Safety Checker</div>
            <div style="opacity:0.8;margin-top:6px;">Pick two drugs. The system will auto-detect interactions, neuro effect, severity and create alerts for high-risk pairs.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    user_id = st.session_state.get("user_id")
    if not user_id:
        st.error("You are not logged in.")
        return

    drugs = list_drugs()
    if not drugs:
        st.info("No drugs found in database. Ask the doctor/admin to add drugs first.")
        return

    options = ["— Select —"] + [f"{d['name']} ({d['drug_id']})" for d in drugs]
    to_id = {f"{d['name']} ({d['drug_id']})": d["drug_id"] for d in drugs}

    c1, c2 = st.columns(2)
    with c1:
        d1 = st.selectbox("Drug 1", options, key="checker_d1")
    with c2:
        d2 = st.selectbox("Drug 2", options, key="checker_d2")

    if st.button("Check", type="primary", key="checker_run"):
        if d1 == "— Select —" or d2 == "— Select —":
            st.error("Select two drugs.")
            return
        if d1 == d2:
            st.error("Select two different drugs.")
            return

        drug_a = to_id[d1]
        drug_b = to_id[d2]

        result = evaluate_pair_and_alert(user_id, drug_a, drug_b, threshold=7.0)

        if result.get("status") == "safe" or not result.get("interaction"):
            st.success("No interaction found in the database for this pair. (Based on current knowledge base)")
            return

        inter = result["interaction"]
        effect = inter.get("effect_name") or inter.get("effect_id")
        sev = inter.get("severity_score")
        mechanism = inter.get("mechanism")

        st.markdown(
            f"""
            <div style="padding:16px;border-radius:18px;border:1px solid rgba(255,255,255,0.10);\
                        background:rgba(255,255,255,0.03);">
                <div style="font-size:16px;font-weight:700;">Effect detected: {effect}</div>
                <div style="margin-top:10px;">Severity: {_severity_badge(sev)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if mechanism:
            st.markdown("### Why was I alerted?")
            st.info(mechanism)

        if result.get("status") == "high":
            st.error("High risk interaction. An alert has been generated and stored in Alerts.")
        elif result.get("status") == "medium":
            st.warning("Moderate risk interaction. Please use caution.")
        else:
            st.warning("Mild interaction possible.")
