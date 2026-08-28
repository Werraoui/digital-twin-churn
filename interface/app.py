"""Point d'entrée Streamlit — tableau de bord Digital Twin Churn."""

from __future__ import annotations

import bootstrap  # noqa: F401
import streamlit as st

from config.settings import CALL_RISK_THRESHOLD, CHURN_RISK_THRESHOLD
from interface.services import (
    clear_persona_cache,
    load_persona_table,
    load_runs,
    pull_from_supabase,
    supabase_status,
)
from interface.style import page_setup, section
from src.persona.ops import OPS_LABELS

page_setup(
    "Vue d’ensemble",
    "Pilotage du churn : Personas, file de travail, alertes et synchronisation warehouse.",
)

status = supabase_status()
with st.sidebar:
    if st.button("Rafraîchir les données", use_container_width=True):
        clear_persona_cache()
        st.rerun()
    if status["configured"] and st.button("Sync depuis Supabase", use_container_width=True):
        n = pull_from_supabase()
        st.success(f"{n} Persona(s) synchronisé(s)")
        st.rerun()
    st.divider()
    st.caption("Pages : risque · fiche · simulateur · batch · analytics")

with st.spinner("Chargement du warehouse…"):
    table = load_persona_table()

n_total = len(table)
n_scored = int(table["scored"].sum()) if n_total else 0
n_high = int((table["churn_risk_score"] >= CHURN_RISK_THRESHOLD).sum()) if n_scored else 0
n_critical = int((table["churn_risk_score"] >= CALL_RISK_THRESHOLD).sum()) if n_scored else 0
n_messages = int(table["has_message"].sum()) if n_total else 0
n_to_call = int((table["ops_status"] == "to_call").sum()) if n_total else 0
n_to_email = int((table["ops_status"] == "to_email").sum()) if n_total else 0
n_contacted = int((table["ops_status"] == "contacted").sum()) if n_total else 0
n_sent = int((table["message_status"] == "sent").sum()) if n_total else 0
n_validated = int((table["message_status"] == "validated").sum()) if n_total else 0

# Alerts
critical_open = table.loc[
    (table["churn_risk_score"] >= CALL_RISK_THRESHOLD)
    & (table["ops_status"].isin(["to_call", "to_email", "none", "postponed"]))
] if n_total else table
if len(critical_open):
    st.warning(
        f"**Alerte** : {len(critical_open)} client(s) critique(s) (score ≥ {CALL_RISK_THRESHOLD}) "
        "pas encore marqués contactés."
    )

st.markdown(
    f"""
<div class="metric-strip">
  <div class="metric-item">
    <div class="label">Personas</div>
    <div class="value">{n_total:,}</div>
    <div class="hint">backend {status.get("backend", "?")} · lecture {status.get("read_from", "?")}</div>
  </div>
  <div class="metric-item">
    <div class="label">À traiter</div>
    <div class="value">{n_high:,}</div>
    <div class="hint">score ≥ {CHURN_RISK_THRESHOLD} · critiques {n_critical}</div>
  </div>
  <div class="metric-item">
    <div class="label">File ops</div>
    <div class="value">{n_to_call + n_to_email}</div>
    <div class="hint">appel {n_to_call} · email {n_to_email}</div>
  </div>
  <div class="metric-item">
    <div class="label">Messages</div>
    <div class="value">{n_messages:,}</div>
    <div class="hint">validés {n_validated} · envoyés {n_sent} · contactés {n_contacted}</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

left, right = st.columns(2, gap="medium")
with left:
    st.markdown(
        """
<div class="panel">
  <div class="panel-title">Parcours opérationnel</div>
  <ol class="steps">
    <li><strong>Clients à risque</strong> — filtrer la file et prioriser.</li>
    <li><strong>Fiche client</strong> — lancer l’orchestrateur, valider offre / message.</li>
    <li><strong>Batch</strong> — scorer les N plus risqués d’un coup.</li>
    <li><strong>Analytics</strong> — distribution, SHAP, funnel messages.</li>
  </ol>
</div>
""",
        unsafe_allow_html=True,
    )

with right:
    st.markdown(
        f"""
<div class="panel">
  <div class="panel-title">Règles de priorité</div>
  <div class="kv">
    <div class="kv-row"><div class="kv-key">Pas d’action</div><div class="kv-val">score &lt; {CHURN_RISK_THRESHOLD}</div></div>
    <div class="kv-row"><div class="kv-key">Email</div><div class="kv-val">{CHURN_RISK_THRESHOLD} ≤ score &lt; {CALL_RISK_THRESHOLD}</div></div>
    <div class="kv-row"><div class="kv-key">Appel</div><div class="kv-val">score ≥ {CALL_RISK_THRESHOLD}</div></div>
    <div class="kv-row"><div class="kv-key">Persistance</div><div class="kv-val">SQLite + dual-write Supabase</div></div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

section("File de travail")
if n_total:
    queue = (
        table.loc[table["ops_status"].isin(["to_call", "to_email", "postponed"])]
        .head(15)[
            [
                "customer_id",
                "churn_risk_score",
                "ops_status",
                "channel",
                "recommended_action",
                "message_status",
            ]
        ]
        .assign(ops_status=lambda d: d["ops_status"].map(lambda x: OPS_LABELS.get(x, x)))
        .rename(
            columns={
                "customer_id": "Client",
                "churn_risk_score": "Risque",
                "ops_status": "Statut",
                "channel": "Canal",
                "recommended_action": "Offre",
                "message_status": "Message",
            }
        )
    )
    if queue.empty:
        st.info("Aucune entrée dans la file (to_call / to_email / postponed).")
    else:
        st.dataframe(queue, use_container_width=True, hide_index=True)

section("Derniers runs orchestrateur")
runs = load_runs(limit=12)
if runs.empty:
    st.caption("Aucun historique pour l’instant.")
else:
    show = runs[
        ["created_at", "customer_id", "status", "score_before", "score_after", "operator"]
    ].rename(
        columns={
            "created_at": "Quand",
            "customer_id": "Client",
            "status": "Statut",
            "score_before": "Avant",
            "score_after": "Après",
            "operator": "Opérateur",
        }
    )
    st.dataframe(show, use_container_width=True, hide_index=True)

section("Clients scorés (aperçu)")
if n_scored:
    preview = (
        table.loc[table["scored"]]
        .head(10)[
            [
                "customer_id",
                "churn_risk_score",
                "sentiment",
                "ops_status",
                "recommended_action",
                "channel",
                "has_message",
            ]
        ]
        .rename(
            columns={
                "customer_id": "Client",
                "churn_risk_score": "Risque",
                "sentiment": "Sentiment",
                "ops_status": "File",
                "recommended_action": "Offre",
                "channel": "Canal",
                "has_message": "Message",
            }
        )
    )
    st.dataframe(
        preview,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Risque": st.column_config.NumberColumn(format="%.3f"),
            "Message": st.column_config.CheckboxColumn(),
        },
    )
else:
    st.info(
        "Aucun client scorés. Ouvre **Fiche client** ou **Batch** pour lancer l’orchestrateur."
    )
