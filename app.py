import streamlit as st

from database.db_connection import init_db, authenticate_user
from frontend.layout import apply_base_style, login_screen, topbar

from frontend.home import show_home
from frontend.drug_page import show_drug_page
from frontend.interaction_page import show_interaction_page
from frontend.neuro_page import show_neuro_page
from frontend.alert_page import show_alert_page
from frontend.timeline_page import show_timeline_page
from frontend.user_page import show_user_page

st.set_page_config(
    page_title="NeuroPharmDB",
    layout="wide",
    initial_sidebar_state="expanded"
)

APP_NAME = "NeuroPharmDB"

apply_base_style()
init_db()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    user_id, email = login_screen(APP_NAME)

    if user_id and email:
        user = authenticate_user(user_id, email)
        if user:
            st.session_state.logged_in = True
            st.session_state.user_id = user["user_id"]
            st.session_state.user_name = user["name"]
            st.success("Login successful")
            st.rerun()
        else:
            st.error("Invalid user ID or email")

    st.stop()

USER_ID = st.session_state.user_id

topbar(APP_NAME, USER_ID)
st.write("")

PAGES = {
    "Home": show_home,
    "Drug Database": show_drug_page,
    "Drug Interactions": show_interaction_page,
    "Neuro Effects": show_neuro_page,
    "Timeline & History": show_timeline_page,
    "Alerts": show_alert_page,
    "Users": show_user_page,
}

with st.sidebar:
    st.markdown("### Navigation")
    selected = st.radio("Go to", list(PAGES.keys()), label_visibility="collapsed")

PAGES[selected]()
