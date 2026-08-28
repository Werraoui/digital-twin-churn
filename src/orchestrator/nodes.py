"""LangGraph node functions — thin wrappers around specialized agents."""

from __future__ import annotations

import logging

from src.agents.data_agent.persona_builder import build_initial_persona
from src.agents.data_agent.repository import get_persona, save_persona
from src.agents.decision_agent.justify import build_justification
from src.agents.decision_agent.run import decide_for_persona
from src.agents.generator_agent.run import generate_for_persona
from src.agents.prediction_agent.predict import apply_prediction
from src.agents.sentiment_agent.persona_updater import update_persona as apply_sentiment
from src.agents.sentiment_agent.sentiment_model import analyze
from src.agents.simulation_agent.run import simulate_persona
from src.orchestrator.state import TwinState

logger = logging.getLogger(__name__)


def load_persona_node(state: TwinState) -> TwinState:
    """Load from warehouse by customer_id, or build from raw Telco inputs."""
    if state.get("persona") is not None:
        persona = state["persona"]
        return {
            "persona": persona,
            "customer_id": persona.customer_id,
            "status": "persona_ready",
        }

    customer_id = state.get("customer_id")
    if customer_id:
        persona = get_persona(customer_id)
        return {
            "persona": persona,
            "customer_id": persona.customer_id,
            "status": "persona_loaded",
        }

    telco = state.get("telco_client")
    if telco is None:
        raise ValueError("Provide customer_id, persona, or telco_client")

    persona = build_initial_persona(
        telco,
        state.get("behavioral_history") or [],
        state.get("review_text"),
        review_tone=state.get("review_tone"),
    )
    return {
        "persona": persona,
        "customer_id": persona.customer_id,
        "status": "persona_built",
    }


def sentiment_node(state: TwinState) -> TwinState:
    persona = state["persona"]
    if persona.is_enriched():
        return {"persona": persona, "status": "sentiment_skipped"}
    if not (persona.raw_review_text or "").strip():
        return {
            "persona": persona,
            "status": "sentiment_skipped_empty_review",
            "message": "Aucune action nécessaire (avis client vide).",
            "action": None,
        }
    persona = apply_sentiment(persona, analyze(persona))
    return {"persona": persona, "status": "sentiment_done"}


def predict_node(state: TwinState) -> TwinState:
    persona = state["persona"]
    if not persona.is_enriched():
        raise ValueError("Persona must be sentiment-enriched before prediction")
    persona = apply_prediction(persona)
    return {
        "persona": persona,
        "status": "predicted",
        "action": None,
        "message": None,
        "justification": None,
        "scenarios": [],
    }


def low_risk_node(state: TwinState) -> TwinState:
    persona = state["persona"]
    risk = persona.churn_risk_score
    if risk is None:
        return {
            "persona": persona,
            "scenarios": [],
            "action": None,
            "message": state.get("message") or "Aucune action nécessaire.",
            "justification": state.get("justification")
            or "Persona non enrichi / non scoré : aucune action recommandée.",
            "status": "skipped",
        }
    risk_f = float(risk)
    return {
        "persona": persona,
        "scenarios": [],
        "action": None,
        "message": "Aucune action nécessaire.",
        "justification": (
            f"Score de risque de {risk_f:.2f} sous le seuil d'intervention : "
            "aucune action recommandée."
        ),
        "status": "low_risk",
    }


def simulate_node(state: TwinState) -> TwinState:
    persona, scenarios = simulate_persona(state["persona"])
    return {
        "persona": persona,
        "scenarios": scenarios,
        "status": "simulated",
    }


def decide_node(state: TwinState) -> TwinState:
    persona, chosen = decide_for_persona(state["persona"])
    justification = persona.decision_justification
    if chosen is None and justification is None:
        risk = float(persona.churn_risk_score or 0.0)
        justification = build_justification(risk, persona.risk_factors, None)
    return {
        "persona": persona,
        "action": chosen,
        "justification": justification,
        "message": None if chosen else "Aucun scénario applicable.",
        "status": "decided" if chosen else "no_action",
    }


def generate_node(state: TwinState) -> TwinState:
    persona, message = generate_for_persona(state["persona"], use_llm=True)
    return {
        "persona": persona,
        "message": message,
        "justification": persona.decision_justification or state.get("justification"),
        "action": persona.recommended_action or state.get("action"),
        "status": "generated",
    }


def persist_node(state: TwinState) -> TwinState:
    if state.get("persist", True) and state.get("persona") is not None:
        from config.settings import UI_OPERATOR
        from src.agents.data_agent.repository import record_pipeline_run
        from src.persona.ops import (
            apply_decision_ops,
            apply_low_risk_ops,
            snapshot_for_run,
            utc_now_iso,
        )

        persona = state["persona"]
        status = state.get("status", "done")
        score_before = (
            float(persona.churn_risk_score)
            if persona.churn_risk_score is not None
            else None
        )

        if status in {"generated", "decided"} or (
            persona.retention_message and status not in {"low_risk", "skipped"}
        ):
            persona = apply_decision_ops(persona)
        elif status in {"low_risk", "skipped", "no_action"}:
            persona = apply_low_risk_ops(persona)
        else:
            persona.updated_at = utc_now_iso()

        save_persona(persona)
        record_pipeline_run(
            snapshot_for_run(
                persona,
                status=status,
                score_before=score_before,
                operator=UI_OPERATOR,
            )
        )
        logger.info("Persisted Persona %s", persona.customer_id)
        return {
            "persona": persona,
            "status": status,
            "persist": state.get("persist", True),
        }
    return {"status": state.get("status", "done"), "persist": state.get("persist", True)}
