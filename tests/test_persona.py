import pandas as pd
import pytest

from src.agents.data_agent.persona_builder import build_initial_persona
from src.persona.schema import Persona


def _telco(**overrides):
    row = {
        "customerID": "7590-VHVEG",
        "gender": "Female",
        "SeniorCitizen": 0,
        "Partner": "Yes",
        "Dependents": "No",
        "tenure": 12,
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
        "Churn": "Yes",
    }
    row.update(overrides)
    return pd.Series(row)


def test_persona_excludes_churn_and_keeps_lineage():
    history = pd.DataFrame([{
        "event_index": 0,
        "months_before_snapshot": 1,
        "amount": 29.85,
        "event_type": "synthetic_engagement",
        "lineage": "SYNTHETIC",
        "profile": "rfm_distribution",
    }])
    persona = build_initial_persona(_telco(), history, "billing issue", review_tone="negative")

    assert persona.customer_id == "7590-VHVEG"
    assert persona.services["internet_service"] == "DSL"
    assert persona.billing["total_charges"] == 29.85
    assert persona.review_tone == "negative"
    assert isinstance(persona.behavioral_history, list)
    assert persona.lineage["behavioral_history"] == "SYNTHETIC"
    assert persona.lineage["demographics"] == "REAL"
    payload = persona.to_dict()
    assert "Churn" not in payload
    assert "churn" not in payload
    assert "Yes" not in str(payload.get("lineage"))


def test_persona_round_trip_json_and_from_dict():
    persona = build_initial_persona(_telco(Churn="No"), [], "text", review_tone="neutral")
    restored = Persona.from_dict(persona.to_dict())
    assert restored.customer_id == persona.customer_id
    assert restored.raw_review_text == "text"
    assert "Churn" not in restored.to_dict()


def test_build_initial_persona_requires_customer_id():
    with pytest.raises(ValueError, match="customerID"):
        build_initial_persona(pd.Series({"gender": "Male"}), [], "x")
