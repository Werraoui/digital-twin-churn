"""Run the Generator Agent on decided Personas and persist the message."""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy.engine import Engine

from src.agents.data_agent.repository import get_persona, list_persona_ids, save_persona
from src.agents.generator_agent.message_generator import generate_retention_message
from src.agents.generator_agent.persona_updater import update_persona
from src.agents.generator_agent.retriever import ensure_ticket_index, retrieve_context
from src.persona.schema import Persona

logger = logging.getLogger(__name__)


def generate_for_persona(
    persona: Persona,
    *,
    use_llm: bool | None = None,
    top_k: int = 3,
    persist_dir: str | Path | None = None,
) -> tuple[Persona, str]:
    """
    Build RAG context + retention message for a Persona that already has a decision.
    """
    action = persona.recommended_action
    if not action:
        raise ValueError("Persona must have recommended_action before generation")

    query = " ".join(
        part
        for part in (
            persona.raw_review_text or "",
            " ".join(persona.complaint_topics or []),
            str(action.get("action") if isinstance(action, dict) else action),
        )
        if part
    )
    snippets = retrieve_context(query, top_k=top_k, persist_dir=persist_dir)
    message = generate_retention_message(
        persona,
        action,
        top_k=top_k,
        use_llm=use_llm,
        retrieve=False,
        rag_snippets=snippets,
    )
    persona = update_persona(persona, retention_message=message, rag_context=snippets)
    return persona, message


def generate_stored_persona(
    customer_id: str,
    engine: Engine | None = None,
    *,
    use_llm: bool | None = None,
    persist_dir: str | Path | None = None,
) -> tuple[Persona, str]:
    persona = get_persona(customer_id, engine=engine)
    persona, message = generate_for_persona(
        persona, use_llm=use_llm, persist_dir=persist_dir
    )
    save_persona(persona, engine=engine)
    return persona, message


def generate_all_personas(
    engine: Engine | None = None,
    *,
    skip_generated: bool = True,
    use_llm: bool | None = None,
    limit: int | None = None,
    persist_dir: str | Path | None = None,
) -> dict:
    try:
        ensure_ticket_index(persist_dir=persist_dir)
    except Exception as exc:
        logger.warning("Could not warm Chroma index (%s); lexical fallback will be used", exc)

    ids = list_persona_ids(engine=engine)
    if limit is not None:
        ids = ids[: int(limit)]

    n_ok = 0
    n_skipped = 0
    n_failed = 0
    failures: list[dict] = []

    for customer_id in ids:
        persona = get_persona(customer_id, engine=engine)
        if skip_generated and "retention_message" in (persona.lineage or {}):
            n_skipped += 1
            continue
        if not persona.recommended_action:
            n_skipped += 1
            continue
        try:
            generate_stored_persona(
                customer_id,
                engine=engine,
                use_llm=use_llm,
                persist_dir=persist_dir,
            )
            n_ok += 1
        except ValueError as exc:
            n_skipped += 1
            logger.warning("Skipping %s: %s", customer_id, exc)
        except Exception as exc:
            n_failed += 1
            failures.append({"customer_id": customer_id, "error": str(exc)})
            logger.exception("Failed to generate message for %s", customer_id)

    summary = {
        "n_total": len(ids),
        "n_ok": n_ok,
        "n_skipped": n_skipped,
        "n_failed": n_failed,
        "failures": failures,
    }
    logger.info("Generator batch: %s", summary)
    return summary
