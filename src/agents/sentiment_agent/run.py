"""Run the Sentiment Agent on stored Personas and persist the results."""

from __future__ import annotations

import logging

from sqlalchemy.engine import Engine

from src.agents.data_agent.repository import get_persona, list_persona_ids, save_persona
from src.agents.sentiment_agent.persona_updater import update_persona
from src.agents.sentiment_agent.sentiment_model import analyze
from src.persona.schema import Persona

logger = logging.getLogger(__name__)


def enrich_stored_persona(customer_id: str, engine: Engine | None = None) -> Persona:
    """
    Load one Persona from the warehouse, enrich it, save it back.

    Other agents should then call get_persona(customer_id).
    """
    persona = get_persona(customer_id, engine=engine)
    persona = update_persona(persona, analyze(persona))
    save_persona(persona, engine=engine)
    return persona


def enrich_all_personas(
    engine: Engine | None = None,
    *,
    skip_enriched: bool = True,
    limit: int | None = None,
) -> dict:
    """
    Enrich every stored Persona (sentiment, emotions, topics, satisfaction).

    skip_enriched: leave Personas that already have sentiment.
    limit: optional cap for tests or dry runs.
    Empty reviews are skipped, not treated as a hard failure of the batch.
    """
    ids = list_persona_ids(engine=engine)
    if limit is not None:
        ids = ids[: int(limit)]

    n_ok = 0
    n_skipped = 0
    n_failed = 0
    failures: list[dict] = []

    for customer_id in ids:
        persona = get_persona(customer_id, engine=engine)
        if skip_enriched and persona.is_enriched():
            n_skipped += 1
            continue
        try:
            enrich_stored_persona(customer_id, engine=engine)
            n_ok += 1
        except ValueError as exc:
            n_skipped += 1
            logger.warning("Skipping %s: %s", customer_id, exc)
        except Exception as exc:
            n_failed += 1
            failures.append({"customer_id": customer_id, "error": str(exc)})
            logger.exception("Failed to enrich %s", customer_id)

    summary = {
        "n_total": len(ids),
        "n_ok": n_ok,
        "n_skipped": n_skipped,
        "n_failed": n_failed,
        "failures": failures,
    }
    logger.info("Sentiment batch enrichment: %s", summary)
    return summary
