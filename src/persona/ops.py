"""Retention ops helpers: status labels, timestamps, pipeline history."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.persona.schema import Persona

OPS_STATUSES = ("none", "to_call", "to_email", "contacted", "postponed")
MESSAGE_STATUSES = ("none", "draft", "validated", "rejected", "sent")

OPS_LABELS = {
    "none": "—",
    "to_call": "À appeler",
    "to_email": "À emailer",
    "contacted": "Contacté",
    "postponed": "Reporté",
}

MESSAGE_LABELS = {
    "none": "—",
    "draft": "Brouillon",
    "validated": "Validé",
    "rejected": "Rejeté",
    "sent": "Envoyé",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def apply_decision_ops(persona: Persona) -> Persona:
    """Set queue status / message draft after decision+generate."""
    channel = (persona.contact_channel or (persona.recommended_action or {}).get("channel") or "").lower()
    if persona.retention_message:
        persona.message_status = persona.message_status if persona.message_status not in {
            "none",
            "",
        } else "draft"
    if channel == "call":
        persona.ops_status = "to_call"
    elif channel == "email":
        persona.ops_status = "to_email"
    persona.updated_at = utc_now_iso()
    return persona


def apply_low_risk_ops(persona: Persona) -> Persona:
    persona.ops_status = "none"
    if not persona.retention_message:
        persona.message_status = "none"
    persona.updated_at = utc_now_iso()
    return persona


def snapshot_for_run(
    persona: Persona,
    *,
    status: str | None,
    score_before: float | None = None,
    operator: str | None = None,
) -> dict[str, Any]:
    action = persona.recommended_action
    score_after = (
        float(action["score_after"])
        if isinstance(action, dict) and action.get("score_after") is not None
        else persona.churn_risk_score
    )
    return {
        "customer_id": persona.customer_id,
        "status": status,
        "action": action,
        "message": persona.retention_message,
        "justification": persona.decision_justification,
        "score_before": score_before if score_before is not None else persona.churn_risk_score,
        "score_after": score_after,
        "operator": operator,
        "created_at": utc_now_iso(),
    }
