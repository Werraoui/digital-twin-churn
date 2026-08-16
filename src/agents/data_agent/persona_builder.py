"""Build the initial Persona from REAL Telco fields + SYNTHETIC enrichment."""

from __future__ import annotations

import pandas as pd

from src.persona.schema import Persona

_LINEAGE = {
    "demographics": "REAL",
    "services": "REAL",
    "contract": "REAL",
    "billing": "REAL",
    "behavioral_history": "SYNTHETIC",
    "raw_review_text": "SYNTHETIC",
    "review_tone": "DERIVED",
}


def _as_history_records(behavioral_history: pd.DataFrame | list | None) -> list[dict]:
    if behavioral_history is None:
        return []
    if isinstance(behavioral_history, pd.DataFrame):
        return behavioral_history.to_dict(orient="records")
    return [dict(row) for row in behavioral_history]


def build_initial_persona(
    telco_client: pd.Series,
    behavioral_history: pd.DataFrame | list | None,
    review_text: str | None,
    review_tone: str | None = None,
) -> Persona:
    """
    Assemble the operational Persona.

    Includes all REAL Telco profile fields except Churn.
    History and review are SYNTHETIC and must already have been generated
    without using Churn.
    """
    if "customerID" not in telco_client.index:
        raise ValueError("telco_client must contain customerID")

    return Persona(
        customer_id=str(telco_client["customerID"]),
        demographics={
            "gender": telco_client["gender"],
            "senior_citizen": bool(int(telco_client["SeniorCitizen"])),
            "partner": telco_client["Partner"],
            "dependents": telco_client["Dependents"],
        },
        services={
            "phone_service": telco_client["PhoneService"],
            "multiple_lines": telco_client["MultipleLines"],
            "internet_service": telco_client["InternetService"],
            "online_security": telco_client["OnlineSecurity"],
            "online_backup": telco_client["OnlineBackup"],
            "device_protection": telco_client["DeviceProtection"],
            "tech_support": telco_client["TechSupport"],
            "streaming_tv": telco_client["StreamingTV"],
            "streaming_movies": telco_client["StreamingMovies"],
        },
        contract={
            "type": telco_client["Contract"],
            "tenure": int(telco_client["tenure"]),
            "paperless_billing": telco_client["PaperlessBilling"],
            "payment_method": telco_client["PaymentMethod"],
        },
        billing={
            "monthly_charges": float(telco_client["MonthlyCharges"]),
            "total_charges": float(telco_client["TotalCharges"]),
        },
        behavioral_history=_as_history_records(behavioral_history),
        raw_review_text=review_text,
        review_tone=review_tone,
        lineage=dict(_LINEAGE),
    )
