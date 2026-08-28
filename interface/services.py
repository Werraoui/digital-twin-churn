"""Data helpers for the Streamlit UI (warehouse Personas + ops)."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from config.settings import (
    CALL_RISK_THRESHOLD,
    CHURN_RISK_THRESHOLD,
    UI_CACHE_TTL_SECONDS,
    UI_OPERATOR,
    UI_ROLE,
)
from src.agents.data_agent.repository import (
    get_persona,
    list_personas,
    list_pipeline_runs,
    save_persona,
    sync_personas_from_supabase,
)
from src.agents.simulation_agent.rules_engine import ACTION_COSTS, ACTIONS
from src.agents.simulation_agent.run import simulate_persona
from src.integrations import supabase_store
from src.persona.ops import MESSAGE_STATUSES, OPS_STATUSES, utc_now_iso
from src.persona.schema import Persona


@st.cache_data(ttl=UI_CACHE_TTL_SECONDS, show_spinner=False)
def load_persona_table() -> pd.DataFrame:
    """Flatten Personas into a table for the risk dashboard."""
    rows: list[dict[str, Any]] = []
    for persona in list_personas():
        action = persona.recommended_action or {}
        rows.append(
            {
                "customer_id": persona.customer_id,
                "churn_risk_score": persona.churn_risk_score,
                "sentiment": persona.sentiment,
                "contract": (persona.contract or {}).get("type"),
                "tenure": (persona.contract or {}).get("tenure"),
                "monthly_charges": (persona.billing or {}).get("monthly_charges"),
                "recommended_action": action.get("action"),
                "channel": persona.contact_channel or action.get("channel"),
                "has_message": bool(persona.retention_message),
                "ops_status": persona.ops_status or "none",
                "message_status": persona.message_status or "none",
                "updated_at": persona.updated_at,
                "enriched": persona.is_enriched(),
                "scored": persona.is_scored(),
            }
        )
    columns = [
        "customer_id",
        "churn_risk_score",
        "sentiment",
        "contract",
        "tenure",
        "monthly_charges",
        "recommended_action",
        "channel",
        "has_message",
        "ops_status",
        "message_status",
        "updated_at",
        "enriched",
        "scored",
    ]
    if not rows:
        return pd.DataFrame(columns=columns)
    frame = pd.DataFrame(rows)
    return frame.sort_values(
        by=["scored", "churn_risk_score"],
        ascending=[False, False],
        na_position="last",
    ).reset_index(drop=True)


def clear_persona_cache() -> None:
    load_persona_table.clear()


def fetch_persona(customer_id: str) -> Persona:
    return get_persona(customer_id)


def risk_band(score: float | None) -> str:
    if score is None:
        return "non scoré"
    if score >= CALL_RISK_THRESHOLD:
        return "critique"
    if score >= CHURN_RISK_THRESHOLD:
        return "élevé"
    return "faible"


def can_write() -> bool:
    return UI_ROLE != "reader"


def supabase_status() -> dict[str, Any]:
    from config.settings import LOCAL_MIRROR, PERSONA_BACKEND, PERSONA_READ_FROM

    return {
        "configured": supabase_store.is_configured(),
        "backend": PERSONA_BACKEND,
        "read_from": PERSONA_READ_FROM,
        "local_mirror": LOCAL_MIRROR,
        "operator": UI_OPERATOR,
        "role": UI_ROLE,
        "cache_ttl": UI_CACHE_TTL_SECONDS,
    }


def pull_from_supabase() -> int:
    n = sync_personas_from_supabase()
    clear_persona_cache()
    return n


def run_orchestrator(customer_id: str, *, persist: bool = True) -> dict:
    import logging

    # Keep Streamlit terminal readable during RAG / HF / HTTP chatter.
    for noisy in ("httpx", "httpcore", "huggingface_hub", "sentence_transformers"):
        logging.getLogger(noisy).setLevel(logging.ERROR)

    from src.orchestrator.graph import run_for_customer

    result = run_for_customer(customer_id, persist=persist)
    clear_persona_cache()
    return result


def run_batch_orchestrator(customer_ids: list[str], *, persist: bool = True) -> list[dict]:
    results = []
    for cid in customer_ids:
        try:
            results.append({"customer_id": cid, **run_orchestrator(cid, persist=persist)})
        except Exception as exc:  # noqa: BLE001
            results.append({"customer_id": cid, "status": "error", "error": str(exc)})
    clear_persona_cache()
    return results


def run_what_if(customer_id: str, action: str) -> dict:
    """Apply one simulation action and return before/after scores."""
    from src.agents.simulation_agent.client_twin import ClientTwin
    from src.agents.simulation_agent.rules_engine import apply_action

    persona = get_persona(customer_id)
    if persona.churn_risk_score is None:
        raise ValueError("Ce client n'a pas encore de score. Lance l'orchestrateur d'abord.")
    twin = ClientTwin(persona=persona, simulated_risk_score=float(persona.churn_risk_score))
    simulated = apply_action(twin, action)
    return {
        "action": action,
        "applied": simulated.applied,
        "score_before": float(twin.simulated_risk_score),
        "score_after": float(simulated.simulated_risk_score),
        "delta": float(twin.simulated_risk_score) - float(simulated.simulated_risk_score),
        "cost": float(ACTION_COSTS.get(action, 0.0)),
    }


def refresh_scenarios(customer_id: str) -> list[dict]:
    persona = get_persona(customer_id)
    if persona.churn_risk_score is None:
        raise ValueError("Score manquant.")
    persona, scenarios = simulate_persona(persona)
    save_persona(persona)
    clear_persona_cache()
    return scenarios


def update_ops(
    customer_id: str,
    *,
    ops_status: str | None = None,
    message_status: str | None = None,
    agent_notes: str | None = None,
    retention_message: str | None = None,
    recommended_action: dict | None = None,
) -> Persona:
    if not can_write():
        raise PermissionError("Rôle reader : écriture interdite.")
    persona = get_persona(customer_id)
    if ops_status is not None:
        if ops_status not in OPS_STATUSES:
            raise ValueError(f"ops_status invalide: {ops_status}")
        persona.ops_status = ops_status
        if ops_status == "contacted":
            persona.contacted_at = utc_now_iso()
    if message_status is not None:
        if message_status not in MESSAGE_STATUSES:
            raise ValueError(f"message_status invalide: {message_status}")
        persona.message_status = message_status
    if agent_notes is not None:
        persona.agent_notes = agent_notes
    if retention_message is not None:
        persona.retention_message = retention_message
    if recommended_action is not None:
        persona.recommended_action = recommended_action
    persona.updated_at = utc_now_iso()
    save_persona(persona)
    clear_persona_cache()
    return persona


def load_runs(customer_id: str | None = None, limit: int = 100) -> pd.DataFrame:
    rows = list_pipeline_runs(customer_id, limit=limit)
    if not rows:
        return pd.DataFrame(
            columns=[
                "id",
                "customer_id",
                "status",
                "action",
                "score_before",
                "score_after",
                "operator",
                "created_at",
            ]
        )
    return pd.DataFrame(rows)


def global_shap_summary(top_n: int = 15) -> pd.DataFrame:
    """Aggregate absolute SHAP contributions across scored Personas."""
    tallies: dict[str, float] = {}
    counts: dict[str, int] = {}
    for persona in list_personas():
        for factor in persona.risk_factors or []:
            name = str(factor.get("feature") or "")
            if not name:
                continue
            val = abs(float(factor.get("shap_value") or 0.0))
            tallies[name] = tallies.get(name, 0.0) + val
            counts[name] = counts.get(name, 0) + 1
    if not tallies:
        return pd.DataFrame(columns=["Variable", "SHAP moyen |abs|", "Occurrences"])
    rows = [
        {
            "Variable": name,
            "SHAP moyen |abs|": tallies[name] / max(counts[name], 1),
            "Occurrences": counts[name],
        }
        for name in tallies
    ]
    frame = pd.DataFrame(rows).sort_values("SHAP moyen |abs|", ascending=False)
    return frame.head(top_n).reset_index(drop=True)


AVAILABLE_ACTIONS = list(ACTIONS)
