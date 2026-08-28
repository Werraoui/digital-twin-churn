"""Optional password gate for the Streamlit workspace."""

from __future__ import annotations

import streamlit as st

from config.settings import UI_OPERATOR, UI_PASSWORD, UI_ROLE
from src.integrations import supabase_store


def require_login() -> None:
    """Block the app until UI_PASSWORD is entered (skipped if unset)."""
    if not UI_PASSWORD:
        st.session_state["ui_authenticated"] = True
        return
    if st.session_state.get("ui_authenticated"):
        return

    st.markdown("### Accès espace rétention")
    st.caption("Authentification locale (UI_PASSWORD).")
    pwd = st.text_input("Mot de passe", type="password")
    if st.button("Entrer", type="primary"):
        if pwd == UI_PASSWORD:
            st.session_state["ui_authenticated"] = True
            st.rerun()
        st.error("Mot de passe incorrect.")
    st.stop()


def sidebar_workspace_meta() -> None:
    from config.settings import PERSONA_BACKEND, PERSONA_READ_FROM

    conf = supabase_store.is_configured()
    st.markdown("**Twin Churn**")
    st.caption(f"{UI_OPERATOR} · rôle `{UI_ROLE}`")
    if conf and PERSONA_BACKEND == "supabase":
        st.caption(f"Warehouse : Supabase (lecture `{PERSONA_READ_FROM}`)")
    elif conf:
        st.caption(f"Backend `{PERSONA_BACKEND}` · Supabase OK")
    else:
        st.caption("Warehouse : SQLite local")