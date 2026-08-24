"""Run the Decision Agent on simulated Personas and persist the choice."""

from __future__ import annotations

import logging

from sqlalchemy.engine import Engine

from src.agents.data_agent.repository import get_persona, list_persona_ids, save_persona
from src.agents.decision_agent.justify import build_justification
from src.agents.decision_agent.persona_updater import update_persona
from src.agents.decision_agent.rules import select_best_action
from src.persona.schema import Persona

logger = logging.getLogger(__name__)


def decide_for_persona(persona: Persona) -> tuple[Persona, dict | None]:
    """
    Pick the best simulated scenario and write DERIVED decision fields.

    Requires churn_risk_score. Uses simulation_scenarios when present.
    """
    if persona.churn_risk_score is None:
        raise ValueError("Persona must have churn_risk_score before decision")

    risk = float(persona.churn_risk_score)
    scenarios = list(persona.simulation_scenarios or [])
    chosen = select_best_action(risk, scenarios)
    justification = build_justification(risk, persona.risk_factors, chosen)
    persona = update_persona(
        persona,
        recommended_action=chosen,
        justification=justification,
    )
    return persona, chosen


def decide_stored_persona(
    customer_id: str,
    engine: Engine | None = None,
) -> tuple[Persona, dict | None]:
    persona = get_persona(customer_id, engine=engine)
    persona, chosen = decide_for_persona(persona)
    save_persona(persona, engine=engine)
    return persona, chosen


def decide_all_personas(
    engine: Engine | None = None,
    *,
    skip_decided: bool = True,
    limit: int | None = None,
) -> dict:
    ids = list_persona_ids(engine=engine)
    if limit is not None:
        ids = ids[: int(limit)]

    n_ok = 0
    n_skipped = 0
    n_failed = 0
    failures: list[dict] = []

    for customer_id in ids:
        persona = get_persona(customer_id, engine=engine)
        if skip_decided and "recommended_action" in (persona.lineage or {}):
            n_skipped += 1
            continue
        if persona.churn_risk_score is None:
            n_skipped += 1
            continue
        try:
            decide_stored_persona(customer_id, engine=engine)
            n_ok += 1
        except ValueError as exc:
            n_skipped += 1
            logger.warning("Skipping %s: %s", customer_id, exc)
        except Exception as exc:
            n_failed += 1
            failures.append({"customer_id": customer_id, "error": str(exc)})
            logger.exception("Failed to decide for %s", customer_id)

    summary = {
        "n_total": len(ids),
        "n_ok": n_ok,
        "n_skipped": n_skipped,
        "n_failed": n_failed,
        "failures": failures,
    }
    logger.info("Decision batch: %s", summary)
    return summary
