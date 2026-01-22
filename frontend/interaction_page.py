import streamlit as st
import pandas as pd
from frontend.layout import severity_badge
from database.db_connection import (
    init_db,
    list_drugs,
    list_neuro_effects,
    add_interaction,
    list_interactions,
    top_risk_combinations,
)

def show_interaction_page():
    st.markdown(
        """
        <div class="apple-card">
          <div class="apple-title">Drug Interactions</div>
          <div class="apple-subtitle">Add + browse interactions (alerts auto-trigger at severity ≥ 7)</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.write("")

    init_db()
    drugs = list_drugs()
    effects = list_neuro_effects()

    drug_labels = ["—"] + [f"{d['name']} ({d['drug_id']})" for d in drugs]
    drug_map = {f"{d['name']} ({d['drug_id']})": d["drug_id"] for d in drugs}

    effect_labels = ["—"] + [f"{e['effect_name']} ({e['effect_id']})" for e in effects]
    effect_map = {f"{e['effect_name']} ({e['effect_id']})": e["effect_id"] for e in effects}

    st.subheader("Add Interaction")
    with st.form("add_interaction_form", clear_on_submit=True):
        interaction_id = st.text_input("Interaction ID * (e.g., I001)")
        d1 = st.selectbox("Drug 1 *", drug_labels)
        d2 = st.selectbox("Drug 2 *", drug_labels)
        eff = st.selectbox("Neuro Effect *", effect_labels)
        severity = st.number_input("Severity score * (0–10)", min_value=0.0, max_value=10.0, step=0.1)
        mechanism = st.text_area("Mechanism (optional)")
        submitted = st.form_submit_button("Add", type="primary")

        if submitted:
            if not interaction_id or d1 == "—" or d2 == "—" or d1 == d2 or eff == "—":
                st.error("Fill interaction_id, choose 2 different drugs, and an effect.")
            else:
                add_interaction(
                    interaction_id=interaction_id.strip(),
                    drug1_id=drug_map[d1],
                    drug2_id=drug_map[d2],
                    effect_id=effect_map[eff],
                    severity_score=float(severity),
                    mechanism=mechanism.strip() if mechanism else None
                )
                st.success("Interaction added. (Alerts auto-create if severity ≥ 7)")
                st.rerun()

    st.markdown("---")
    st.subheader("Top Risk Combinations")
    try:
        top = top_risk_combinations(limit=10)
        if top:
            st.dataframe(pd.DataFrame(top), use_container_width=True, hide_index=True)
        else:
            st.info("No interactions yet.")
    except Exception as e:
        st.error(f"Failed to load top risk combos: {e}")

    st.markdown("---")
    st.subheader("All Interactions (with risk)")
    inters = list_interactions()
    if inters:
        df = pd.DataFrame(inters)
        # Make a human-friendly column
        if "severity_score" in df.columns:
            df["Risk"] = df["severity_score"].apply(lambda x: "High" if float(x) >= 7 else ("Medium" if float(x) >= 4 else "Low"))
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown("#### Quick Risk View")
        for row in inters[:12]:
            st.markdown(
                f"- **{row['drug1_id']} + {row['drug2_id']}** → `{row['effect_id']}` "
                f"{severity_badge(row.get('severity_score'))}",
                unsafe_allow_html=True
            )
    else:
        st.info("No interactions yet.")
    inters = list_interactions()
    if inters:
        st.dataframe(pd.DataFrame(inters), use_container_width=True, hide_index=True)
    else:
        st.info("No interactions yet.")
