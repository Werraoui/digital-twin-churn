"""Retention message generation (RAG + free LLM, with template fallback)."""

from __future__ import annotations

import logging

from src.agents.generator_agent.corpus import ACTION_LABELS
from src.agents.generator_agent.llm import generate_with_llm, resolve_provider
from src.agents.generator_agent.retriever import retrieve_context
from src.persona.schema import Persona

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Tu es une conseillère fidélisation empathique pour un opérateur telecom.
Ton ton est chaleureux mais professionnel.
Tu t'appuies UNIQUEMENT sur le contexte fourni (Persona + extraits de tickets).
N'invente pas de faits, de prix, ni d'engagements absents du contexte.
N'utilise jamais le label Churn Yes/No.
Réponds dans la langue du client si elle est claire, sinon en français.
"""


def _action_id(recommended_action: str | dict | None) -> str:
    if recommended_action is None:
        return ""
    if isinstance(recommended_action, dict):
        return str(recommended_action.get("action") or "")
    return str(recommended_action)


def _channel(persona: Persona, recommended_action: str | dict | None) -> str:
    if persona.contact_channel:
        return str(persona.contact_channel)
    if isinstance(recommended_action, dict) and recommended_action.get("channel"):
        return str(recommended_action["channel"])
    return "email"


def _action_label(action_id: str) -> str:
    return ACTION_LABELS.get(action_id, action_id or "a retention offer")


def _build_user_prompt(
    persona: Persona,
    *,
    action_id: str,
    channel: str,
    rag_snippets: list[str],
) -> str:
    topics = ", ".join(persona.complaint_topics or []) or "none"
    risk = persona.churn_risk_score
    risk_txt = f"{float(risk):.2f}" if risk is not None else "unknown"
    snippets = "\n\n".join(f"- {text}" for text in rag_snippets) or "- (no ticket context)"
    format_hint = (
        "Write a short outbound CALL SCRIPT (greeting, empathy, offer, closing question)."
        if channel == "call"
        else "Write a short retention EMAIL (subject line + body)."
    )
    return f"""Customer context (Persona — shared memory):
- customer_id: {persona.customer_id}
- contract: {persona.contract}
- services: {persona.services}
- billing: {persona.billing}
- sentiment: {persona.sentiment} (confidence={persona.sentiment_confidence})
- emotions: {persona.emotions}
- complaint_topics: {topics}
- customer review text: {persona.raw_review_text}
- churn_risk_score: {risk_txt}
- recommended retention action: {action_id} ({_action_label(action_id)})
- contact channel: {channel}

Retrieved support-ticket patterns (NOT the same customer — style/resolution cues only):
{snippets}

Task: {format_hint}
Keep it under 180 words. Mention the recommended action explicitly.
"""


def _template_message(
    persona: Persona,
    *,
    action_id: str,
    channel: str,
    rag_snippets: list[str],
) -> str:
    """Offline fallback when no LLM API key is configured."""
    label = _action_label(action_id)
    review = (persona.raw_review_text or "your recent feedback").strip()
    cue = rag_snippets[0].split("\n")[0] if rag_snippets else "Category: support"
    if channel == "call":
        return (
            f"CALL SCRIPT\n"
            f"Hello, this is the retention team regarding account {persona.customer_id}. "
            f"We reviewed your note about “{review[:120]}” and similar cases ({cue}). "
            f"To reduce friction, we’d like to {label}. "
            f"Would you be open to activating this today?"
        )
    return (
        f"Subject: A retention offer for your account\n\n"
        f"Hello,\n\n"
        f"Thank you for sharing your experience (“{review[:120]}”). "
        f"Based on similar support patterns ({cue}), we recommend that we {label}. "
        f"This offer is tailored to your current contract and preferences.\n\n"
        f"Reply to this email if you’d like us to proceed.\n\n"
        f"Kind regards,\nRetention Team"
    )


def generate_retention_message(
    persona: Persona,
    recommended_action: str | dict | None = None,
    *,
    top_k: int = 3,
    use_llm: bool | None = None,
    provider: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
    retrieve: bool = True,
    rag_snippets: list[str] | None = None,
) -> str:
    """
    Generate a retention email or call script for the chosen action.

    Default LLM order (free-first): Groq → Gemini → Anthropic → template.
    """
    if persona is None:
        raise ValueError("persona is required")

    action = recommended_action
    if action is None:
        action = persona.recommended_action
    action_id = _action_id(action)
    if not action_id:
        raise ValueError("recommended_action is required")

    channel = _channel(persona, action)
    query = " ".join(
        part
        for part in (
            persona.raw_review_text or "",
            " ".join(persona.complaint_topics or []),
            persona.sentiment or "",
            _action_label(action_id),
        )
        if part
    )
    snippets = list(rag_snippets) if rag_snippets is not None else []
    if retrieve and not snippets:
        snippets = retrieve_context(query, top_k=top_k)

    user_prompt = _build_user_prompt(
        persona, action_id=action_id, channel=channel, rag_snippets=snippets
    )

    chosen = resolve_provider(provider)
    should_use_llm = use_llm if use_llm is not None else chosen != "template"
    if should_use_llm and chosen != "template":
        try:
            return generate_with_llm(
                SYSTEM_PROMPT,
                user_prompt,
                provider=chosen,
                api_key=api_key,
                model=model,
            )
        except Exception as exc:
            logger.warning(
                "LLM provider %s failed (%s); using template fallback", chosen, exc
            )

    return _template_message(
        persona, action_id=action_id, channel=channel, rag_snippets=snippets
    )
