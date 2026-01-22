import streamlit as st
import pandas as pd
from database.db_connection import init_db, list_drugs, create_drug, delete_drug, get_drug_by_id

def show_drug_page():
    st.markdown(
        """
        <div class="apple-card">
          <div class="apple-title">Drug Database</div>
          <div class="apple-subtitle">Manage drugs (Drug table)</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.write("")

    init_db()

    q = st.text_input("Search", placeholder="Search by name / class / mechanism...").strip().lower()
    drugs = list_drugs()

    if q:
        drugs = [
            d for d in drugs
            if q in (d.get("name","").lower() + " " + (d.get("class","") or "").lower() + " " + (d.get("mechanism","") or "").lower())
        ]

    if drugs:
        df = pd.DataFrame(drugs)
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.write("")
        pick = st.selectbox("View details", options=["—"] + [d["drug_id"] for d in drugs])
        if pick != "—":
            d = get_drug_by_id(pick)
            if d:
                st.markdown("### Details")
                st.write(f"**Drug ID:** {d['drug_id']}")
                st.write(f"**Name:** {d['name']}")
                st.write(f"**Class:** {d.get('class','')}")
                st.write(f"**Mechanism:** {d.get('mechanism','')}")
    else:
        st.info("No drugs found.")

    st.markdown("---")

    with st.expander("Add Drug"):
        with st.form("add_drug_form", clear_on_submit=True):
            drug_id = st.text_input("Drug ID * (e.g., D001)")
            name = st.text_input("Drug Name *")
            drug_class = st.text_input("Class (optional)")
            mechanism = st.text_area("Mechanism (optional)")
            submitted = st.form_submit_button("Add", type="primary")

            if submitted:
                if not drug_id or not name:
                    st.error("Drug ID and Drug Name are required.")
                else:
                    create_drug(
                        drug_id=drug_id.strip(),
                        name=name.strip(),
                        drug_class=drug_class.strip() if drug_class else None,
                        mechanism=mechanism.strip() if mechanism else None
                    )
                    st.success("Drug added.")
                    st.rerun()

    with st.expander("🗑️ Delete Drug"):
        did = st.text_input("Drug ID to delete")
        if st.button("Delete", type="secondary"):
            delete_drug(did.strip())
            st.success("Deleted.")
            st.rerun()
