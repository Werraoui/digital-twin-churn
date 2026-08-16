"""Génération de messages de rétention personnalisés (Agent Générateur, RAG)."""
from src.persona.schema import Persona
from src.agents.generator_agent.retriever import retrieve_context

SYSTEM_PROMPT = """Tu es une conseillère fidélisation empathique. Ton ton est chaleureux mais
professionnel, et tu t'appuies uniquement sur le contexte réel du client, jamais sur des
suppositions."""


def generate_retention_message(persona: Persona, recommended_action: str) -> str:
    """Génère un message de rétention personnalisé, ancré dans le contexte réel du client.

    TODO : construire le prompt (SYSTEM_PROMPT + contexte RAG + persona + action), appeler le LLM.
    """
    context = retrieve_context(persona.raw_review_text or "")
    raise NotImplementedError
