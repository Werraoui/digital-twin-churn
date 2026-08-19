"""Run the Simulation Agent on scored Personas and persist applicable scenarios."""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy.engine import Engine

from config.settings import CHURN_RISK_THRESHOLD
from src.agents.data_agent.repository import get_persona, list_persona_ids, save_persona
from src.agents.simulation_agent.client_twin import ClientTwin
from src.agents.simulation_agent.scenario_runner import run_scenarios
from src.persona.schema import Persona

logger = logging.getLogger(__name__)

_SIMULATION_LINEAGE = {"simulation_scenarios": "SYNTHETIC"}


def attach_scenarios(persona: Persona, scenarios: list[dict]) -> Persona:
    """Store what-if rows on the Persona. Does not change contract/services (real profile)."""
    persona.simulation_scenarios = list(scenarios)
    lineage = dict(persona.lineage or {})
    lineage.update(_SIMULATION_LINEAGE)
    persona.lineage = lineage
    return persona


def simulate_persona(
    persona: Persona,
    *,
    model=None,
    models_dir: str | Path | None = None,
    include_skipped: bool = False,
) -> tuple[Persona, list[dict]]:
    if persona.churn_risk_score is None:
        raise ValueError("Persona must have churn_risk_score before simulation")
    twin = ClientTwin(
        persona=persona,
        simulated_risk_score=float(persona.churn_risk_score),
    )
    scenarios = run_scenarios(
        twin,
        model=model,
        models_dir=models_dir,
        include_skipped=include_skipped,
    )
    persona = attach_scenarios(persona, scenarios)
    return persona, scenarios


def simulate_stored_persona(
    customer_id: str,
    engine: Engine | None = None,
    *,
    model=None,
    models_dir: str | Path | None = None,
    min_risk: float | None = None,
) -> tuple[Persona, list[dict]]:
    """Load a scored Persona, run applicable scenarios, save the list (not the cloned offers)."""
    threshold = CHURN_RISK_THRESHOLD if min_risk is None else min_risk
    persona = get_persona(customer_id, engine=engine)
    if persona.churn_risk_score is None:
        raise ValueError(f"{customer_id} has no churn_risk_score; run the Prediction Agent first")
    if float(persona.churn_risk_score) < threshold:
        persona = attach_scenarios(persona, [])
        save_persona(persona, engine=engine)
        return persona, []
    persona, scenarios = simulate_persona(
        persona, model=model, models_dir=models_dir, include_skipped=False
    )
    save_persona(persona, engine=engine)
    return persona, scenarios


def simulate_all_personas(
    engine: Engine | None = None,
    *,
    model=None,
    models_dir: str | Path | None = None,
    skip_simulated: bool = True,
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
        if skip_simulated and "simulation_scenarios" in (persona.lineage or {}):
            n_skipped += 1
            continue
        if persona.churn_risk_score is None:
            n_skipped += 1
            continue
        try:
            simulate_stored_persona(
                customer_id, engine=engine, model=model, models_dir=models_dir
            )
            n_ok += 1
        except ValueError as exc:
            n_skipped += 1
            logger.warning("Skipping %s: %s", customer_id, exc)
        except Exception as exc:
            n_failed += 1
            failures.append({"customer_id": customer_id, "error": str(exc)})
            logger.exception("Failed to simulate %s", customer_id)

    summary = {
        "n_total": len(ids),
        "n_ok": n_ok,
        "n_skipped": n_skipped,
        "n_failed": n_failed,
        "failures": failures,
    }
    logger.info("Simulation batch: %s", summary)
    return summary
