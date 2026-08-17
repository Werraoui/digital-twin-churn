"""Inférence : score de churn à partir du Persona (modèle logreg retenu)."""

from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd
from sklearn.pipeline import Pipeline

from config.settings import MODELS_DIR
from src.agents.prediction_agent.explain import explain_prediction
from src.agents.prediction_agent.features import FEATURE_COLUMNS, build_features
from src.agents.prediction_agent.persona_updater import update_persona
from src.persona.schema import Persona

_model = None
_feature_columns: list[str] | None = None


def _models_dir(models_dir: str | Path | None) -> Path:
    return Path(models_dir or MODELS_DIR)


def _load_model(models_dir: str | Path | None = None):
    global _model
    directory = _models_dir(models_dir)
    if _model is None or models_dir is not None:
        selected = directory / "selected_churn.joblib"
        fallback = directory / "logreg_churn.joblib"
        path = selected if selected.exists() else fallback
        if not path.exists():
            raise FileNotFoundError(
                f"No trained logreg model at {path}. Run:\n"
                "  python -m src.agents.prediction_agent.train"
            )
        loaded = joblib.load(path)
        if models_dir is None:
            _model = loaded
        return loaded
    return _model


def _load_feature_columns(models_dir: str | Path | None = None) -> list[str]:
    global _feature_columns
    path = _models_dir(models_dir) / "feature_columns.joblib"
    if path.exists():
        columns = list(joblib.load(path))
        if models_dir is None:
            _feature_columns = columns
        return columns
    return list(FEATURE_COLUMNS)


def _align_features(X: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    missing = [c for c in columns if c not in X.columns]
    if missing:
        raise ValueError(f"feature vector missing columns: {missing}")
    return X.loc[:, columns]


def apply_prediction(
    persona: Persona,
    *,
    model: Pipeline | None = None,
    models_dir: str | Path | None = None,
    explain: bool = True,
    top_k: int = 5,
) -> Persona:
    """Score one Persona and write PREDICTED lineage fields."""
    fitted = model if model is not None else _load_model(models_dir)
    columns = _load_feature_columns(models_dir)
    X = _align_features(build_features(persona), columns)
    score = float(fitted.predict_proba(X)[0, 1])
    factors = []
    if explain:
        factors = explain_prediction(
            fitted, X, models_dir=models_dir, top_k=top_k
        )
    return update_persona(persona, churn_risk_score=score, risk_factors=factors)


def predict_churn(
    persona: Persona,
    *,
    model: Pipeline | None = None,
    models_dir: str | Path | None = None,
) -> float:
    """Probability of churn in [0, 1]. Updates the Persona in place."""
    scored = apply_prediction(persona, model=model, models_dir=models_dir)
    return float(scored.churn_risk_score)
