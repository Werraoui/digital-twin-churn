"""Entraînement du modèle de prédiction du churn (hors ligne)."""
import pandas as pd
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier
import joblib


def train_model(X: pd.DataFrame, y: pd.Series, output_path: str = "src/models/xgb_churn.joblib"):
    """Entraîne un modèle XGBoost et le sauvegarde. À exécuter hors ligne, pas à chaque appel."""
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
    model = XGBClassifier(eval_metric="logloss")
    model.fit(X_train, y_train)
    joblib.dump(model, output_path)
    return model, (X_test, y_test)
