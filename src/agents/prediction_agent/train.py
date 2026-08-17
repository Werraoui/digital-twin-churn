"""Entraînement hors ligne : logistic regression, Random Forest, XGBoost."""

from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from config.settings import MODELS_DIR, SELECTED_CHURN_MODEL, TELCO_ML_READY_PATH

TARGET = "Churn"


def load_xy(path: str | Path | None = None) -> tuple[pd.DataFrame, pd.Series]:
    source = Path(path or TELCO_ML_READY_PATH)
    df = pd.read_csv(source)
    if TARGET not in df.columns:
        raise ValueError(f"{source} must contain {TARGET}")
    leak = [c for c in ("customerID", "sentiment") if c in df.columns]
    X = df.drop(columns=[TARGET, *leak])
    y = df[TARGET].astype(int)
    return X, y


def split_train_test(
    X: pd.DataFrame,
    y: pd.Series,
    *,
    test_size: float = 0.2,
    random_state: int = 42,
):
    return train_test_split(X, y, test_size=test_size, stratify=y, random_state=random_state)


def _scale_pos_weight(y: pd.Series) -> float:
    n_neg = int((y == 0).sum())
    n_pos = int((y == 1).sum())
    if n_pos == 0:
        return 1.0
    return n_neg / n_pos


def build_models(y_train: pd.Series) -> dict:
    return {
        "logreg": Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "clf",
                    LogisticRegression(
                        max_iter=1000,
                        class_weight="balanced",
                        random_state=42,
                    ),
                ),
            ]
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=200,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        ),
        "xgboost": XGBClassifier(
            eval_metric="logloss",
            scale_pos_weight=_scale_pos_weight(y_train),
            random_state=42,
            n_jobs=-1,
        ),
    }


def evaluate(model, X_test: pd.DataFrame, y_test: pd.Series) -> dict[str, float]:
    proba = model.predict_proba(X_test)[:, 1]
    pred = (proba >= 0.5).astype(int)
    return {
        "roc_auc": float(roc_auc_score(y_test, proba)),
        "f1": float(f1_score(y_test, pred)),
        "recall_churn": float(((pred == 1) & (y_test == 1)).sum() / max(int((y_test == 1).sum()), 1)),
    }


def train_models(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    *,
    models_dir: str | Path | None = None,
) -> tuple[dict, pd.DataFrame]:
    out_dir = Path(models_dir or MODELS_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    fitted = {}
    rows = []
    for name, model in build_models(y_train).items():
        model.fit(X_train, y_train)
        fitted[name] = model
        metrics = evaluate(model, X_test, y_test)
        rows.append({"model": name, **metrics})
        joblib.dump(model, out_dir / f"{name}_churn.joblib")

    comparison = pd.DataFrame(rows).sort_values("roc_auc", ascending=False)
    joblib.dump(list(X_train.columns), out_dir / "feature_columns.joblib")
    joblib.dump(fitted[SELECTED_CHURN_MODEL], out_dir / "selected_churn.joblib")
    n_bg = min(100, len(X_train))
    joblib.dump(
        X_train.sample(n=n_bg, random_state=42),
        out_dir / "shap_background.joblib",
    )
    return fitted, comparison


def main() -> None:
    X, y = load_xy()
    X_train, X_test, y_train, y_test = split_train_test(X, y)
    print(f"train={X_train.shape} test={X_test.shape}")
    print(f"churn train={y_train.mean():.4f} test={y_test.mean():.4f}")
    _, comparison = train_models(X_train, y_train, X_test, y_test)
    print(comparison.to_string(index=False))
    print("selected model:", SELECTED_CHURN_MODEL)
    print("saved under", MODELS_DIR)


if __name__ == "__main__":
    main()
