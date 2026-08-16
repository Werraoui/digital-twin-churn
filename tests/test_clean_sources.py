from pathlib import Path

import pandas as pd
import pytest

from config.settings import RETAIL_RAW_CSV_PATH, TELCO_RAW_PATH, TICKETS_RAW_PATH
from src.agents.data_agent.clean import (
    clean_retail,
    clean_support_tickets,
    filter_retail_purchases,
)
from src.agents.data_agent.ingest import (
    RETAIL_COLUMNS,
    TICKET_COLUMNS,
    load_online_retail_ii,
    load_support_tickets,
    load_telco,
)


def _retail_row(**overrides):
    row = {
        "Invoice": "489434",
        "StockCode": "85048",
        "Description": "GLASS BALL",
        "Quantity": 12,
        "InvoiceDate": "2009-12-01 07:45:00",
        "Price": 6.95,
        "Customer ID": 13085,
        "Country": "United Kingdom",
    }
    row.update(overrides)
    return row


def _ticket_row(**overrides):
    row = {column: "x" for column in TICKET_COLUMNS}
    row.update({
        "ticket_id": 1,
        "customer_email": "Pat.Smith@Outlook.com",
        "customer_age": 31,
        "customer_tenure_months": 12,
        "previous_tickets": 2,
        "customer_satisfaction_score": 4,
        "first_response_time_hours": 1.5,
        "resolution_time_hours": 10.0,
        "ticket_created_date": "2023-05-17",
        "ticket_resolved_date": "2023-05-20",
        "escalated": "No",
        "sla_breached": "Yes",
        "browser": None,
        "issue_complexity_score": 3,
    })
    row.update(overrides)
    return row


def test_clean_retail_parses_dates_and_drops_duplicate_rows():
    df = pd.DataFrame([
        _retail_row(),
        _retail_row(),
        _retail_row(Invoice="C489435", Quantity=-1, **{"Customer ID": None}),
    ], columns=RETAIL_COLUMNS)

    cleaned = clean_retail(df)

    assert len(cleaned) == 2
    assert pd.api.types.is_datetime64_any_dtype(cleaned["InvoiceDate"])
    assert str(cleaned["Customer ID"].dtype) == "Int64"
    assert pd.isna(cleaned.loc[cleaned["Invoice"] == "C489435", "Customer ID"].iloc[0])
    assert cleaned.loc[cleaned["Invoice"] == "C489435", "Quantity"].iloc[0] == -1


def test_clean_retail_does_not_invent_columns():
    cleaned = clean_retail(pd.DataFrame([_retail_row()], columns=RETAIL_COLUMNS))
    assert list(cleaned.columns) == RETAIL_COLUMNS


def test_filter_retail_purchases_keeps_only_identified_positive_lines():
    df = clean_retail(pd.DataFrame([
        _retail_row(),
        _retail_row(Invoice="C489435", Quantity=-1, **{"Customer ID": 13085}),
        _retail_row(Invoice="489436", Quantity=2, **{"Customer ID": None}),
        _retail_row(Invoice="489437", Price=0.0, Quantity=3),
        _retail_row(
            Invoice="A506401",
            StockCode="B",
            Description="Adjust bad debt",
            Quantity=1,
            Price=-53594.36,
            **{"Customer ID": None},
        ),
        _retail_row(Invoice="489438", Quantity=6, Price=2.55, **{"Customer ID": 17850}),
    ], columns=RETAIL_COLUMNS))

    purchases = filter_retail_purchases(df)

    assert set(purchases["Invoice"].astype(str)) == {"489434", "489438"}
    assert purchases["Customer ID"].notna().all()
    assert (purchases["Quantity"] > 0).all()
    assert (purchases["Price"] > 0).all()


def test_clean_support_tickets_parses_dates_and_keeps_browser_nulls():
    df = pd.DataFrame([
        _ticket_row(),
        _ticket_row(ticket_id=1, customer_email="dup@example.com"),
        _ticket_row(ticket_id=2, browser="Chrome"),
    ], columns=TICKET_COLUMNS)

    cleaned = clean_support_tickets(df)

    assert len(cleaned) == 2
    assert pd.api.types.is_datetime64_any_dtype(cleaned["ticket_created_date"])
    assert pd.api.types.is_datetime64_any_dtype(cleaned["ticket_resolved_date"])
    assert cleaned.loc[cleaned["ticket_id"] == 1, "customer_email"].iloc[0] == "pat.smith@outlook.com"
    assert pd.isna(cleaned.loc[cleaned["ticket_id"] == 1, "browser"].iloc[0])
    assert cleaned.loc[cleaned["ticket_id"] == 1, "escalated"].iloc[0] == "No"


def test_clean_support_tickets_does_not_encode_yes_no():
    cleaned = clean_support_tickets(pd.DataFrame([_ticket_row()], columns=TICKET_COLUMNS))
    assert cleaned.loc[0, "escalated"] == "No"
    assert cleaned.loc[0, "sla_breached"] == "Yes"


def test_clean_functions_require_source_columns():
    with pytest.raises(ValueError, match="clean_retail requires columns"):
        clean_retail(pd.DataFrame({"Invoice": ["1"]}))
    with pytest.raises(ValueError, match="clean_support_tickets requires columns"):
        clean_support_tickets(pd.DataFrame({"ticket_id": [1]}))


@pytest.mark.skipif(not Path(RETAIL_RAW_CSV_PATH).exists(), reason="raw Retail CSV is not present")
def test_clean_retail_real_csv_dedupes_and_does_not_join_telco():
    raw = load_online_retail_ii(RETAIL_RAW_CSV_PATH)
    cleaned = clean_retail(raw)
    purchases = filter_retail_purchases(cleaned)

    assert list(cleaned.columns) == RETAIL_COLUMNS
    assert len(cleaned) == len(raw) - int(raw.duplicated().sum())
    assert pd.api.types.is_datetime64_any_dtype(cleaned["InvoiceDate"])
    assert purchases["Customer ID"].notna().all()
    assert (purchases["Quantity"] > 0).all()
    assert (purchases["Price"] > 0).all()

    if Path(TELCO_RAW_PATH).exists():
        telco_ids = set(load_telco()["customerID"].astype(str))
        retail_ids = set(purchases["Customer ID"].astype(str))
        assert telco_ids.isdisjoint(retail_ids)


@pytest.mark.skipif(not Path(TICKETS_RAW_PATH).exists(), reason="raw tickets CSV is not present")
def test_clean_tickets_real_csv_keeps_rows_and_browser_nulls():
    raw = load_support_tickets()
    cleaned = clean_support_tickets(raw)

    assert list(cleaned.columns) == TICKET_COLUMNS
    assert len(cleaned) == 200_000
    assert pd.api.types.is_datetime64_any_dtype(cleaned["ticket_created_date"])
    assert int(cleaned["browser"].isna().sum()) == 40_023
    assert cleaned["escalated"].isin(["Yes", "No"]).all()
    assert "customerID" not in cleaned.columns
