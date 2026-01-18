import streamlit as st
import pandas as pd
from datetime import date
from frontend.layout import severity_badge
from database.db_connection import (
    init_db,
    list_drugs,
    add_timeline_entry,
    list_timeline_for_user,
    check_new_drug_and_alert,
    get_active_drugs_for_user,
    find_interaction_between,
)

def show_timeline_page():
    st.markdown(
        """
        <div class="apple-card">
          <div class="apple-title">📅 Timeline & History</div>
          <div class="apple-subtitle">Medication history for logged-in user</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.write("")

    user_id = st.session_state.get("user_id")
    if not user_id:
        st.error("Not logged in.")
        return

    init_db()
    drugs = list_drugs()

    drug_labels = ["—"] + [f"{d['name']} ({d['drug_id']})" for d in drugs]
    drug_map = {f"{d['name']} ({d['drug_id']})": d["drug_id"] for d in drugs}

    st.subheader("➕ Add to History")
    with st.form("add_timeline", clear_on_submit=True):
        timeline_id = st.text_input("Timeline ID * (e.g., TL001)")
        drug_label = st.selectbox("Drug *", drug_labels)
        dosage = st.text_input("Dosage (e.g., 50mg)")
        frequency = st.text_input("Frequency (e.g., once daily)")
        start_date = st.date_input("Start date", value=date.today())
        submitted = st.form_submit_button("Add", type="primary")

        if submitted:
            if not timeline_id or drug_label == "—":
                st.error("timeline_id and drug are required.")
            else:
                new_drug_id = drug_map[drug_label]

                # add timeline row
                add_timeline_entry(
                    timeline_id=timeline_id.strip(),
                    user_id=user_id,
                    drug_id=new_drug_id,
                    dosage=dosage.strip() if dosage else None,
                    frequency=frequency.strip() if frequency else None,
                    start_date=start_date.isoformat(),
                )

                # trigger alerts for high-risk interactions
                created = check_new_drug_and_alert(user_id, new_drug_id, min_severity=7.0)
                if created > 0:
                    st.warning(f"{created} alert(s) generated. Check Alerts 🔔")

                # show interactions found with current meds (informational)
                pairs = []
                for other in get_active_drugs_for_user(user_id):
                    if other == new_drug_id:
                        continue
                    inter = find_interaction_between(new_drug_id, other)
                    if inter:
                        pairs.append({
                            "Drug A": new_drug_id,
                            "Drug B": other,
                            "Effect": inter["effect_name"],
                            "Severity": inter["severity_score"],
                            "Mechanism": inter["mechanism"] or ""
                        })

                st.success("Added.")
                if pairs:
                    st.markdown("#### Interaction(s) found with your current meds")
                    st.dataframe(pd.DataFrame(pairs), use_container_width=True, hide_index=True)

                    st.markdown("#### Risk badges")
                    for p in pairs:
                        st.markdown(
                            f"- **{p['Drug A']} + {p['Drug B']}** → {p['Effect']} {severity_badge(p['Severity'])}",
                            unsafe_allow_html=True
                        )

                st.rerun()

    st.markdown("---")
    st.subheader("📄 Your History")
    history = list_timeline_for_user(user_id)
    if history:
        st.dataframe(pd.DataFrame(history), use_container_width=True, hide_index=True)
    else:
        st.info("No history yet.")
