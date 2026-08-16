"""Inférence : calcule le score de risque de churn pour un client (Agent Prédiction)."""
import joblib
from src.persona.schema import Persona

_model = None


def _load_model(path: str = "src/models/xgb_churn.joblib"):
    global _model
    if _model is None:
        _model = joblib.load(path)
    return _model


def predict_churn(persona: Persona) -> float:
    """Calcule le score de risque de churn à partir du Persona actualisé.

    TODO : appeler build_features() sur le Persona, puis model.predict_proba().
    """
    raise NotImplementedError
