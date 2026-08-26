"""Page : simulateur what-if sur les actions de rétention."""

from __future__ import annotations

import interface.bootstrap  # noqa: F401
import pandas as pd
import streamlit as st

from interface.services import (
    AVAILABLE_ACTIONS,
    fetch_persona,
    load_persona_table,
    refresh_scenarios,
    run_what_if,
)
from interface.style import page_setup

page_setup(
    "Simulateur",
    "Tester une offre sans écraser la recommandation (clone du jumeau)",
)

table = load_persona_table()
ids = table.loc[table["scored"], "customer_id"].tolist() if not table.empty else []
if not ids:
    st.warning(
        "Aucun client scorés. Passe d’abord par **Fiche client** et lance l’orchestrateur."
    )
    st.stop()

default = st.session_state.get("selected_customer_id", ids[0])
if default not in ids:
    default = ids[0]

customer_id = st.selectbox("Client scorés", ids, index=ids.index(default))
persona = fetch_persona(customer_id)
st.metric("Score actuel", f"{float(persona.churn_risk_score):.3f}")

action = st.selectbox("Action à simuler", AVAILABLE_ACTIONS)

c1, c2 = st.columns(2)
with c1:
    do_one = st.button("Simuler cette action", type="primary", use_container_width=True)
with c2:
    do_all = st.button("Recalculer tous les scénarios", use_container_width=True)

if do_one:
    try:
        result = run_what_if(customer_id, action)
        st.session_state["sim_result"] = result
    except Exception as exc:
        st.error(str(exc))

if do_all:
    with st.spinner("Simulation de toutes les actions…"):
        try:
            scenarios = refresh_scenarios(customer_id)
            st.session_state["sim_all"] = scenarios
            st.success(f"{len(scenarios)} scénario(s) applicable(s)")
        except Exception as exc:
            st.error(str(exc))

if "sim_result" in st.session_state:
    r = st.session_state["sim_result"]
    st.subheader("Résultat")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Avant", f"{r['score_before']:.3f}")
    m2.metric("Après", f"{r['score_after']:.3f}")
    m3.metric("Δ risque", f"{r['delta']:+.3f}")
    m4.metric("Coût relatif", f"{r['cost']:.1f}")
    if not r["applied"]:
        st.info("Action non applicable pour ce profil (no-op).")

if "sim_all" in st.session_state:
    st.subheader("Tous les scénarios")
    st.dataframe(
        pd.DataFrame(st.session_state["sim_all"]),
        use_container_width=True,
        hide_index=True,
    )
elif persona.simulation_scenarios:
    st.subheader("Scénarios déjà stockés sur le Persona")
    st.dataframe(
        pd.DataFrame(persona.simulation_scenarios),
        use_container_width=True,
        hide_index=True,
    )

st.caption(
    "Le simulateur clone le Persona : le profil réel (contrat, paiement) n’est pas modifié "
    "sauf si tu recalcules et sauvegardes la liste des scénarios."
)
