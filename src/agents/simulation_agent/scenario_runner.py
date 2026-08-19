"""Comparaison de plusieurs scénarios d'action pour un client (Agent Simulation)."""

from __future__ import annotations

from pathlib import Path

from src.agents.simulation_agent.client_twin import ClientTwin
from src.agents.simulation_agent.rules_engine import ACTION_COSTS, ACTIONS, apply_action


def run_scenarios(
    twin: ClientTwin,
    *,
    model=None,
    models_dir: str | Path | None = None,
    actions: tuple[str, ...] | list[str] | None = None,
    include_skipped: bool = False,
) -> list[dict]:
    """Teste les actions SHAP-alignées.

    include_skipped=False : uniquement les actions vraiment applicables (applied=True).
    """
    results = []
    for action in actions or ACTIONS:
        simulated = apply_action(twin, action, model=model, models_dir=models_dir)
        before = float(twin.simulated_risk_score)
        after = float(simulated.simulated_risk_score)
        cost = float(ACTION_COSTS[action])
        delta = before - after
        row = {
            "action": action,
            "applied": simulated.applied,
            "score_before": before,
            "score_after": after,
            "delta": delta,
            "cost": cost,
            "delta_per_cost": (delta / cost) if cost else 0.0,
        }
        if simulated.applied or include_skipped:
            results.append(row)
    return results
