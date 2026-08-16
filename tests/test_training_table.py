import pandas as pd
import pytest
from sqlalchemy import create_engine

from src.agents.data_agent.repository import replace_personas
from src.agents.data_agent.warehouse import init_db
from src.agents.prediction_agent.training_table import (
    build_training_table,
    export_training_table,
    personas_to_feature_frame,
)
from src.persona.schema import Persona


def _persona(customer_id: str, sentiment: str, topics: list[str], emotions: list[str]) -> Persona:
    return Persona(
        customer_id=customer_id,
        demographics={},
        services={},
        contract={},
        billing={},
        sentiment=sentiment,
        sentiment_confidence=0.91 if sentiment == "negative" else 0.77,
        emotions=emotions,
        complaint_topics=topics,
        satisfaction_score=1.18 if sentiment == "negative" else 4.54,
        lineage={"sentiment": "DERIVED"},
    )


def test_personas_to_feature_frame_encodes_sentiment_for_ml():
    features = personas_to_feature_frame([
        _persona("0001-AAAAA", "negative", ["Payment Problem"], ["frustration", "anger"]),
    ])
    assert features.loc[0, "sentiment_negative"] == 1
    assert features.loc[0, "sentiment_positive"] == 0
    assert features.loc[0, "emotion_anger"] == 1
    assert features.loc[0, "topic_payment_problem"] == 1
    assert features.loc[0, "topic_bug_report"] == 0
    assert "Churn" not in features.columns


def test_build_training_table_joins_on_customer_id_and_keeps_churn_as_target():
    telco_ml = pd.DataFrame({
        "tenure": [12, 36],
        "MonthlyCharges": [50.0, 90.0],
        "Churn": [1, 0],
        "customerID": ["0001-AAAAA", "0002-BBBBB"],
    })
    personas = [
        _persona("0001-AAAAA", "negative", ["Payment Problem"], ["frustration"]),
        _persona("0002-BBBBB", "positive", ["Bug Report"], ["satisfaction"]),
    ]
    table = build_training_table(telco_ml, personas)
    assert list(table["customerID"]) == ["0001-AAAAA", "0002-BBBBB"]
    assert list(table["Churn"]) == [1, 0]
    assert table.loc[0, "sentiment_negative"] == 1
    assert table.loc[1, "sentiment_positive"] == 1
    assert table.loc[0, "satisfaction_score"] == 1.18


def test_build_training_table_requires_enriched_personas():
    telco_ml = pd.DataFrame({
        "Churn": [1, 0],
        "customerID": ["0001-AAAAA", "0002-BBBBB"],
    })
    personas = [_persona("0001-AAAAA", "negative", [], ["frustration"])]
    with pytest.raises(ValueError, match="no enriched Persona sentiment"):
        build_training_table(telco_ml, personas, require_enriched=True)


def test_export_training_table_writes_ml_data_processed(tmp_path):
    source = tmp_path / "telco_clean_src.csv"
    dest = tmp_path / "ml_data" / "processed" / "telco_clean.csv"
    pd.DataFrame({
        "tenure": [12],
        "Churn": [1],
        "customerID": ["0001-AAAAA"],
    }).to_csv(source, index=False)

    engine = create_engine("sqlite:///:memory:", future=True)
    init_db(engine)
    replace_personas(
        [_persona("0001-AAAAA", "negative", ["Payment Problem"], ["anger"])],
        engine=engine,
    )

    written = export_training_table(
        telco_ml_path=source,
        output_path=dest,
        engine=engine,
    )
    out = pd.read_csv(written)
    assert written == dest
    assert "sentiment_negative" in out.columns
    assert out.loc[0, "Churn"] == 1
    assert out.loc[0, "customerID"] == "0001-AAAAA"
    assert "churn_risk_score" not in out.columns
