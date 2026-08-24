"""Write Decision Agent results onto the shared Persona."""

from __future__ import annotations

from src.persona.schema import Persona

_DECISION_LINEAGE = {
    "recommended_action": "DERIVED",
    "decision_justification": "DERIVED",
    "contact_channel": "DERIVED",
}


def update_persona(
    persona: Persona,
    *,
    recommended_action: dict | None,
    justification: str,
) -> Persona:
    """Attach the chosen scenario. Does not mutate contract/services or Churn."""
    persona.recommended_action = None if recommended_action is None else dict(recommended_action)
    persona.decision_justification = justification
    persona.contact_channel = (
        None if recommended_action is None else recommended_action.get("channel")
    )
    lineage = dict(persona.lineage or {})
    lineage.update(_DECISION_LINEAGE)
    persona.lineage = lineage
    return persona
