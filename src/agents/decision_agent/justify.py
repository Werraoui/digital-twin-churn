"""Construction de la justification textuelle de la recommandation (Agent Décision)."""

from __future__ import annotations


def _format_risk_factors(risk_factors: list | None, *, top_k: int = 3) -> str:
    if not risk_factors:
        return "facteurs non détaillés"

    labels = []
    for item in risk_factors[: int(top_k)]:
        if isinstance(item, dict):
            name = item.get("feature", "feature")
            direction = item.get("direction", "")
            if direction == "increases_risk":
                labels.append(f"{name} (↑ risque)")
            elif direction == "decreases_risk":
                labels.append(f"{name} (↓ risque)")
            else:
                labels.append(str(name))
        else:
            labels.append(str(item))
    return ", ".join(labels) if labels else "facteurs non détaillés"


def build_justification(
    risk_score: float,
    risk_factors: list | None,
    chosen_scenario: dict | None,
) -> str:
    """Explication traçable : score, SHAP, action, gain estimé, canal."""
    if chosen_scenario is None:
        return (
            f"Score de risque de {float(risk_score):.2f} sous le seuil d'intervention "
            "ou aucun scénario applicable : aucune action recommandée."
        )

    action = chosen_scenario.get("action", "action inconnue")
    score_after = chosen_scenario.get("score_after")
    delta = chosen_scenario.get("delta")
    cost = chosen_scenario.get("cost")
    channel = chosen_scenario.get("channel", "email")
    factors = _format_risk_factors(risk_factors)

    parts = [
        f"Score de risque de {float(risk_score):.2f}, motivé principalement par : {factors}.",
        f"Action recommandée : {action}",
    ]
    if score_after is not None:
        parts[-1] += f" (score simulé après action : {float(score_after):.2f}"
        if delta is not None:
            parts[-1] += f", Δ = {float(delta):+.2f}"
        if cost is not None:
            parts[-1] += f", coût relatif = {float(cost):.1f}"
        parts[-1] += ")."
    else:
        parts[-1] += "."
    parts.append(f"Canal de contact : {channel}.")
    return " ".join(parts)
