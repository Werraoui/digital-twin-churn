from pathlib import Path

import pandas as pd
import pytest

from config.settings import TELCO_RAW_PATH
from src.agents.data_agent.clean import clean_telco
from src.agents.data_agent.ingest import TELCO_COLUMNS, load_telco


def test_clean_telco_fills_total_charges_for_tenure_zero():
    df = pd.DataFrame({
        "customerID": ["1", "2"],
        "tenure": [1, 0],
        "TotalCharges": ["29.85", " "],
        "Partner": ["Yes", "No"],
        "Churn": ["No", "No"],
    })

    cleaned = clean_telco(df)

    assert len(cleaned) == 2
    assert cleaned.loc[cleaned["customerID"] == "2", "TotalCharges"].iloc[0] == 0.0
    assert cleaned.loc[cleaned["customerID"] == "1", "TotalCharges"].iloc[0] == 29.85
    assert cleaned["TotalCharges"].dtype.kind == "f"
    assert cleaned.loc[cleaned["customerID"] == "1", "Partner"].iloc[0] == "Yes"
    assert cleaned.loc[cleaned["customerID"] == "1", "Churn"].iloc[0] == "No"


def test_clean_telco_does_not_encode_categoricals():
    df = pd.DataFrame({
        "customerID": ["1"],
        "tenure": [12],
        "TotalCharges": ["100.5"],
        "gender": ["Female"],
        "Contract": ["Month-to-month"],
        "InternetService": ["DSL"],
    })

    cleaned = clean_telco(df)

    assert cleaned.loc[0, "gender"] == "Female"
    assert cleaned.loc[0, "Contract"] == "Month-to-month"
    assert cleaned.loc[0, "InternetService"] == "DSL"


def test_clean_telco_drops_duplicate_customer_id():
    df = pd.DataFrame({
        "customerID": ["1", "1"],
        "tenure": [5, 5],
        "TotalCharges": ["50.0", "50.0"],
        "Partner": ["Yes", "No"],
    })

    cleaned = clean_telco(df)

    assert len(cleaned) == 1
    assert cleaned.iloc[0]["customerID"] == "1"
    assert cleaned.iloc[0]["Partner"] == "Yes"


def test_clean_telco_requires_key_columns():
    df = pd.DataFrame({"customerID": ["1"], "TotalCharges": ["10"]})
    with pytest.raises(ValueError, match="requires columns"):
        clean_telco(df)


@pytest.mark.skipif(not Path(TELCO_RAW_PATH).exists(), reason="raw Telco CSV is not present")
def test_clean_telco_keeps_all_real_rows_and_fills_new_customers():
    raw = load_telco()
    cleaned = clean_telco(raw)

    assert list(cleaned.columns) == TELCO_COLUMNS
    assert len(cleaned) == len(raw) == 7043
    assert int(cleaned["TotalCharges"].isna().sum()) == 0
    assert int((cleaned["tenure"] == 0).sum()) == 11
    assert (cleaned.loc[cleaned["tenure"] == 0, "TotalCharges"] == 0).all()
    assert cleaned["Partner"].isin(["Yes", "No"]).all()
    assert cleaned["Churn"].isin(["Yes", "No"]).all()
