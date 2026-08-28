"""Page : lancer l’orchestrateur en batch sur les clients les plus risqués."""

from __future__ import annotations

import interface.bootstrap  # noqa: F401
import pandas as pd
import streamlit as st

from config.settings import CHURN_RISK_THRESHOLD
from interface.services import can_write, load_persona_table, run_batch_orchestrator
from interface.style import page_setup, section

page_setup(
    "Batch orchestrateur",
    "Scorer / décider / générer pour les N clients les plus risqués.",
)

if not can_write():
    st.warning("Rôle reader : le batch est désactivé.")
    st.stop()

table = load_persona_table()
if table.empty:
    st.warning("Warehouse vide.")
    st.stop()

candidates = table.copy()
section("Paramètres du batch")
only_unscored = st.toggle("Prioriser les non scorés", value=False)
min_risk = st.slider(
    "Score minimum (si déjà scorés)",
    0.0,
    1.0,
    float(CHURN_RISK_THRESHOLD),
    0.05,
)
n = st.number_input("Nombre de clients", min_value=1, max_value=50, value=5, step=1)
persist = st.toggle("Sauvegarder (SQLite + Supabase)", value=True)

if only_unscored:
    pool = candidates.loc[~candidates["scored"]].head(int(n))
else:
    pool = (
        candidates.loc[
            candidates["scored"]
            & (candidates["churn_risk_score"] >= min_risk)
        ]
        .sort_values("churn_risk_score", ascending=False)
        .head(int(n))
    )
    if pool.empty:
        # fall back: top by any score / unscored first for bootstrap
        pool = candidates.sort_values(
            by=["scored", "churn_risk_score"],
            ascending=[True, False],
            na_position="first",
        ).head(int(n))

section(f"Sélection ({len(pool)})")
st.dataframe(
    pool[
        [
            "customer_id",
            "churn_risk_score",
            "ops_status",
            "channel",
            "has_message",
        ]
    ].rename(
        columns={
            "customer_id": "Client",
            "churn_risk_score": "Risque",
            "ops_status": "File",
            "channel": "Canal",
            "has_message": "Message",
        }
    ),
    use_container_width=True,
    hide_index=True,
)

ids = pool["customer_id"].tolist()
if st.button("Lancer le batch", type="primary", disabled=not ids):
    progress = st.progress(0.0)
    results = []
    for i, cid in enumerate(ids, start=1):
        with st.spinner(f"{cid}…"):
            chunk = run_batch_orchestrator([cid], persist=persist)
            results.extend(chunk)
        progress.progress(i / len(ids))
    st.session_state["batch_results"] = results
    st.success(f"Batch terminé — {len(results)} client(s)")

if "batch_results" in st.session_state:
    section("Résultats")
    rows = []
    for item in st.session_state["batch_results"]:
        action = item.get("action") or {}
        persona = item.get("persona")
        rows.append(
            {
                "Client": item.get("customer_id"),
                "Statut": item.get("status") or item.get("error"),
                "Score": getattr(persona, "churn_risk_score", None) if persona else None,
                "Offre": action.get("action") if isinstance(action, dict) else None,
                "Canal": getattr(persona, "contact_channel", None) if persona else None,
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

st.caption(
    "Le batch peut être long (sentiment + ML + LLM). Commence avec N=3–5 pour un essai."
)
