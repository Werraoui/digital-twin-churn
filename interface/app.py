"""Point d'entrée Streamlit — tableau de bord Digital Twin Churn."""

from __future__ import annotations

import interface.bootstrap  # noqa: F401
import streamlit as st

from config.settings import CALL_RISK_THRESHOLD, CHURN_RISK_THRESHOLD
from interface.services import clear_persona_cache, load_persona_table
from interface.style import page_setup

page_setup(
    "Twin Churn",
    "Digital Twin client · prédiction du churn · rétention guidée",
)

st.sidebar.markdown("### Navigation")
st.sidebar.caption("Clients à risque · Fiche client · Simulateur")

if st.sidebar.button("Rafraîchir les données", use_container_width=True):
    clear_persona_cache()
    st.rerun()

with st.spinner("Chargement du warehouse…"):
    table = load_persona_table()

n_total = len(table)
n_scored = int(table["scored"].sum()) if n_total else 0
n_high = (
    int((table["churn_risk_score"] >= CHURN_RISK_THRESHOLD).sum())
    if n_scored
    else 0
)
n_critical = (
    int((table["churn_risk_score"] >= CALL_RISK_THRESHOLD).sum())
    if n_scored
    else 0
)
n_messages = int(table["has_message"].sum()) if n_total else 0

st.markdown(
    f"""
<div class="metric-strip">
  <div class="metric-item"><div class="label">Personas</div><div class="value">{n_total}</div></div>
  <div class="metric-item"><div class="label">Scorés</div><div class="value">{n_scored}</div></div>
  <div class="metric-item"><div class="label">Risque ≥ {CHURN_RISK_THRESHOLD}</div><div class="value">{n_high}</div></div>
  <div class="metric-item"><div class="label">Messages prêts</div><div class="value">{n_messages}</div></div>
</div>
""",
    unsafe_allow_html=True,
)

left, right = st.columns((1.4, 1))
with left:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Comment ça marche")
    st.markdown(
        """
1. **Warehouse** — Personas déjà construits par l’Agent Données  
2. **Orchestrateur** — Sentiment → Prédiction → Simulation → Décision → Génération  
3. **Décision** — une offre + un canal (`call` **ou** `email`)  
4. **Interface** — suivre les clients à risque et lancer le parcours  
        """
    )
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Seuils")
    st.markdown(
        f"""
- **Intervention** : score ≥ **{CHURN_RISK_THRESHOLD}**  
- **Appel** : score ≥ **{CALL_RISK_THRESHOLD}**  
- Sinon : email  
- Sous {CHURN_RISK_THRESHOLD} : aucune action  
        """
    )
    st.caption(f"Clients en zone critique (appel) : **{n_critical}**")
    st.markdown("</div>", unsafe_allow_html=True)

if n_scored:
    preview = table.loc[table["scored"]].head(8)[
        ["customer_id", "churn_risk_score", "sentiment", "recommended_action", "channel"]
    ]
    st.subheader("Aperçu des clients scorés")
    st.dataframe(preview, use_container_width=True, hide_index=True)
else:
    st.info(
        "Aucun client scorés pour l’instant. Ouvre **Fiche client**, choisis un ID "
        "(ex. `7590-VHVEG`) et lance l’orchestrateur."
    )
