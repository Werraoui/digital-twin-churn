"""Logique de routage de l'orchestrateur (à enrichir avec LangGraph au fil du projet)."""


def should_escalate_to_human(step: str, error: Exception | None) -> bool:
    """Détermine si un échec d'agent doit être escaladé à un humain plutôt que réessayé."""
    return error is not None
