import streamlit as st
import pandas as pd

from database import db_connection as dbc


def _severity_badge(sev: float) -> str:
    if sev is None:
        return ""
    try:
        sev_f = float(sev)
    except Exception:
        return str(sev)

    if sev_f >= 7:
        color = "#ff453a"
        label = "HIGH"
    elif sev_f >= 4:
        color = "#ff9f0a"
        label = "MOD"
    else:
        color = "#32d74b"
        label = "LOW"

    return (
        f"<span style='display:inline-block;padding:4px 10px;border-radius:999px;"
        f"background:{color};color:#000;font-weight:800;font-size:12px;'>"
        f"{label} · {sev_f:.1f}/10</span>"
    )


def show_alert_page():
    st.markdown(
        """
        <div style="padding:16px;border:1px solid rgba(255,255,255,0.08);border-radius:18px;
                    background:rgba(255,255,255,0.04);margin-bottom:14px;">
            <div style="font-size:20px;font-weight:800;">Alerts</div>
            <div style="opacity:0.8;margin-top:6px;">
                Notifications for DB interactions and AI predictions (plus doctor approval/denial).
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    user_id = st.session_state.get("user_id")
    if not user_id:
        st.error("Not logged in.")
        return

    if not hasattr(dbc, "list_recent_alerts"):
        st.error("Backend missing list_recent_alerts().")
        return

    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("Recent Alerts")
    with c2:
        if hasattr(dbc, "mark_alerts_read_for_user"):
            if st.button("Mark all as read", key="alerts_mark_all_read", use_container_width=True):
                dbc.mark_alerts_read_for_user(user_id)
                st.success("Marked all as read.")
                st.rerun()

    alerts = dbc.list_recent_alerts(user_id, limit=100)
    # alerts could be ORM rows or dicts
    rows = []
    for a in alerts:
        if isinstance(a, dict):
            rows.append(a)
        else:
            rows.append({
                "alert_id": getattr(a, "alert_id", None),
                "message": getattr(a, "message", None),
                "severity_score": getattr(a, "severity_score", None),
                "status": getattr(a, "status", None),
                "created_at": str(getattr(a, "created_at", "")),
            })

    if not rows:
        st.info("No alerts yet.")
        return

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Why was I alerted?")

    alert_ids = [r.get("alert_id") for r in rows if r.get("alert_id") is not None]
    pick = st.selectbox("Select alert", ["—"] + alert_ids, key="alert_pick_id")

    if pick != "—":
        if not hasattr(dbc, "get_alert_explanation"):
            st.error("Backend missing get_alert_explanation().")
            return

        info = dbc.get_alert_explanation(pick)
        if not info:
            st.error("No explanation found for this alert.")
            return

        st.markdown(f"**Severity:** {_severity_badge(info.get('severity_score', 0))}", unsafe_allow_html=True)
        st.write(f"**Message:** {info.get('message','')}")
        st.write(f"**Created:** {info.get('created_at','')}")

        if info.get("source") == "database":
            st.write("**Source:** Known DB interaction")
        elif info.get("source") == "ai":
            st.write("**Source:** AI suggestion (prototype)")
            st.warning("AI can be incorrect. Doctor decision should be followed.")

        with st.expander("Details"):
            for k, v in info.items():
                st.write(f"**{k}**: {v}")
