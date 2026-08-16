"""Explicabilité du score de risque via SHAP (Agent Prédiction)."""
import shap


def explain_prediction(model, X_row) -> list:
    """Retourne les facteurs explicatifs (valeurs SHAP) pour une prédiction donnée.

    TODO : shap.TreeExplainer(model), calculer les shap_values pour X_row, trier par importance.
    """
    raise NotImplementedError
