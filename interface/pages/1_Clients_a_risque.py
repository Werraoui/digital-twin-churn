"""Page : clients triés par risque de churn."""

from __future__ import annotations

import interface.bootstrap  # noqa: F401
import streamlit as st

from config.settings import CHURN_RISK_THRESHOLD
from interface.services import load_persona_table, risk_band
from interface.style import page_setup

page_setup("Clients à risque", "Liste triée par score de churn décroissant")

table = load_persona_table()
if table.empty:
    st.warning("Warehouse vide. Lance d’abord le Data Agent.")
    st.stop()

only_scored = st.toggle("Uniquement les clients scorés", value=True)
min_risk = st.slider(
    "Score minimum",
    min_value=0.0,
    max_value=1.0,
    value=float(CHURN_RISK_THRESHOLD),
    step=0.05,
)

view = table.copy()
if only_scored:
    view = view.loc[view["scored"]]
view = view.loc[
    view["churn_risk_score"].isna() | (view["churn_risk_score"] >= min_risk)
]

st.caption(f"{len(view)} client(s) affiché(s)")

if view.empty:
    st.info("Aucun client ne correspond aux filtres.")
    st.stop()

display = view[
    [
        "customer_id",
        "churn_risk_score",
        "sentiment",
        "contract",
        "tenure",
        "monthly_charges",
        "recommended_action",
        "channel",
        "has_message",
    ]
].copy()
display["bande"] = display["churn_risk_score"].map(risk_band)

st.dataframe(
    display,
    use_container_width=True,
    hide_index=True,
    column_config={
        "churn_risk_score": st.column_config.ProgressColumn(
            "Risque",
            min_value=0.0,
            max_value=1.0,
            format="%.2f",
        ),
        "has_message": st.column_config.CheckboxColumn("Message"),
    },
)

choice = st.selectbox("Ouvrir la fiche d’un client", display["customer_id"].tolist())
if st.button("Aller à la fiche client", type="primary"):
    st.session_state["selected_customer_id"] = choice
    st.switch_page("pages/2_Fiche_client.py")
