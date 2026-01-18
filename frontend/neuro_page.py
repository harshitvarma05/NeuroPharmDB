import streamlit as st
import pandas as pd
from database.db_connection import init_db, list_neuro_effects, create_neuro_effect

def show_neuro_page():
    st.markdown(
        """
        <div class="apple-card">
          <div class="apple-title">🧠 Neuro Effects</div>
          <div class="apple-subtitle">Manage NeuroEffect table</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.write("")

    init_db()

    effects = list_neuro_effects()
    if effects:
        st.dataframe(pd.DataFrame(effects), use_container_width=True, hide_index=True)
    else:
        st.info("No neuro effects yet.")

    st.markdown("---")
    with st.expander("➕ Add Neuro Effect"):
        with st.form("add_effect", clear_on_submit=True):
            effect_id = st.text_input("Effect ID * (e.g., E001)")
            effect_name = st.text_input("Effect name *")
            category = st.text_input("Category (optional)")
            severity_level = st.text_input("Default severity (optional)")
            submitted = st.form_submit_button("Add", type="primary")

            if submitted:
                if not effect_id or not effect_name:
                    st.error("effect_id and effect_name are required.")
                else:
                    create_neuro_effect(
                        effect_id=effect_id.strip(),
                        effect_name=effect_name.strip(),
                        category=category.strip() if category else None,
                        severity_level=severity_level.strip() if severity_level else None
                    )
                    st.success("Added.")
                    st.rerun()
