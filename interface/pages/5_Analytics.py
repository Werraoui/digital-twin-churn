"""Page analytics : distribution des scores, SHAP global, funnel messages."""

from __future__ import annotations

import interface.bootstrap  # noqa: F401
import pandas as pd
import streamlit as st

from config.settings import CALL_RISK_THRESHOLD, CHURN_RISK_THRESHOLD
from interface.services import global_shap_summary, load_persona_table, load_runs
from interface.style import page_setup, section
from src.persona.ops import MESSAGE_LABELS, OPS_LABELS

page_setup(
    "Analytics",
    "Distribution des risques, facteurs SHAP globaux et funnel rétention.",
)

table = load_persona_table()
if table.empty:
    st.warning("Warehouse vide.")
    st.stop()

scored = table.loc[table["scored"]].copy()

section("Distribution des scores")
if scored.empty:
    st.info("Aucun client scorés.")
else:
    hist = scored[["churn_risk_score"]].rename(columns={"churn_risk_score": "score"})
    st.bar_chart(hist["score"].value_counts(bins=10).sort_index())
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Moyenne", f"{scored['churn_risk_score'].mean():.3f}")
    m2.metric("Médiane", f"{scored['churn_risk_score'].median():.3f}")
    m3.metric(
        "≥ seuil",
        int((scored["churn_risk_score"] >= CHURN_RISK_THRESHOLD).sum()),
    )
    m4.metric(
        "Critiques",
        int((scored["churn_risk_score"] >= CALL_RISK_THRESHOLD).sum()),
    )

section("Top facteurs SHAP (global)")
shap = global_shap_summary(15)
if shap.empty:
    st.caption("Pas encore de risk_factors sur les Personas.")
else:
    st.dataframe(shap, use_container_width=True, hide_index=True)
    st.bar_chart(shap.set_index("Variable")["SHAP moyen |abs|"])

section("Funnel messages & file")
ops_counts = (
    table["ops_status"]
    .fillna("none")
    .map(lambda x: OPS_LABELS.get(x, x))
    .value_counts()
    .rename_axis("Statut")
    .reset_index(name="Nb")
)
msg_counts = (
    table["message_status"]
    .fillna("none")
    .map(lambda x: MESSAGE_LABELS.get(x, x))
    .value_counts()
    .rename_axis("Statut message")
    .reset_index(name="Nb")
)
c1, c2 = st.columns(2)
with c1:
    st.markdown("**File ops**")
    st.dataframe(ops_counts, use_container_width=True, hide_index=True)
with c2:
    st.markdown("**Messages**")
    st.dataframe(msg_counts, use_container_width=True, hide_index=True)

generated = int(table["has_message"].sum())
validated = int((table["message_status"] == "validated").sum())
sent = int((table["message_status"] == "sent").sum())
contacted = int((table["ops_status"] == "contacted").sum())
st.markdown(
    f"""
<div class="metric-strip">
  <div class="metric-item"><div class="label">Générés</div><div class="value">{generated}</div></div>
  <div class="metric-item"><div class="label">Validés</div><div class="value">{validated}</div></div>
  <div class="metric-item"><div class="label">Envoyés</div><div class="value">{sent}</div></div>
  <div class="metric-item"><div class="label">Contactés</div><div class="value">{contacted}</div></div>
</div>
""",
    unsafe_allow_html=True,
)
st.caption(
    "Le churn évité réel nécessite un feedback métier (client resté / parti). "
    "Ici on suit le funnel opérationnel généré → validé → envoyé → contacté."
)

section("Activité récente (runs)")
runs = load_runs(limit=30)
if runs.empty:
    st.caption("Aucun run.")
else:
    st.dataframe(
        runs[
            [
                "created_at",
                "customer_id",
                "status",
                "score_before",
                "score_after",
                "operator",
            ]
        ].rename(
            columns={
                "created_at": "Quand",
                "customer_id": "Client",
                "status": "Statut",
                "score_before": "Avant",
                "score_after": "Après",
                "operator": "Opérateur",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

section("ROI relatif des scénarios (échantillon)")
from src.agents.data_agent.repository import list_personas

roi_rows = []
for persona in list_personas():
    for scen in persona.simulation_scenarios or []:
        if not scen.get("applied"):
            continue
        roi_rows.append(
            {
                "Action": scen.get("action"),
                "Δ": scen.get("delta"),
                "Coût": scen.get("cost"),
                "Δ/coût": scen.get("delta_per_cost"),
            }
        )
if not roi_rows:
    st.caption("Aucun scénario applicable en base.")
else:
    roi = pd.DataFrame(roi_rows)
    agg = (
        roi.groupby("Action", as_index=False)
        .agg({"Δ": "mean", "Coût": "mean", "Δ/coût": "mean"})
        .sort_values("Δ/coût", ascending=False)
    )
    st.dataframe(agg, use_container_width=True, hide_index=True)
