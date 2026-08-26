"""Routing helpers for the LangGraph orchestrator."""

from __future__ import annotations

from config.settings import CHURN_RISK_THRESHOLD
from src.orchestrator.state import TwinState


def should_escalate_to_human(step: str, error: Exception | None) -> bool:
    """Escalate hard failures to a human rather than silently retrying forever."""
    return error is not None


def route_after_sentiment(state: TwinState) -> str:
    """Skip prediction when sentiment could not run (empty review)."""
    persona = state.get("persona")
    if persona is None:
        return "end_low_risk"
    if not persona.is_enriched():
        return "end_low_risk"
    return "predict"


def route_after_predict(state: TwinState) -> str:
    """Low risk → stop; high risk → simulate retention offers."""
    persona = state.get("persona")
    if persona is None or persona.churn_risk_score is None:
        return "end_low_risk"
    if float(persona.churn_risk_score) < CHURN_RISK_THRESHOLD:
        return "end_low_risk"
    return "simulate"


def route_after_decide(state: TwinState) -> str:
    """No applicable offer → stop; otherwise generate the retention message."""
    if state.get("action") is None:
        return "end_no_action"
    return "generate"
