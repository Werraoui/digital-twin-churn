"""Page : clients triés par risque de churn + file de travail."""

from __future__ import annotations

import interface.bootstrap  # noqa: F401
import streamlit as st

from config.settings import CHURN_RISK_THRESHOLD
from interface.services import can_write, load_persona_table, risk_band, update_ops
from interface.style import page_setup, section
from src.persona.ops import MESSAGE_LABELS, OPS_LABELS, OPS_STATUSES

page_setup(
    "Clients à risque",
    "Filtrer, exporter et prioriser la file de rétention.",
)

table = load_persona_table()
if table.empty:
    st.warning("Warehouse vide. Lance d’abord le Data Agent.")
    st.stop()

section("Filtres")
f1, f2, f3, f4 = st.columns(4)
with f1:
    only_scored = st.toggle("Scorés uniquement", value=True)
with f2:
    min_risk = st.slider(
        "Score minimum",
        min_value=0.0,
        max_value=1.0,
        value=float(CHURN_RISK_THRESHOLD),
        step=0.05,
    )
with f3:
    max_risk = st.slider("Score maximum", 0.0, 1.0, 1.0, 0.05)
with f4:
    st.metric("Seuil d’intervention", f"{CHURN_RISK_THRESHOLD:.2f}")

f5, f6, f7, f8 = st.columns(4)
contracts = sorted({c for c in table["contract"].dropna().unique()})
sentiments = sorted({s for s in table["sentiment"].dropna().unique()})
channels = sorted({c for c in table["channel"].dropna().unique()})
with f5:
    contract_f = st.multiselect("Contrat", contracts)
with f6:
    sentiment_f = st.multiselect("Sentiment", sentiments)
with f7:
    channel_f = st.multiselect("Canal", channels)
with f8:
    ops_f = st.multiselect(
        "Statut file",
        list(OPS_STATUSES),
        format_func=lambda x: OPS_LABELS.get(x, x),
    )

t1, t2 = st.columns(2)
with t1:
    tenure_min, tenure_max = st.slider(
        "Ancienneté (mois)",
        0,
        int(max(table["tenure"].fillna(0).max(), 72)),
        (0, int(max(table["tenure"].fillna(0).max(), 72))),
    )
with t2:
    msg_only = st.toggle("Avec message uniquement", value=False)

view = table.copy()
if only_scored:
    view = view.loc[view["scored"]]
view = view.loc[
    view["churn_risk_score"].isna()
    | (
        (view["churn_risk_score"] >= min_risk)
        & (view["churn_risk_score"] <= max_risk)
    )
]
if contract_f:
    view = view.loc[view["contract"].isin(contract_f)]
if sentiment_f:
    view = view.loc[view["sentiment"].isin(sentiment_f)]
if channel_f:
    view = view.loc[view["channel"].isin(channel_f)]
if ops_f:
    view = view.loc[view["ops_status"].isin(ops_f)]
if msg_only:
    view = view.loc[view["has_message"]]
view = view.loc[
    view["tenure"].isna()
    | ((view["tenure"] >= tenure_min) & (view["tenure"] <= tenure_max))
]

section(f"Résultats ({len(view)})")
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
        "ops_status",
        "recommended_action",
        "channel",
        "message_status",
        "has_message",
    ]
].copy()
display["niveau"] = display["churn_risk_score"].map(risk_band)
display["ops_status"] = display["ops_status"].map(lambda x: OPS_LABELS.get(x, x))
display["message_status"] = display["message_status"].map(
    lambda x: MESSAGE_LABELS.get(x, x)
)
display = display.rename(
    columns={
        "customer_id": "Client",
        "churn_risk_score": "Risque",
        "sentiment": "Sentiment",
        "contract": "Contrat",
        "tenure": "Ancienneté",
        "monthly_charges": "Mensuel",
        "ops_status": "File",
        "recommended_action": "Offre",
        "channel": "Canal",
        "message_status": "Msg",
        "has_message": "Message",
        "niveau": "Niveau",
    }
)

st.dataframe(
    display,
    use_container_width=True,
    hide_index=True,
    height=420,
    column_config={
        "Risque": st.column_config.ProgressColumn(
            "Risque",
            min_value=0.0,
            max_value=1.0,
            format="%.2f",
        ),
        "Mensuel": st.column_config.NumberColumn(format="%.2f"),
        "Message": st.column_config.CheckboxColumn(),
    },
)

csv = display.to_csv(index=False).encode("utf-8")
st.download_button(
    "Exporter CSV (priorisation)",
    data=csv,
    file_name="clients_a_risque.csv",
    mime="text/csv",
    use_container_width=True,
)

section("Actions rapides")
c1, c2, c3 = st.columns([2, 1, 1])
with c1:
    choice = st.selectbox("Client à ouvrir", display["Client"].tolist())
with c2:
    st.markdown("**Fiche**")
    if st.button("Ouvrir la fiche", type="primary", use_container_width=True):
        st.session_state["selected_customer_id"] = choice
        st.switch_page("pages/2_Fiche_client.py")
with c3:
    new_ops = st.selectbox(
        "Nouveau statut file",
        ["to_call", "to_email", "contacted", "postponed", "none"],
        format_func=lambda x: OPS_LABELS.get(x, x),
    )
    if st.button("Mettre à jour le statut", use_container_width=True, disabled=not can_write()):
        try:
            update_ops(choice, ops_status=new_ops)
            st.success("Statut mis à jour")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))
