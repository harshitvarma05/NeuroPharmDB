import streamlit as st
import pandas as pd
from database.db_connection import run_sql_query

def show_sql_console():
    st.markdown(
        """
        <div class="apple-card">
          <div class="apple-title">🧾 SQL Console</div>
          <div class="apple-subtitle">Run SQL queries manually (SELECT recommended)</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.warning(
        "For safety, this console is intended for SELECT queries. "
        "If UPDATE/DELETE is enabled, it can modify your database."
    )

    default_query = "SELECT * FROM drug LIMIT 10;"
    sql = st.text_area("Write SQL", value=default_query, height=180)

    col1, col2 = st.columns([1, 3])
    with col1:
        run = st.button("Run", type="primary", key="sql_run_btn")
    with col2:
        allow_write = st.checkbox("Allow UPDATE/DELETE/DDL (danger)", value=False)

    if run:
        try:
            result = run_sql_query(sql, allow_write=allow_write)

            if result["type"] == "select":
                df = pd.DataFrame(result["rows"])
                st.success(f"Returned {len(df)} row(s).")
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.success(f"Query OK. Rows affected: {result.get('rowcount', 0)}")

        except Exception as e:
            st.error(f"SQL Error: {e}")
