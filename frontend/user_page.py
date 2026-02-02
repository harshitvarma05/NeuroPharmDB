import streamlit as st
import pandas as pd
from database.db_connection import init_db, create_user, list_users

def show_user_page():
    st.markdown(
        """
        <div class="apple-card">
          <div class="apple-title">Users</div>
          <div class="apple-subtitle">Manage users (user_id + email login)</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.write("")

    init_db()

    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Create User")

        user_id = st.text_input("User ID")
        name = st.text_input("Name")
        email = st.text_input("Email")

        role = st.selectbox(
            "Role",
            ["patient", "admin"],
            help="Admin/Doctor can manage drugs and interactions. Patient has limited access."
        )

        age = st.number_input("Age", min_value=0, step=1)
        medical_history = st.text_area("Medical History")

        if st.button("Create User", type="primary"):
            if not user_id or not email:
                st.error("User ID and Email are required.")
            else:
                create_user(
                    user_id=user_id,
                    name=name,
                    email=email,
                    age=age,
                    medical_history=medical_history,
                    role=role
                )
                st.success(f"User {user_id} created with role '{role}'.")
                st.rerun()

    with col2:
        st.subheader("All Users")
        users = list_users()
        if users:
            st.dataframe(pd.DataFrame(users), use_container_width=True, hide_index=True)
        else:
            st.info("No users yet.")
