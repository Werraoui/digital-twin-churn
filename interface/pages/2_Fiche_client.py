"""Page : fiche client (Persona, orchestrateur, ops, message)."""

from __future__ import annotations

import copy
import html

import interface.bootstrap  # noqa: F401
import pandas as pd
import streamlit as st

from interface.services import (
    can_write,
    fetch_persona,
    load_persona_table,
    load_runs,
    risk_band,
    run_orchestrator,
    update_ops,
)
from interface.style import badge_html, kv_html, page_setup, section
from src.persona.ops import MESSAGE_LABELS, MESSAGE_STATUSES, OPS_LABELS, OPS_STATUSES

page_setup(
    "Fiche client",
    "Profil, score, scénarios, décision, message et file opérationnelle.",
)

table = load_persona_table()
ids = table["customer_id"].tolist() if not table.empty else []
default = st.session_state.get("selected_customer_id", "7590-VHVEG")
if default not in ids and ids:
    default = ids[0]

top1, top2, top3 = st.columns([2, 1, 1])
with top1:
    customer_id = st.selectbox(
        "Identifiant client",
        options=ids or [default],
        index=(ids.index(default) if default in ids else 0),
    )
with top2:
    persist = st.toggle("Sauvegarder en warehouse", value=True, disabled=not can_write())
with top3:
    st.markdown("**Action**")
    run = st.button(
        "Lancer l’orchestrateur",
        type="primary",
        use_container_width=True,
        disabled=not can_write(),
    )

# Snapshot before run for before/after panel
try:
    before_persona = fetch_persona(customer_id)
except Exception:
    before_persona = None

if run:
    snapshot = {
        "score": before_persona.churn_risk_score if before_persona else None,
        "action": (before_persona.recommended_action or {}).get("action")
        if before_persona
        else None,
        "channel": before_persona.contact_channel if before_persona else None,
        "message": before_persona.retention_message if before_persona else None,
        "ops": before_persona.ops_status if before_persona else None,
    }
    with st.spinner("Orchestrateur en cours…"):
        try:
            result = run_orchestrator(customer_id, persist=persist)
            st.session_state["last_result"] = result
            st.session_state["before_after"] = {
                "before": snapshot,
                "after": {
                    "score": getattr(result.get("persona"), "churn_risk_score", None),
                    "action": (result.get("action") or {}).get("action")
                    if isinstance(result.get("action"), dict)
                    else None,
                    "channel": getattr(result.get("persona"), "contact_channel", None),
                    "message": result.get("message"),
                    "ops": getattr(result.get("persona"), "ops_status", None),
                    "status": result.get("status"),
                },
            }
            msg = result.get("message") or ""
            if msg.startswith("CALL SCRIPT") or msg.startswith("Subject:"):
                st.info(
                    "Message généré en **mode template** (Groq/Gemini indisponible). "
                    "Le pipeline score → simulation → décision a bien tourné."
                )
            st.success(f"Terminé — statut : {result.get('status')}")
        except Exception as exc:
            st.error(f"Échec : {exc}")
            st.stop()

try:
    persona = fetch_persona(customer_id)
except Exception as exc:
    st.error(f"Impossible de charger le Persona : {exc}")
    st.stop()

band = risk_band(persona.churn_risk_score)
score_txt = (
    f"{float(persona.churn_risk_score):.3f}"
    if persona.churn_risk_score is not None
    else "—"
)
action = persona.recommended_action or {}
channel = persona.contact_channel or action.get("channel") or "—"

st.markdown(
    f"""
<div class="risk-line">
  <span class="risk-meta"><strong>Niveau</strong></span>
  {badge_html(band)}
  <span class="risk-meta"><strong>Score</strong></span>
  <span class="risk-score">{html.escape(score_txt)}</span>
  <span class="risk-meta">Offre : <strong>{html.escape(str(action.get('action') or '—'))}</strong>
  · Canal : <strong>{html.escape(str(channel))}</strong>
  · File : <strong>{html.escape(OPS_LABELS.get(persona.ops_status or 'none', persona.ops_status or '—'))}</strong></span>
</div>
""",
    unsafe_allow_html=True,
)

