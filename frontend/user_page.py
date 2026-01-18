import streamlit as st
import pandas as pd
from database.db_connection import init_db, create_user, list_users

def show_user_page():
    st.markdown(
        """
        <div class="apple-card">
          <div class="apple-title">👤 Users</div>
          <div class="apple-subtitle">Manage users (user_id + email login)</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.write("")

    init_db()

    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("➕ Create User")
        with st.form("add_user", clear_on_submit=True):
            user_id = st.text_input("User ID * (e.g., U001)")
            name = st.text_input("Name *")
            email = st.text_input("Email *")
            age = st.number_input("Age (optional)", min_value=0, max_value=120, value=0)
            medical_history = st.text_area("Medical history (optional)")
            submitted = st.form_submit_button("Create", type="primary")

            if submitted:
                if not user_id or not name or not email:
                    st.error("user_id, name, email required.")
                else:
                    create_user(
                        user_id=user_id.strip(),
                        name=name.strip(),
                        email=email.strip(),
                        age=int(age) if age and int(age) > 0 else None,
                        medical_history=medical_history.strip() if medical_history else None
                    )
                    st.success("User created.")
                    st.rerun()

    with col2:
        st.subheader("All Users")
        users = list_users()
        if users:
            st.dataframe(pd.DataFrame(users), use_container_width=True, hide_index=True)
        else:
            st.info("No users yet.")
