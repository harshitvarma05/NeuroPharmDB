import streamlit as st
import pandas as pd

from database import db_connection as dbc


def show_user_page():
    st.markdown(
        """
        <div style="padding:16px;border:1px solid rgba(255,255,255,0.08);border-radius:18px;
                    background:rgba(255,255,255,0.04);margin-bottom:14px;">
            <div style="font-size:20px;font-weight:800;">Users</div>
            <div style="opacity:0.8;margin-top:6px;">
                Create users and assign role (patient / doctor). Login uses User ID + Email.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    dbc.init_db()

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Create / Update User")

        user_id = st.text_input("User ID", key="u_user_id")
        name = st.text_input("Name", key="u_name")
        email = st.text_input("Email", key="u_email")
        age = st.text_input("Age", key="u_age")  # keep string if backend expects
        medical_history = st.text_area("Medical History", key="u_med_hist")

        role = st.selectbox("Role", ["patient", "doctor"], key="u_role")

        if st.button("Save User", use_container_width=True, key="u_save_btn"):
            if not user_id or not name or not email:
                st.error("User ID, Name, Email are required.")
            else:
                # create_user signature in your backend: (user_id, name, email, age, medical_history, role="patient")
                dbc.create_user(
                    user_id=user_id,
                    name=name,
                    email=email,
                    role=role,
                    age=age,
                    medical_history=medical_history
                )
                st.success(f"Saved {user_id} as {role}.")
                st.rerun()

    with col2:
        st.subheader("All Users")
        users = dbc.list_users() if hasattr(dbc, "list_users") else []
        if not users:
            st.info("No users found.")
        else:
            st.dataframe(pd.DataFrame(users), use_container_width=True, hide_index=True)