if "before_after" in st.session_state and st.session_state["before_after"].get("after"):
    ba = st.session_state["before_after"]
    section("Avant / après orchestrateur")
    b, a = ba["before"], ba["after"]
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Champ": "Score",
                    "Avant": b.get("score"),
                    "Après": a.get("score"),
                },
                {"Champ": "Offre", "Avant": b.get("action"), "Après": a.get("action")},
                {"Champ": "Canal", "Avant": b.get("channel"), "Après": a.get("channel")},
                {"Champ": "File", "Avant": b.get("ops"), "Après": a.get("ops")},
                {
                    "Champ": "Message",
                    "Avant": "oui" if b.get("message") else "non",
                    "Après": "oui" if a.get("message") else "non",
                },
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )

c1, c2, c3 = st.columns(3, gap="medium")
with c1:
    st.markdown(
        f"""
<div class="panel">
  <div class="panel-title">Contrat & facturation</div>
  {kv_html([
      ("Contrat", (persona.contract or {}).get("type")),
      ("Ancienneté", (persona.contract or {}).get("tenure")),
      ("Paiement", (persona.contract or {}).get("payment_method")),
      ("Paperless", (persona.contract or {}).get("paperless_billing")),
      ("Mensuel", (persona.billing or {}).get("monthly_charges")),
      ("Total", (persona.billing or {}).get("total_charges")),
  ])}
</div>
""",
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        f"""
<div class="panel">
  <div class="panel-title">Sentiment</div>
  {kv_html([
      ("Polarité", persona.sentiment),
      ("Confiance", persona.sentiment_confidence),
      ("Émotions", persona.emotions),
      ("Sujets", persona.complaint_topics),
      ("Avis", (persona.raw_review_text or "")[:160]),
  ])}
</div>
""",
        unsafe_allow_html=True,
    )
with c3:
    st.markdown(
        f"""
<div class="panel">
  <div class="panel-title">Décision</div>
  {kv_html([
      ("Action", action.get("action")),
      ("Canal", channel),
      ("Δ risque", action.get("delta")),
      ("Coût relatif", action.get("cost")),
      ("Score après", action.get("score_after")),
      ("Msg", MESSAGE_LABELS.get(persona.message_status or "none")),
  ])}
</div>
""",
        unsafe_allow_html=True,
    )

section("File opérationnelle")
o1, o2, o3 = st.columns(3)
with o1:
    ops_status = st.selectbox(
        "Statut file",
        list(OPS_STATUSES),
        index=list(OPS_STATUSES).index(persona.ops_status)
        if persona.ops_status in OPS_STATUSES
        else 0,
        format_func=lambda x: OPS_LABELS.get(x, x),
        disabled=not can_write(),
    )
with o2:
    msg_status = st.selectbox(
        "Statut message",
        list(MESSAGE_STATUSES),
        index=list(MESSAGE_STATUSES).index(persona.message_status)
        if persona.message_status in MESSAGE_STATUSES
        else 0,
        format_func=lambda x: MESSAGE_LABELS.get(x, x),
        disabled=not can_write(),
    )
with o3:
    st.markdown("**Enregistrement**")
    if st.button("Enregistrer statuts", use_container_width=True, disabled=not can_write()):
        try:
            update_ops(customer_id, ops_status=ops_status, message_status=msg_status)
            st.success("Statuts enregistrés (SQLite + Supabase si configuré)")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))

notes = st.text_area("Note agent", value=persona.agent_notes or "", height=80)
if st.button("Sauver la note", disabled=not can_write()):
    try:
        update_ops(customer_id, agent_notes=notes)
        st.success("Note enregistrée")
    except Exception as exc:
        st.error(str(exc))

