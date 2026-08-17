"""Write Prediction Agent results onto the shared Persona."""

from __future__ import annotations

from src.persona.schema import Persona

_PREDICTION_LINEAGE = {
    "churn_risk_score": "PREDICTED",
    "risk_factors": "PREDICTED",
}


def update_persona(
    persona: Persona,
    *,
    churn_risk_score: float,
    risk_factors: list | None = None,
) -> Persona:
    """Attach the churn score. Does not copy the Churn label."""
    persona.churn_risk_score = float(churn_risk_score)
    persona.risk_factors = list(risk_factors or [])
    lineage = dict(persona.lineage or {})
    lineage.update(_PREDICTION_LINEAGE)
    persona.lineage = lineage
    return persona
