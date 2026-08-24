"""Logique de décision : sélection du meilleur scénario (Agent Décision)."""

from __future__ import annotations

from config.settings import CALL_RISK_THRESHOLD, CHURN_RISK_THRESHOLD


def _delta_per_cost(scenario: dict) -> float:
    if "delta_per_cost" in scenario and scenario["delta_per_cost"] is not None:
        return float(scenario["delta_per_cost"])
    cost = float(scenario.get("cost") or 0.0)
    delta = float(scenario.get("delta") or 0.0)
    if cost <= 0:
        return delta
    return delta / cost


def _is_applicable(scenario: dict) -> bool:
    if scenario.get("applied") is False:
        return False
    return float(scenario.get("delta") or 0.0) > 0


def choose_contact_channel(risk_score: float) -> str:
    """Canal de contact : appel si risque élevé, sinon email."""
    if float(risk_score) >= CALL_RISK_THRESHOLD:
        return "call"
    return "email"


def select_best_action(
    risk_score: float,
    scenarios: list[dict],
    *,
    threshold: float | None = None,
) -> dict | None:
    """
    Choisit le scénario au meilleur rapport delta/coût.

    - sous le seuil de risque → None
    - ignore les scénarios non applicables ou à delta ≤ 0
    - en cas d'égalité sur delta_per_cost → plus grand delta, puis coût plus bas
    """
    min_risk = CHURN_RISK_THRESHOLD if threshold is None else threshold
    if float(risk_score) < min_risk:
        return None

    candidates = [row for row in scenarios if _is_applicable(row)]
    if not candidates:
        return None

    best = max(
        candidates,
        key=lambda row: (
            _delta_per_cost(row),
            float(row.get("delta") or 0.0),
            -float(row.get("cost") or 0.0),
        ),
    )
    chosen = dict(best)
    chosen["channel"] = choose_contact_channel(risk_score)
    return chosen
