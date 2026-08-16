"""Construction de la justification textuelle de la recommandation (Agent Décision)."""


def build_justification(risk_score: float, risk_factors: list, chosen_scenario: dict) -> str:
    """Génère une explication traçable citant les données ayant motivé la décision."""
    factors = ", ".join(risk_factors) if risk_factors else "facteurs non détaillés"
    return (
        f"Score de risque de {risk_score:.2f}, motivé principalement par : {factors}. "
        f"Action recommandée : {chosen_scenario.get('action')} "
        f"(réduction estimée du risque à {chosen_scenario.get('score_after'):.2f})."
    )
