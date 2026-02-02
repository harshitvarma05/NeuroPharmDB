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
from frontend.sql_console import show_sql_console

# Patient-only checker page (you should have this file in your frontend folder)
try:
    from frontend.patient_checker import show_patient_checker
except Exception:
    show_patient_checker = None


st.set_page_config(
    page_title="NeuroPharmDB",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_NAME = "NeuroPharmDB"


def _ensure_session_defaults():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "role" not in st.session_state:
        st.session_state.role = "patient"


apply_base_style()
init_db()
_ensure_session_defaults()


# ---------------------------
# LOGIN
# ---------------------------
if not st.session_state.logged_in:
    user_id, email = login_screen(APP_NAME)

    if user_id and email:
        user = authenticate_user(user_id, email)
        if user:
            st.session_state.logged_in = True
            st.session_state.user_id = user["user_id"]
            st.session_state.user_name = user.get("name")
            st.session_state.role = user.get("role", "patient")
            st.success("Login successful")
            st.rerun()
        else:
            st.error("Invalid user ID or email")

    st.stop()


USER_ID = st.session_state.user_id
ROLE = st.session_state.get("role", "patient")

topbar(APP_NAME, USER_ID)
st.write("")


# ---------------------------
# ROLE-BASED NAVIGATION
# ---------------------------
if ROLE == "admin":
    PAGES = {
        "Home": show_home,
        "Drugs": show_drug_page,
        "Interactions": show_interaction_page,
        "Neuro Effects": show_neuro_page,
        "Users": show_user_page,
        "Alerts": show_alert_page,
        "SQL Console": show_sql_console,
    }
else:
    PAGES = {
        "Dashboard": show_home,
        "Timeline": show_timeline_page,
        "Alerts": show_alert_page,
    }
    # Only show patient checker page if present
    if show_patient_checker is not None:
        PAGES = {"Check Drug Safety": show_patient_checker, **PAGES}


with st.sidebar:
    st.markdown("### Navigation")
    selected = st.radio("Go to", list(PAGES.keys()), label_visibility="collapsed")

PAGES[selected]()
