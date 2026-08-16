"""Build the ML training table: encoded Telco + DERIVED sentiment features.

Does not train a model. Does not use sentiment to rewrite Churn.
Churn stays the target column only.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from sqlalchemy.engine import Engine

from config.settings import TELCO_ML_PATH, TELCO_ML_TRAINING_PATH
from src.agents.data_agent.repository import list_personas
from src.persona.schema import Persona

logger = logging.getLogger(__name__)

SENTIMENT_VALUES = ("negative", "neutral", "positive")
EMOTION_VALUES = (
    "satisfaction",
    "calm",
    "frustration",
    "anger",
    "anxiety",
    "disappointment",
)
TOPIC_VALUES = (
    "Payment Problem",
    "Refund Request",
    "Subscription Cancellation",
    "Security Concern",
    "Login Issue",
    "Bug Report",
    "Performance Issue",
    "Data Sync Issue",
    "Feature Request",
    "Account Suspension",
)


def _topic_column(topic: str) -> str:
    return "topic_" + topic.lower().replace(" ", "_")


def personas_to_feature_frame(personas: list[Persona]) -> pd.DataFrame:
    rows = []
    for persona in personas:
        row = {
            "customerID": persona.customer_id,
            "sentiment": persona.sentiment,
            "sentiment_confidence": persona.sentiment_confidence,
            "satisfaction_score": persona.satisfaction_score,
        }
        for label in SENTIMENT_VALUES:
            row[f"sentiment_{label}"] = int(persona.sentiment == label)
        for emotion in EMOTION_VALUES:
            row[f"emotion_{emotion}"] = int(emotion in (persona.emotions or []))
        for topic in TOPIC_VALUES:
            row[_topic_column(topic)] = int(topic in (persona.complaint_topics or []))
        rows.append(row)
    return pd.DataFrame(rows)


def build_training_table(
    telco_ml: pd.DataFrame,
    personas: list[Persona],
    *,
    require_enriched: bool = True,
) -> pd.DataFrame:
    """
    Left-join sentiment features onto the encoded Telco ML table by customerID.
    """
    if "customerID" not in telco_ml.columns:
        raise ValueError("telco ML table must contain customerID")
    if "Churn" not in telco_ml.columns:
        raise ValueError("telco ML table must contain Churn as the training target")

    features = personas_to_feature_frame(personas)
    if features.empty:
        raise ValueError("no Personas available to join onto the ML table")

    merged = telco_ml.merge(features, on="customerID", how="left")
    missing = merged["sentiment"].isna().sum()
    if require_enriched and missing:
        raise ValueError(
            f"{int(missing)} Telco rows have no enriched Persona sentiment. "
            "Run enrich_all_personas() first."
        )

    # Keep Churn as last training target; do not move it into features here.
    logger.info(
        "training table: %s rows, %s columns (%s missing sentiment)",
        len(merged),
        merged.shape[1],
        int(missing),
    )
    return merged


def export_training_table(
    *,
    telco_ml_path: str | Path | None = None,
    output_path: str | Path | None = None,
    engine: Engine | None = None,
    require_enriched: bool = True,
) -> Path:
    source = Path(telco_ml_path or TELCO_ML_PATH)
    dest = Path(output_path or TELCO_ML_TRAINING_PATH)
    telco_ml = pd.read_csv(source)
    personas = list_personas(engine=engine)
    if not personas:
        raise ValueError(
            "No Personas in the warehouse. Run the Data Agent first:\n"
            "  from src.agents.data_agent.pipeline import run_data_agent_pipeline\n"
            "  run_data_agent_pipeline()\n"
            "Then enrich them:\n"
            "  from src.agents.sentiment_agent.run import enrich_all_personas\n"
            "  enrich_all_personas()"
        )
    table = build_training_table(telco_ml, personas, require_enriched=require_enriched)
    dest.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(dest, index=False)
    logger.info("Wrote ML training table to %s", dest)
    return dest
