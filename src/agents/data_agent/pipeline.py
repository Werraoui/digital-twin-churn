"""
Data Agent ETL: ingest → clean → validate → RFM → synthetic → persona → warehouse.

This is the operational pipeline. It does not train ML models.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from sqlalchemy.engine import Engine

from src.agents.data_agent.behavioral import compute_retail_rfm
from src.agents.data_agent.clean import (
    clean_retail,
    clean_support_tickets,
    clean_telco,
    filter_retail_purchases,
)
from src.agents.data_agent.ingest import (
    load_online_retail_ii,
    load_support_tickets,
    load_telco,
)
from src.agents.data_agent.persona_builder import build_initial_persona
from src.agents.data_agent.repository import (
    replace_customers,
    replace_personas,
    replace_retail_rfm,
    replace_synthetic_events,
    replace_synthetic_reviews,
    upsert_meta,
)
from src.agents.data_agent.synthetic_behavior import extract_rfm_stats, generate_behavioral_history
from src.agents.data_agent.synthetic_reviews import (
    generate_client_review,
    infer_review_tone,
    sample_reference_tickets,
)
from src.agents.data_agent.validate import raise_if_any_errors, validate_cleaned_sources
from src.agents.data_agent.warehouse import init_db

logger = logging.getLogger(__name__)


def _customer_row(telco_client: pd.Series) -> dict:
    return {
        "customer_id": str(telco_client["customerID"]),
        "gender": telco_client["gender"],
        "senior_citizen": int(telco_client["SeniorCitizen"]),
        "partner": telco_client["Partner"],
        "dependents": telco_client["Dependents"],
        "tenure": int(telco_client["tenure"]),
        "phone_service": telco_client["PhoneService"],
        "multiple_lines": telco_client["MultipleLines"],
        "internet_service": telco_client["InternetService"],
        "online_security": telco_client["OnlineSecurity"],
        "online_backup": telco_client["OnlineBackup"],
        "device_protection": telco_client["DeviceProtection"],
        "tech_support": telco_client["TechSupport"],
        "streaming_tv": telco_client["StreamingTV"],
        "streaming_movies": telco_client["StreamingMovies"],
        "contract": telco_client["Contract"],
        "paperless_billing": telco_client["PaperlessBilling"],
        "payment_method": telco_client["PaymentMethod"],
        "monthly_charges": float(telco_client["MonthlyCharges"]),
        "total_charges": float(telco_client["TotalCharges"]),
    }


def _rfm_row(row: pd.Series) -> dict:
    return {
        "retail_customer_id": int(row["Customer ID"]),
        "last_purchase_date": pd.Timestamp(row["last_purchase_date"]).isoformat(),
        "recency_days": int(row["recency_days"]),
        "frequency": int(row["frequency"]),
        "monetary": float(row["monetary"]),
        "avg_order_value": float(row["avg_order_value"]),
        "r_score": int(row["r_score"]),
        "f_score": int(row["f_score"]),
        "m_score": int(row["m_score"]),
        "rfm_segment": str(row["rfm_segment"]),
    }


def run_data_agent_pipeline(
    *,
    telco_path: str | Path | None = None,
    retail_path: str | Path | None = None,
    tickets_path: str | Path | None = None,
    engine: Engine | None = None,
    seed: int = 42,
    max_customers: int | None = None,
) -> dict:
    """Run the full Data Agent ETL and persist results. Returns row counts."""
    engine = init_db(engine)

    telco = clean_telco(load_telco(telco_path) if telco_path else load_telco())
    retail = clean_retail(
        load_online_retail_ii(retail_path) if retail_path else load_online_retail_ii()
    )
    tickets = clean_support_tickets(
        load_support_tickets(tickets_path) if tickets_path else load_support_tickets()
    )
    purchases = filter_retail_purchases(retail)

    reports = validate_cleaned_sources(telco, retail, tickets, purchases=purchases)
    raise_if_any_errors(reports)

    rfm = compute_retail_rfm(purchases)
    rfm_stats = extract_rfm_stats(rfm)

    if max_customers is not None:
        telco = telco.head(int(max_customers)).copy()

    reference_by_tone = {
        tone: sample_reference_tickets(tickets, tone, n=30, seed=seed)
        for tone in ("negative", "neutral", "positive")
    }

    customers = []
    personas = []
    events = []
    reviews = []
    for _, client in telco.iterrows():
        history = generate_behavioral_history(client, rfm_stats, seed=seed)
        tone = infer_review_tone(client)
        review = generate_client_review(client, reference_by_tone[tone], seed=seed)
        persona = build_initial_persona(client, history, review, review_tone=tone)
        if "Churn" in persona.to_dict() or "churn" in persona.to_dict():
            raise RuntimeError("Persona payload must not contain Churn")

        customers.append(_customer_row(client))
        personas.append(persona)
        reviews.append({
            "customer_id": persona.customer_id,
            "tone": tone,
            "review_text": review,
            "lineage": "SYNTHETIC",
        })
        for record in persona.behavioral_history:
            events.append({
                "customer_id": persona.customer_id,
                "event_index": int(record["event_index"]),
                "months_before_snapshot": int(record["months_before_snapshot"]),
                "amount": float(record["amount"]),
                "event_type": record["event_type"],
                "lineage": record["lineage"],
                "profile": record["profile"],
            })

    counts = {
        "customers": replace_customers(customers, engine=engine),
        "retail_rfm": replace_retail_rfm([_rfm_row(row) for _, row in rfm.iterrows()], engine=engine),
        "synthetic_events": replace_synthetic_events(events, engine=engine),
        "synthetic_reviews": replace_synthetic_reviews(reviews, engine=engine),
        "personas": replace_personas(personas, engine=engine),
    }
    upsert_meta("rfm_stats", rfm_stats, engine=engine)
    logger.info("Data Agent pipeline loaded %s", counts)
    return counts


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run_data_agent_pipeline())
