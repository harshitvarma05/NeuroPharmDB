import streamlit as st
from database.db_connection import (
    list_recent_alerts,
    count_unread_alerts_for_user,
    mark_alerts_read_for_user,
)

def apply_base_style():
    st.markdown(
        """
        <style>
        /* ===============================
           NEVER-ALLOW SIDEBAR COLLAPSE
           =============================== */

        /* Force sidebar to always be visible */
        section[data-testid="stSidebar"] {
            min-width: 18rem !important;
            max-width: 18rem !important;
            width: 18rem !important;
            transform: translateX(0px) !important;
            visibility: visible !important;
        }

        /* Disable collapse animation / hiding */
        section[data-testid="stSidebar"][aria-expanded="false"] {
            transform: translateX(0px) !important;
            visibility: visible !important;
        }

        /* Hide the hamburger toggle completely */
        button[data-testid="collapsedControl"] {
            display: none !important;
        }

        /* ===============================
           HEADER: keep minimal, no deploy
           =============================== */

        header[data-testid="stHeader"] {
            background: transparent !important;
            border-bottom: none !important;
            height: 3rem !important;
        }

        /* Remove Deploy / toolbar buttons */
        header [data-testid="stToolbar"] {
            display: none !important;
        }

        /* Remove Streamlit menu + footer */
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }

        /* ===============================
           LAYOUT POLISH
           =============================== */

        .block-container {
            padding-top: 1.25rem !important;
        }

        /* Apple-style cards (keeps your UI consistent) */

        .apple-title {
            font-size: 1.1rem;
            font-weight: 650;
        }

        .apple-subtitle {
            font-size: 0.85rem;
            opacity: 0.75;
        }
        /* ===== Apple-ish Dark Mode (Readable) ===== */
        .stApp {
          background:
            radial-gradient(1200px 800px at 18% 0%, rgba(10,132,255,0.22), transparent 60%),
            radial-gradient(900px 600px at 82% 10%, rgba(48,209,88,0.10), transparent 55%),
            #0B0F14;
          color: #F3F6FF;
        }

        .block-container{
          padding-top: 1.0rem;
          padding-bottom: 2rem;
          max-width: 1200px;
        }

        section[data-testid="stSidebar"]{
          background: rgba(15, 23, 42, 0.78);
          border-right: 1px solid rgba(255,255,255,0.08);
          backdrop-filter: blur(18px);
        }

        
        .apple-title{
          font-size: 26px;
          font-weight: 650;
          letter-spacing: -0.02em;
          margin: 0;
          color: #F3F6FF;
        }
        .apple-subtitle{
          font-size: 13px;
          color: rgba(243,246,255,0.75);
          margin-top: 4px;
        }

        /* Labels readability */
        label, .stMarkdown, .stTextInput label, .stSelectbox label, .stTextArea label {
          color: rgba(243,246,255,0.92) !important;
        }

        /* Inputs */
        div[data-baseweb="input"] > div,
        div[data-baseweb="textarea"] > div,
        div[data-baseweb="select"] > div{
          border-radius: 14px !important;
          background: rgba(255,255,255,0.06) !important;
          border: 1px solid rgba(255,255,255,0.10) !important;
        }

        /* Buttons */
        .stButton button, .stFormSubmitButton button{
          border-radius: 14px !important;
          border: 1px solid rgba(255,255,255,0.12) !important;
          background: rgba(255,255,255,0.08) !important;
          color: #F3F6FF !important;
        }
        .stButton button:hover, .stFormSubmitButton button:hover{
          background: rgba(255,255,255,0.11) !important;
          transform: translateY(-1px);
        }

        /* Dataframes */
        [data-testid="stDataFrame"]{
          border-radius: 16px;
          overflow: hidden;
          border: 1px solid rgba(255,255,255,0.10);
        }
         /* Hide Streamlit deploy button + menu */
        header [data-testid="stToolbar"] {
            display: none !important;
        }

        /* Hide top right menu (⋮) */
        #MainMenu {
            visibility: hidden;
        }

        /* Hide footer */
        footer {
            visibility: hidden;
        }

        /* Reduce top padding caused by header */
        .block-container {
            padding-top: 1.5rem !important;
        }
        /* --- Remove Streamlit header bar completely --- */
    header[data-testid="stHeader"] {
        display: none !important;
    }

    /* Older/alternate header selector */
    header.stAppHeader {
        display: none !important;
    }

    /* Remove extra top padding after header disappears */
    .block-container {
        padding-top: 1.25rem !important;
    }
    /* Severity pill badges */
.sev-pill{
  display:inline-block;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 650;
  letter-spacing: .01em;
  border: 1px solid rgba(255,255,255,0.14);
  background: rgba(255,255,255,0.06);
}
.sev-low{ color: rgba(48,209,88,0.95); }
.sev-med{ color: rgba(255,214,10,0.95); }
.sev-high{ color: rgba(255,69,58,0.95); }

    /* Optional: hide Streamlit menu + footer */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
        hr{ border: none; border-top: 1px solid rgba(255,255,255,0.08); }
    
        </style>
        """,
        unsafe_allow_html=True
    )

def severity_badge(score):
    if score is None:
        return '<span class="sev-pill">—</span>'
    s = float(score)
    if s >= 7.0:
        cls = "sev-high"
        label = f"High • {s:.1f}"
    elif s >= 4.0:
        cls = "sev-med"
        label = f"Medium • {s:.1f}"
    else:
        cls = "sev-low"
        label = f"Low • {s:.1f}"
    return f'<span class="sev-pill {cls}">{label}</span>'


def login_screen(app_name: str):
    left, mid, right = st.columns([1.2, 1.6, 1.2])
    with mid:
        st.markdown(
            f"""
            <div class="apple-card">
              <div class="apple-title">{app_name}</div>
              <div class="apple-subtitle">Sign in using User ID and Email</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.write("")

        user_id = st.text_input("User ID", placeholder="e.g., U001")
        email = st.text_input("Email", placeholder="e.g., user@email.com")

        if st.button("Login", use_container_width=True):
            return user_id.strip(), email.strip()
        return None, None

def topbar(app_name: str, user_id: str):
    unread = count_unread_alerts_for_user(user_id)

    c1, c2, c3 = st.columns([7, 2, 2])
    with c1:
        st.markdown(
            f"""
            <div class="apple-card">
              <div class="apple-title">{app_name}</div>
              <div class="apple-subtitle">Logged in as <b>{user_id}</b></div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c2:
        # Apple-like bell dropdown
        with st.popover(f"{unread}"):
            st.markdown("**Notifications**")
            alerts = list_recent_alerts(user_id, limit=10)
            if not alerts:
                st.caption("No notifications yet.")
            else:
                for a in alerts:
                    status = "! Unread" if a["status"] == "unread" else "⬛ Read"
                    st.write(f"{status} — {a['message']}")
                    st.caption(a["created_at"])
                if st.button("Mark all as read", key="topbar_mark_all_read"):
                    mark_alerts_read_for_user(user_id)
                    st.rerun()

    with c3:
        st.markdown('<div class="apple-card">', unsafe_allow_html=True)
        if st.button("Logout", key="topbar_logout"):
            st.session_state.logged_in = False
            for k in ["user_id", "user_name"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
