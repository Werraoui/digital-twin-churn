"""Local SHAP explanations for the selected logistic regression model."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import shap
from sklearn.pipeline import Pipeline

from config.settings import MODELS_DIR


def _linear_parts(model) -> tuple:
    if isinstance(model, Pipeline):
        return model.named_steps["scaler"], model.named_steps["clf"]
    return None, model


def explain_prediction(
    model,
    X_row: pd.DataFrame,
    *,
    background: pd.DataFrame | None = None,
    models_dir: str | Path | None = None,
    top_k: int = 5,
) -> list[dict]:
    """Top SHAP factors for one encoded row. Values are in log-odds."""
    scaler, clf = _linear_parts(model)
    if background is None:
        bg_path = Path(models_dir or MODELS_DIR) / "shap_background.joblib"
        if bg_path.exists():
            import joblib

            background = joblib.load(bg_path)
        else:
            background = X_row

    background = background.reindex(columns=X_row.columns)
    if scaler is not None:
        x_scaled = scaler.transform(X_row)
        bg_scaled = scaler.transform(background)
    else:
        x_scaled = X_row.to_numpy()
        bg_scaled = background.to_numpy()

    explainer = shap.LinearExplainer(clf, bg_scaled)
    shap_values = np.array(explainer.shap_values(x_scaled), dtype=float).reshape(-1)
    names = list(X_row.columns)
    ranked = sorted(
        zip(names, shap_values),
        key=lambda item: abs(item[1]),
        reverse=True,
    )
    factors = []
    for name, value in ranked[: int(top_k)]:
        factors.append(
            {
                "feature": name,
                "shap_value": float(value),
                "direction": "increases_risk" if value > 0 else "decreases_risk",
            }
        )
    return factors
