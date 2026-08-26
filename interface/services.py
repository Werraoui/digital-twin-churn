"""Data helpers for the Streamlit UI (warehouse Personas)."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from config.settings import CALL_RISK_THRESHOLD, CHURN_RISK_THRESHOLD
from src.agents.data_agent.repository import get_persona, list_personas, save_persona
from src.agents.simulation_agent.rules_engine import ACTION_COSTS, ACTIONS
from src.agents.simulation_agent.run import simulate_persona
from src.persona.schema import Persona


@st.cache_data(ttl=120, show_spinner=False)
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
                "enriched": persona.is_enriched(),
                "scored": persona.is_scored(),
            }
        )
    if not rows:
        return pd.DataFrame(
            columns=[
                "customer_id",
                "churn_risk_score",
                "sentiment",
                "contract",
                "tenure",
                "monthly_charges",
                "recommended_action",
                "channel",
                "has_message",
                "enriched",
                "scored",
            ]
        )
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


def run_orchestrator(customer_id: str, *, persist: bool = True) -> dict:
    from src.orchestrator.graph import run_for_customer

    result = run_for_customer(customer_id, persist=persist)
    clear_persona_cache()
    return result


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


AVAILABLE_ACTIONS = list(ACTIONS)
