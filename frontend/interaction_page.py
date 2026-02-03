import streamlit as st
import pandas as pd

from database.db_connection import (
    init_db,
    list_drugs,
    list_neuro_effects,
    list_interactions,
    add_interaction,
    delete_interaction,
    get_pending_ai_suggestions,
    approve_ai_suggestion,
    reject_ai_suggestion,
)

from frontend.layout import severity_badge


def _drug_label(d: dict) -> str:
    return f"{d['drug_id']} — {d.get('name','')}".strip()


def _effect_label(e: dict) -> str:
    name = e.get('effect_name', '')
    eff_id = e.get('effect_id', '')
    if name and eff_id:
        return f"{eff_id} — {name}"
    return eff_id or name or "(unknown)"


def show_interaction_page():
    init_db()

    role = st.session_state.get("role", "patient")
    user_id = st.session_state.get("user_id", "")

    st.markdown("""<div class='glass-card'>
        <h2 style='margin:0'>Drug Interactions</h2>
        <p style='margin:6px 0 0 0' class='muted'>Known interactions in the database and AI suggestions pending doctor review.</p>
    </div>""", unsafe_allow_html=True)

    if role not in ("doctor", "admin"):
        _patient_readonly()
        return

    tabs = st.tabs(["Interactions", "AI Suggestions (Review)"])
    with tabs[0]:
        _doctor_interactions_panel()
    with tabs[1]:
        _doctor_ai_review_panel(doctor_id=user_id)


def _patient_readonly():
    st.subheader("Known Interactions")
    interactions = list_interactions()
    if not interactions:
        st.info("No interactions found in the database.")
        return

    df = pd.DataFrame(interactions)
    # Keep a clean, readable subset if possible
    cols = [c for c in ["interaction_id", "drug1_id", "drug2_id", "effect_name", "severity_score", "evidence_level"] if c in df.columns]
    if cols:
        df = df[cols]
    st.dataframe(df, use_container_width=True)


def _doctor_interactions_panel():
    st.subheader("Interaction Database")

    drugs = list_drugs()
    effects = list_neuro_effects()
    interactions = list_interactions()

    col_a, col_b = st.columns([1.1, 0.9], gap="large")

    with col_a:
        st.markdown("#### Existing Interactions")
        if not interactions:
            st.info("No interactions found.")
        else:
            df = pd.DataFrame(interactions)
            st.dataframe(df, use_container_width=True, height=360)

            st.markdown("---")
            st.markdown("#### Remove Interaction")
            ids = [x.get("interaction_id") for x in interactions if x.get("interaction_id")]
            if ids:
                delete_id = st.selectbox("Select interaction ID", ids, key="int_delete_id")
                if st.button("Delete selected", key="int_delete_btn", type="secondary"):
                    ok = delete_interaction(delete_id)
                    if ok:
                        st.success("Deleted interaction.")
                        st.rerun()
                    else:
                        st.warning("Interaction not found.")

    with col_b:
        st.markdown("#### Add Interaction")

        if not drugs or not effects:
            st.warning("You need at least 1 drug and 1 neuro effect in the database before adding interactions.")
            return

        drug_opts = { _drug_label(d): d["drug_id"] for d in drugs }
        effect_opts = { _effect_label(e): e["effect_id"] for e in effects }

        with st.form("add_interaction_form", clear_on_submit=True):
            interaction_id = st.text_input("Interaction ID", placeholder="e.g., INT001")
            d1 = st.selectbox("Drug A", list(drug_opts.keys()))
            d2 = st.selectbox("Drug B", list(drug_opts.keys()))
            eff = st.selectbox("Neuro effect", list(effect_opts.keys()))

            sev = st.slider("Severity score (0–10)", min_value=0.0, max_value=10.0, value=6.0, step=0.1)
            st.markdown(severity_badge(sev), unsafe_allow_html=True)

            mechanism = st.text_area("Mechanism / Notes", placeholder="Short mechanism or rationale", height=80)
            evidence_level = st.selectbox("Evidence level", ["low", "moderate", "high"], index=1)

            submitted = st.form_submit_button("Add interaction")
            if submitted:
                if not interaction_id.strip():
                    st.error("Interaction ID is required.")
                elif drug_opts[d1] == drug_opts[d2]:
                    st.error("Drug A and Drug B must be different.")
                else:
                    add_interaction(
                        interaction_id=interaction_id.strip(),
                        drug1_id=drug_opts[d1],
                        drug2_id=drug_opts[d2],
                        effect_id=effect_opts[eff],
                        severity_score=float(sev),
                        mechanism=mechanism.strip(),
                        evidence_level=evidence_level,
                    )
                    st.success("Interaction added.")
                    st.rerun()


def _doctor_ai_review_panel(doctor_id: str):
    st.subheader("AI Suggestions")

    st.caption("Suggestions are generated by an AI-assisted module and require doctor approval before being treated as clinically reliable.")

    pending = get_pending_ai_suggestions()
    if not pending:
        st.info("No pending AI suggestions.")
        return

    # Sort newest first
    pending = sorted(pending, key=lambda x: x.get("created_at") or 0, reverse=True)

    for s in pending:
        sid = int(s["suggestion_id"])
        sev = float(s.get("severity_score", 0.0))

        header = f"Suggestion #{sid} — {s.get('predicted_effect','')}"
        with st.expander(header, expanded=False):
            c1, c2 = st.columns([0.65, 0.35], gap="medium")
            with c1:
                st.markdown(f"**Patient:** {s.get('user_id','')}  ")
                st.markdown(f"**Drugs:** {s.get('drug1_id','')} + {s.get('drug2_id','')}  ")
                st.markdown(f"**Severity:** {sev:.1f}/10")
                st.markdown(severity_badge(sev), unsafe_allow_html=True)
                st.markdown("**Explanation**")
                st.write(s.get("explanation", ""))
            with c2:
                st.markdown("**Decision**")
                approve_key = f"ai_approve_{sid}"
                reject_key = f"ai_reject_{sid}"

                if st.button("Approve", key=approve_key, type="primary"):
                    ok = approve_ai_suggestion(suggestion_id=sid, approved=True, doctor_id=doctor_id)
                    if ok:
                        st.success("Approved. Patient will see an alert.")
                        st.rerun()
                    else:
                        st.warning("Could not approve (already processed).")
                if st.button("Reject", key=reject_key, type="secondary"):
                    ok = reject_ai_suggestion(suggestion_id=sid, doctor_id=doctor_id)
                    if ok:
                        st.success("Rejected. Patient will see an alert.")
                        st.rerun()
                    else:
                        st.warning("Could not reject (already processed).")

