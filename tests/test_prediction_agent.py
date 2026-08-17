from pathlib import Path

import joblib
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.agents.data_agent.persona_builder import build_initial_persona
from src.agents.prediction_agent.features import FEATURE_COLUMNS, build_features
from src.agents.prediction_agent.predict import apply_prediction, predict_churn
from src.agents.prediction_agent.train import load_xy, split_train_test, train_models
from src.agents.sentiment_agent.persona_updater import update_persona as apply_sentiment


def _telco(**overrides):
    row = {
        "customerID": "7590-VHVEG",
        "gender": "Female",
        "SeniorCitizen": 0,
        "Partner": "Yes",
        "Dependents": "No",
        "tenure": 1,
        "PhoneService": "No",
        "MultipleLines": "No phone service",
        "InternetService": "DSL",
        "OnlineSecurity": "No",
        "OnlineBackup": "Yes",
        "DeviceProtection": "No",
        "TechSupport": "No",
        "StreamingTV": "No",
        "StreamingMovies": "No",
        "Contract": "Month-to-month",
        "PaperlessBilling": "Yes",
        "PaymentMethod": "Electronic check",
        "MonthlyCharges": 29.85,
        "TotalCharges": 29.85,
        "Churn": "No",
    }
    row.update(overrides)
    return pd.Series(row)


def _enriched_persona(**telco_overrides):
    persona = build_initial_persona(_telco(**telco_overrides), [], "billing issue")
    return apply_sentiment(
        persona,
        {
            "sentiment": "neutral",
            "confidence": 0.74,
            "emotions": ["calm"],
            "complaint_topics": ["Payment Problem"],
            "satisfaction_score": 3.0,
        },
    )


def test_load_split_and_train_three_models(tmp_path: Path):
    csv_path = tmp_path / "telco_train_ready.csv"
    n = 40
    rows = []
    for i in range(n):
        churn = int(i % 4 == 0)
        rows.append(
            {
                "tenure": i,
                "MonthlyCharges": 20 + i,
                "sentiment_negative": churn,
                "Churn": churn,
            }
        )
    pd.DataFrame(rows).to_csv(csv_path, index=False)

    X, y = load_xy(csv_path)
    assert "Churn" not in X.columns
    X_train, X_test, y_train, y_test = split_train_test(X, y, test_size=0.25)
    assert len(X_train) + len(X_test) == n

    models, comparison = train_models(
        X_train, y_train, X_test, y_test, models_dir=tmp_path / "models"
    )
    assert set(models) == {"logreg", "random_forest", "xgboost"}
    assert set(comparison["model"]) == set(models)
    assert (tmp_path / "models" / "selected_churn.joblib").exists()


def test_build_features_matches_first_telco_customer():
    persona = _enriched_persona()
    frame = build_features(persona)
    row = frame.iloc[0]
    assert list(frame.columns) == FEATURE_COLUMNS
    assert "Churn" not in FEATURE_COLUMNS
    assert row["gender"] == 0
    assert row["Partner"] == 1
    assert row["PhoneService"] == 0
    assert row["MultipleLines_No phone service"] == 1
    assert row["InternetService_Fiber optic"] == 0
    assert row["OnlineBackup_Yes"] == 1
    assert row["n_services"] == 1
    assert row["PaymentMethod_Electronic check"] == 1
    assert row["Contract_One year"] == 0
    assert row["tenure_bucket_1-2y"] == 0
    assert row["sentiment_neutral"] == 1
    assert row["topic_payment_problem"] == 1


def test_build_features_requires_sentiment():
    persona = build_initial_persona(_telco(), [], "text")
    with pytest.raises(ValueError, match="sentiment-enriched"):
        build_features(persona)


def test_predict_churn_writes_predicted_lineage(tmp_path: Path):
    X = pd.DataFrame(0, index=range(40), columns=FEATURE_COLUMNS)
    X["tenure"] = list(range(40))
    X["MonthlyCharges"] = [20 + i for i in range(40)]
    y = pd.Series([int(i % 3 == 0) for i in range(40)])
    model = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=500, class_weight="balanced")),
        ]
    )
    model.fit(X, y)
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    joblib.dump(model, models_dir / "selected_churn.joblib")
    joblib.dump(FEATURE_COLUMNS, models_dir / "feature_columns.joblib")
    joblib.dump(X.head(20), models_dir / "shap_background.joblib")

    persona = _enriched_persona()
    score = predict_churn(persona, models_dir=models_dir)
    assert 0.0 <= score <= 1.0
    assert persona.churn_risk_score == score
    assert persona.lineage["churn_risk_score"] == "PREDICTED"
    assert persona.lineage["risk_factors"] == "PREDICTED"
    assert persona.risk_factors
    assert "feature" in persona.risk_factors[0]
    payload = persona.to_dict()
    assert "Churn" not in payload


def test_score_stored_persona_persists_predicted_fields(tmp_path: Path):
    from sqlalchemy import create_engine

    from src.agents.data_agent.repository import get_persona, replace_personas
    from src.agents.data_agent.warehouse import init_db
    from src.agents.prediction_agent.run import score_stored_persona

    X = pd.DataFrame(0, index=range(20), columns=FEATURE_COLUMNS)
    y = pd.Series([0, 1] * 10)
    model = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=200)),
        ]
    )
    model.fit(X, y)
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    joblib.dump(model, models_dir / "selected_churn.joblib")
    joblib.dump(FEATURE_COLUMNS, models_dir / "feature_columns.joblib")
    joblib.dump(X, models_dir / "shap_background.joblib")

    engine = create_engine("sqlite:///:memory:", future=True)
    init_db(engine)
    replace_personas([_enriched_persona()], engine=engine)

    scored = score_stored_persona("7590-VHVEG", engine=engine, models_dir=models_dir)
    reloaded = get_persona("7590-VHVEG", engine=engine)
    assert scored.churn_risk_score is not None
    assert reloaded.churn_risk_score == scored.churn_risk_score
    assert reloaded.lineage["churn_risk_score"] == "PREDICTED"
    assert "Churn" not in reloaded.to_dict()


def test_apply_prediction_without_explain():
    X = pd.DataFrame(0, index=range(20), columns=FEATURE_COLUMNS)
    y = pd.Series([0, 1] * 10)
    model = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=200)),
        ]
    )
    model.fit(X, y)
    persona = apply_prediction(_enriched_persona(), model=model, explain=False)
    assert persona.risk_factors == []
    assert persona.churn_risk_score is not None
