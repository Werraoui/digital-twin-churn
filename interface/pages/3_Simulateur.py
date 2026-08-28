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
from interface.style import page_setup, section

page_setup(
    "Simulateur",
    "Comparer l’effet d’une offre sur le score, sans modifier le profil client réel.",
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

section("Paramètres")
p1, p2, p3 = st.columns([1.4, 1.6, 1])
with p1:
    customer_id = st.selectbox("Client scorés", ids, index=ids.index(default))
with p2:
    action = st.selectbox("Action à tester", AVAILABLE_ACTIONS)
with p3:
    persona = fetch_persona(customer_id)
    st.metric("Score actuel", f"{float(persona.churn_risk_score):.3f}")

b1, b2 = st.columns(2)
with b1:
    do_one = st.button("Simuler cette action", type="primary", use_container_width=True)
with b2:
    do_all = st.button("Recalculer tous les scénarios", use_container_width=True)

if do_one:
    try:
        st.session_state["sim_result"] = run_what_if(customer_id, action)
    except Exception as exc:
        st.error(str(exc))

if do_all:
    with st.spinner("Simulation de toutes les actions…"):
        try:
            scenarios = refresh_scenarios(customer_id)
            st.session_state["sim_all"] = scenarios
            st.success(f"{len(scenarios)} scénario(s) applicable(s) enregistré(s)")
        except Exception as exc:
            st.error(str(exc))

if "sim_result" in st.session_state:
    r = st.session_state["sim_result"]
    section("Résultat de la simulation")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Avant", f"{r['score_before']:.3f}")
    m2.metric("Après", f"{r['score_after']:.3f}")
    m3.metric("Δ risque", f"{r['delta']:+.3f}")
    m4.metric("Coût relatif", f"{r['cost']:.1f}")
    if not r["applied"]:
        st.info("Action non applicable pour ce profil (aucun changement).")

section("Scénarios")
if "sim_all" in st.session_state:
    frame = pd.DataFrame(st.session_state["sim_all"])
elif persona.simulation_scenarios:
    frame = pd.DataFrame(persona.simulation_scenarios)
else:
    frame = pd.DataFrame()

if not frame.empty:
    st.dataframe(
        frame.rename(
            columns={
                "action": "Action",
                "applied": "Applicable",
                "score_before": "Avant",
                "score_after": "Après",
                "delta": "Δ",
                "cost": "Coût",
                "delta_per_cost": "Δ / coût",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.caption("Aucun scénario disponible pour ce client.")

st.caption(
    "Le simulateur travaille sur un clone du Persona. "
    "Le contrat / paiement réels ne changent que si tu recalcules et sauvegardes les scénarios."
)