if persona.decision_justification:
    section("Justification")
    st.write(persona.decision_justification)

if persona.risk_factors:
    section("Facteurs SHAP (local)")
    shap_df = pd.DataFrame(persona.risk_factors).rename(
        columns={
            "feature": "Variable",
            "shap_value": "SHAP",
            "direction": "Effet",
        }
    )
    st.dataframe(shap_df, use_container_width=True, hide_index=True)
    st.bar_chart(shap_df.set_index("Variable")["SHAP"])

scenarios = persona.simulation_scenarios or []
if scenarios:
    section("Scénarios simulés (coût / Δ / ROI relatif)")
    scen_df = pd.DataFrame(scenarios).copy()
    if "delta_per_cost" not in scen_df.columns and "delta" in scen_df.columns:
        scen_df["delta_per_cost"] = scen_df.apply(
            lambda r: (r["delta"] / r["cost"]) if r.get("cost") else None,
            axis=1,
        )
    scen_df = scen_df.rename(
        columns={
            "action": "Action",
            "applied": "Applicable",
            "score_before": "Avant",
            "score_after": "Après",
            "delta": "Δ",
            "cost": "Coût",
            "delta_per_cost": "ROI relatif (Δ/coût)",
        }
    )
    st.dataframe(scen_df, use_container_width=True, hide_index=True)

section("Message de rétention")
if persona.retention_message:
    st.caption(f"Canal généré : **{channel}** — statut {MESSAGE_LABELS.get(persona.message_status or 'none')}")
    edited = st.text_area(
        "Éditer le message",
        value=persona.retention_message,
        height=180,
        disabled=not can_write(),
    )
    b1, b2, b3, b4 = st.columns(4)
    with b1:
        if st.button("Sauver texte", disabled=not can_write()):
            update_ops(customer_id, retention_message=edited)
            st.success("Message mis à jour")
    with b2:
        if st.button("Valider", disabled=not can_write()):
            update_ops(customer_id, retention_message=edited, message_status="validated")
            st.success("Validé")
            st.rerun()
    with b3:
        if st.button("Rejeter", disabled=not can_write()):
            update_ops(customer_id, message_status="rejected")
            st.warning("Rejeté")
            st.rerun()
    with b4:
        if st.button("Marquer envoyé", disabled=not can_write()):
            update_ops(
                customer_id,
                retention_message=edited,
                message_status="sent",
                ops_status="contacted",
            )
            st.success("Marqué envoyé + contacté")
            st.rerun()
else:
    st.info("Pas encore de message. Lance l’orchestrateur pour ce client.")

# Optional: override recommended action
with st.expander("Modifier / valider l’offre recommandée"):
    new_action = st.text_input("Action", value=str(action.get("action") or ""))
    if st.button("Mettre à jour l’offre", disabled=not can_write()):
        updated = copy.deepcopy(action) if action else {}
        updated["action"] = new_action
        update_ops(customer_id, recommended_action=updated)
        st.success("Offre mise à jour")
        st.rerun()

if persona.rag_context:
    with st.expander("Contexte RAG (extraits tickets)"):
        for i, snippet in enumerate(persona.rag_context, 1):
            st.markdown(f"**Extrait {i}**")
            st.code(snippet, language=None)

section("Historique des runs")
runs = load_runs(customer_id, limit=20)
if runs.empty:
    st.caption("Aucun run enregistré pour ce client.")
else:
    show = runs.copy()
    show["action_name"] = show["action"].apply(
        lambda a: a.get("action") if isinstance(a, dict) else None
    )
    st.dataframe(
        show[
            [
                "created_at",
                "status",
                "action_name",
                "score_before",
                "score_after",
                "operator",
            ]
        ].rename(
            columns={
                "created_at": "Quand",
                "status": "Statut",
                "action_name": "Offre",
                "score_before": "Avant",
                "score_after": "Après",
                "operator": "Opérateur",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )
