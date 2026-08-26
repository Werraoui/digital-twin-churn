"""Page : fiche client (Persona, orchestrateur, recommandation, message)."""

from __future__ import annotations

import interface.bootstrap  # noqa: F401
import pandas as pd
import streamlit as st

from interface.services import fetch_persona, load_persona_table, risk_band, run_orchestrator
from interface.style import badge_html, page_setup

page_setup("Fiche client", "Persona · score · scénarios · décision · message")

table = load_persona_table()
ids = table["customer_id"].tolist() if not table.empty else []
default = st.session_state.get("selected_customer_id", "7590-VHVEG")
if default not in ids and ids:
    default = ids[0]

customer_id = st.selectbox(
    "Client",
    options=ids or [default],
    index=(ids.index(default) if default in ids else 0),
)

col_a, col_b = st.columns([1, 1])
with col_a:
    run = st.button("Lancer l’orchestrateur", type="primary", use_container_width=True)
with col_b:
    persist = st.toggle("Sauvegarder dans le warehouse", value=True)

if run:
    with st.spinner(
        "Orchestrateur en cours (prédiction / simulation / décision / génération)…"
    ):
        try:
            result = run_orchestrator(customer_id, persist=persist)
            st.session_state["last_result"] = result
            st.success(f"Terminé — status: {result.get('status')}")
        except Exception as exc:
            st.error(f"Échec : {exc}")
            st.stop()

try:
    persona = fetch_persona(customer_id)
except Exception as exc:
    st.error(f"Impossible de charger le Persona : {exc}")
    st.stop()

band = risk_band(persona.churn_risk_score)
st.markdown(
    f"**Risque** {badge_html(band)} &nbsp; "
    f"score = `{persona.churn_risk_score if persona.churn_risk_score is not None else '—'}`",
    unsafe_allow_html=True,
)

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown("##### Contrat & facturation")
    st.json(
        {
            "contract": persona.contract,
            "billing": persona.billing,
        }
    )
    st.markdown("</div>", unsafe_allow_html=True)
with c2:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown("##### Sentiment")
    st.write(
        {
            "sentiment": persona.sentiment,
            "confidence": persona.sentiment_confidence,
            "emotions": persona.emotions,
            "topics": persona.complaint_topics,
            "review": persona.raw_review_text,
        }
    )
    st.markdown("</div>", unsafe_allow_html=True)
with c3:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown("##### Décision")
    st.write(persona.recommended_action or "Aucune action")
    st.caption(persona.decision_justification or "")
    st.markdown("</div>", unsafe_allow_html=True)

if persona.risk_factors:
    st.subheader("Facteurs SHAP (top)")
    st.dataframe(pd.DataFrame(persona.risk_factors), use_container_width=True, hide_index=True)

scenarios = persona.simulation_scenarios or []
if scenarios:
    st.subheader("Scénarios simulés")
    st.dataframe(pd.DataFrame(scenarios), use_container_width=True, hide_index=True)

st.subheader("Message de rétention")
if persona.retention_message:
    channel = persona.contact_channel or (persona.recommended_action or {}).get("channel")
    st.caption(f"Canal : **{channel}** (un seul : call **ou** email)")
    st.markdown(
        f'<div class="message-box">{persona.retention_message}</div>',
        unsafe_allow_html=True,
    )
else:
    st.info("Pas encore de message. Lance l’orchestrateur pour ce client.")

if persona.rag_context:
    with st.expander("Contexte RAG (tickets)"):
        for i, snippet in enumerate(persona.rag_context, 1):
            st.markdown(f"**Extrait {i}**")
            st.code(snippet)
