"""Write Sentiment Agent results onto the shared Persona."""

from __future__ import annotations

from src.persona.schema import Persona

_SENTIMENT_LINEAGE = {
    "sentiment": "DERIVED",
    "sentiment_confidence": "DERIVED",
    "emotions": "DERIVED",
    "complaint_topics": "DERIVED",
    "satisfaction_score": "DERIVED",
}


def update_persona(persona: Persona, analysis: dict) -> Persona:
    """
    Enrich the initial Persona with sentiment analysis.

    Does not copy Churn. Marks sentiment fields as DERIVED.
    """
    if "Churn" in analysis or "churn" in analysis:
        analysis = {
            key: value
            for key, value in analysis.items()
            if key not in {"Churn", "churn"}
        }

    persona.sentiment = analysis.get("sentiment")
    confidence = analysis.get("confidence", analysis.get("sentiment_confidence"))
    persona.sentiment_confidence = None if confidence is None else float(confidence)
    persona.emotions = list(analysis.get("emotions") or [])
    persona.complaint_topics = list(analysis.get("complaint_topics") or [])
    satisfaction = analysis.get("satisfaction_score")
    persona.satisfaction_score = None if satisfaction is None else float(satisfaction)

    lineage = dict(persona.lineage or {})
    lineage.update(_SENTIMENT_LINEAGE)
    persona.lineage = lineage
    return persona
