"""Logique de décision : sélection du meilleur scénario (Agent Décision)."""
from config.settings import CHURN_RISK_THRESHOLD


def select_best_action(risk_score: float, scenarios: list[dict]) -> dict | None:
    """Sélectionne l'action au meilleur rapport gain/coût, ou None si le risque est sous le seuil.

    TODO : filtrer scenarios par gain sur le score, choisir le meilleur rapport gain/coût.
    """
    if risk_score < CHURN_RISK_THRESHOLD:
        return None
    raise NotImplementedError
