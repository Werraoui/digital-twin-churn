"""Rebuild the training feature vector from a Persona (no Churn)."""

from __future__ import annotations

import pandas as pd

from src.agents.prediction_agent.training_table import (
    EMOTION_VALUES,
    SENTIMENT_VALUES,
    TOPIC_VALUES,
    _topic_column,
)
from src.persona.schema import Persona

FEATURE_COLUMNS = [
    "gender",
    "SeniorCitizen",
    "Partner",
    "Dependents",
    "tenure",
    "PhoneService",
    "PaperlessBilling",
    "MonthlyCharges",
    "TotalCharges",
    "MultipleLines_No phone service",
    "MultipleLines_Yes",
    "InternetService_Fiber optic",
    "InternetService_No",
    "OnlineSecurity_No internet service",
    "OnlineSecurity_Yes",
    "OnlineBackup_No internet service",
    "OnlineBackup_Yes",
    "DeviceProtection_No internet service",
    "DeviceProtection_Yes",
    "TechSupport_No internet service",
    "TechSupport_Yes",
    "StreamingTV_No internet service",
    "StreamingTV_Yes",
    "StreamingMovies_No internet service",
    "StreamingMovies_Yes",
    "Contract_One year",
    "Contract_Two year",
    "PaymentMethod_Credit card (automatic)",
    "PaymentMethod_Electronic check",
    "PaymentMethod_Mailed check",
    "avg_monthly_spend",
    "n_services",
    "tenure_bucket_1-2y",
    "tenure_bucket_2-4y",
    "tenure_bucket_4-6y",
    "sentiment_confidence",
    "satisfaction_score",
    "sentiment_negative",
    "sentiment_neutral",
    "sentiment_positive",
    "emotion_satisfaction",
    "emotion_calm",
    "emotion_frustration",
    "emotion_anger",
    "emotion_anxiety",
    "emotion_disappointment",
    "topic_payment_problem",
    "topic_refund_request",
    "topic_subscription_cancellation",
    "topic_security_concern",
    "topic_login_issue",
    "topic_bug_report",
    "topic_performance_issue",
    "topic_data_sync_issue",
    "topic_feature_request",
    "topic_account_suspension",
]

_ADDON_KEYS = (
    "online_security",
    "online_backup",
    "device_protection",
    "tech_support",
    "streaming_tv",
    "streaming_movies",
)


def _yes_no(value) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)) and value in (0, 1):
        return int(value)
    text = str(value).strip().lower()
    if text in {"yes", "true", "1"}:
        return 1
    if text in {"no", "false", "0"}:
        return 0
    raise ValueError(f"expected Yes/No, got {value!r}")


def _eq(value, expected: str) -> int:
    return int(str(value).strip() == expected)


def _tenure_bucket(tenure: int) -> dict[str, int]:
    label = pd.cut(
        [tenure],
        bins=[0, 12, 24, 48, 72],
        labels=["0-1y", "1-2y", "2-4y", "4-6y"],
    )[0]
    return {
        "tenure_bucket_1-2y": int(label == "1-2y"),
        "tenure_bucket_2-4y": int(label == "2-4y"),
        "tenure_bucket_4-6y": int(label == "4-6y"),
    }


def build_features(persona: Persona) -> pd.DataFrame:
    """One-row frame aligned on FEATURE_COLUMNS. Never includes Churn."""
    if not persona.is_enriched():
        raise ValueError("Persona must be sentiment-enriched before prediction")

    demo = persona.demographics or {}
    services = persona.services or {}
    contract = persona.contract or {}
    billing = persona.billing or {}

    tenure = int(contract["tenure"])
    monthly = float(billing["monthly_charges"])
    total = float(billing["total_charges"])
    gender = str(demo["gender"]).strip().lower()
    if gender not in {"male", "female"}:
        raise ValueError(f"unexpected gender: {demo.get('gender')!r}")

    row = {
        "gender": int(gender == "male"),
        "SeniorCitizen": int(bool(demo["senior_citizen"])),
        "Partner": _yes_no(demo["partner"]),
        "Dependents": _yes_no(demo["dependents"]),
        "tenure": tenure,
        "PhoneService": _yes_no(services["phone_service"]),
        "PaperlessBilling": _yes_no(contract["paperless_billing"]),
        "MonthlyCharges": monthly,
        "TotalCharges": total,
        "MultipleLines_No phone service": _eq(services["multiple_lines"], "No phone service"),
        "MultipleLines_Yes": _eq(services["multiple_lines"], "Yes"),
        "InternetService_Fiber optic": _eq(services["internet_service"], "Fiber optic"),
        "InternetService_No": _eq(services["internet_service"], "No"),
        "OnlineSecurity_No internet service": _eq(services["online_security"], "No internet service"),
        "OnlineSecurity_Yes": _eq(services["online_security"], "Yes"),
        "OnlineBackup_No internet service": _eq(services["online_backup"], "No internet service"),
        "OnlineBackup_Yes": _eq(services["online_backup"], "Yes"),
        "DeviceProtection_No internet service": _eq(services["device_protection"], "No internet service"),
        "DeviceProtection_Yes": _eq(services["device_protection"], "Yes"),
        "TechSupport_No internet service": _eq(services["tech_support"], "No internet service"),
        "TechSupport_Yes": _eq(services["tech_support"], "Yes"),
        "StreamingTV_No internet service": _eq(services["streaming_tv"], "No internet service"),
        "StreamingTV_Yes": _eq(services["streaming_tv"], "Yes"),
        "StreamingMovies_No internet service": _eq(services["streaming_movies"], "No internet service"),
        "StreamingMovies_Yes": _eq(services["streaming_movies"], "Yes"),
        "Contract_One year": _eq(contract["type"], "One year"),
        "Contract_Two year": _eq(contract["type"], "Two year"),
        "PaymentMethod_Credit card (automatic)": _eq(
            contract["payment_method"], "Credit card (automatic)"
        ),
        "PaymentMethod_Electronic check": _eq(contract["payment_method"], "Electronic check"),
        "PaymentMethod_Mailed check": _eq(contract["payment_method"], "Mailed check"),
        "avg_monthly_spend": total / (tenure if tenure else 1),
        "n_services": sum(_eq(services[key], "Yes") for key in _ADDON_KEYS),
        **_tenure_bucket(tenure),
        "sentiment_confidence": float(persona.sentiment_confidence or 0.0),
        "satisfaction_score": float(persona.satisfaction_score or 0.0),
    }
    for label in SENTIMENT_VALUES:
        row[f"sentiment_{label}"] = int(persona.sentiment == label)
    for emotion in EMOTION_VALUES:
        row[f"emotion_{emotion}"] = int(emotion in (persona.emotions or []))
    for topic in TOPIC_VALUES:
        row[_topic_column(topic)] = int(topic in (persona.complaint_topics or []))

    frame = pd.DataFrame([row], columns=FEATURE_COLUMNS)
    if "Churn" in frame.columns or "customerID" in frame.columns:
        raise ValueError("Churn/customerID must not appear in prediction features")
    return frame
