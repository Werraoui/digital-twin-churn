"""Run the Prediction Agent on stored Personas and persist the score."""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy.engine import Engine

from src.agents.data_agent.repository import get_persona, list_persona_ids, save_persona
from src.agents.prediction_agent.predict import apply_prediction
from src.persona.schema import Persona

logger = logging.getLogger(__name__)


def score_stored_persona(
    customer_id: str,
    engine: Engine | None = None,
    *,
    models_dir: str | Path | None = None,
) -> Persona:
    """Load one Persona, score it with logreg, save it back."""
    persona = get_persona(customer_id, engine=engine)
    persona = apply_prediction(persona, models_dir=models_dir)
    save_persona(persona, engine=engine)
    return persona


def score_all_personas(
    engine: Engine | None = None,
    *,
    models_dir: str | Path | None = None,
    skip_scored: bool = True,
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
        if skip_scored and persona.churn_risk_score is not None:
            n_skipped += 1
            continue
        try:
            score_stored_persona(customer_id, engine=engine, models_dir=models_dir)
            n_ok += 1
        except ValueError as exc:
            n_skipped += 1
            logger.warning("Skipping %s: %s", customer_id, exc)
        except Exception as exc:
            n_failed += 1
            failures.append({"customer_id": customer_id, "error": str(exc)})
            logger.exception("Failed to score %s", customer_id)

    summary = {
        "n_total": len(ids),
        "n_ok": n_ok,
        "n_skipped": n_skipped,
        "n_failed": n_failed,
        "failures": failures,
    }
    logger.info("Prediction batch: %s", summary)
    return summary
