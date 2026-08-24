"""Write Generator Agent results onto the shared Persona."""

from __future__ import annotations

from src.persona.schema import Persona

_GENERATOR_LINEAGE = {
    "retention_message": "DERIVED",
    "rag_context": "REAL",
}


def update_persona(
    persona: Persona,
    *,
    retention_message: str,
    rag_context: list[str] | None = None,
) -> Persona:
    """Attach the generated message. Does not copy Churn."""
    persona.retention_message = retention_message
    persona.rag_context = list(rag_context or [])
    lineage = dict(persona.lineage or {})
    lineage.update(_GENERATOR_LINEAGE)
    persona.lineage = lineage
    return persona
