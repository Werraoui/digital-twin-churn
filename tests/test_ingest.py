import importlib

import pandas as pd
import pytest

from src.agents.data_agent.ingest import (
    RETAIL_COLUMNS,
    TELCO_COLUMNS,
    TICKET_COLUMNS,
    load_online_retail_ii,
    load_support_tickets,
    load_telco,
)


def _write_csv(path, rows, columns):
    pd.DataFrame(rows, columns=columns).to_csv(path, index=False)
    return path


def test_importing_ingest_does_not_read_any_dataset(monkeypatch):
    def fail_read(*_args, **_kwargs):
        raise AssertionError("ingest import must not read datasets")

    monkeypatch.setattr(pd, "read_csv", fail_read)
    monkeypatch.setattr(pd, "read_excel", fail_read)
    ingest = importlib.import_module("src.agents.data_agent.ingest")
    importlib.reload(ingest)


def test_load_telco_reads_fixture_without_cleaning(tmp_path):
    path = _write_csv(
        tmp_path / "telco.csv",
        rows=[
            {
                "customerID": "7590-VHVEG",
                "gender": "Female",
                "SeniorCitizen": 0,
                "Partner": "Yes",
                "Dependents": "No",
                "tenure": 0,
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
                "TotalCharges": " ",
                "Churn": "No",
            }
        ],
        columns=TELCO_COLUMNS,
    )

    df = load_telco(path)

    assert list(df.columns) == TELCO_COLUMNS
    assert len(df) == 1
    assert df.loc[0, "customerID"] == "7590-VHVEG"
    assert df.loc[0, "TotalCharges"] == " "
    assert df.loc[0, "Churn"] == "No"


def test_load_telco_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="Dataset not found"):
        load_telco(tmp_path / "missing.csv")


def test_load_telco_rejects_non_csv(tmp_path):
    path = tmp_path / "telco.xlsx"
    path.write_text("not a csv", encoding="utf-8")
    with pytest.raises(ValueError, match="Expected a CSV file"):
        load_telco(path)


def test_load_telco_rejects_missing_columns(tmp_path):
    path = tmp_path / "telco.csv"
    pd.DataFrame({"customerID": ["1"], "gender": ["Male"]}).to_csv(path, index=False)
    with pytest.raises(ValueError, match="missing required columns"):
        load_telco(path)


def test_load_support_tickets_reads_fixture(tmp_path):
    row = {column: 0 if column in {
        "ticket_id",
        "customer_age",
        "customer_tenure_months",
        "previous_tickets",
        "customer_satisfaction_score",
        "issue_complexity_score",
    } else "x" for column in TICKET_COLUMNS}
    row["ticket_id"] = 1
    row["first_response_time_hours"] = 1.5
    row["resolution_time_hours"] = 3.0
    row["browser"] = None
    path = _write_csv(tmp_path / "tickets.csv", rows=[row], columns=TICKET_COLUMNS)

    df = load_support_tickets(path)

    assert list(df.columns) == TICKET_COLUMNS
    assert len(df) == 1
    assert df.loc[0, "ticket_id"] == 1
    assert pd.isna(df.loc[0, "browser"])


def test_load_online_retail_ii_csv_uses_nullable_customer_id(tmp_path):
    path = _write_csv(
        tmp_path / "retail.csv",
        rows=[
            {
                "Invoice": "489434",
                "StockCode": "85048",
                "Description": "GLASS BALL",
                "Quantity": 12,
                "InvoiceDate": "2009-12-01 07:45:00",
                "Price": 6.95,
                "Customer ID": 13085,
                "Country": "United Kingdom",
            },
            {
                "Invoice": "C489435",
                "StockCode": "85048",
                "Description": "GLASS BALL",
                "Quantity": -1,
                "InvoiceDate": "2009-12-01 08:00:00",
                "Price": 6.95,
                "Customer ID": None,
                "Country": "United Kingdom",
            },
        ],
        columns=RETAIL_COLUMNS,
    )

    df = load_online_retail_ii(path)

    assert list(df.columns) == RETAIL_COLUMNS
    assert len(df) == 2
    assert str(df["Customer ID"].dtype) == "Int64"
    assert df.loc[0, "Customer ID"] == 13085
    assert pd.isna(df.loc[1, "Customer ID"])
    assert df.loc[1, "Invoice"] == "C489435"
    assert df.loc[1, "Quantity"] == -1


def test_load_online_retail_ii_excel_concatenates_both_years(tmp_path):
    path = tmp_path / "online_retail_II.xlsx"
    year_1 = pd.DataFrame(
        [{
            "Invoice": "489434",
            "StockCode": "85048",
            "Description": "GLASS BALL",
            "Quantity": 12,
            "InvoiceDate": "2009-12-01 07:45:00",
            "Price": 6.95,
            "Customer ID": 13085,
            "Country": "United Kingdom",
        }]
    )
    year_2 = pd.DataFrame(
        [{
            "Invoice": "536365",
            "StockCode": "85123A",
            "Description": "WHITE HANGING HEART",
            "Quantity": 6,
            "InvoiceDate": "2010-12-01 08:26:00",
            "Price": 2.55,
            "Customer ID": 17850,
            "Country": "United Kingdom",
        }]
    )
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        year_1.to_excel(writer, sheet_name="Year 2009-2010", index=False)
        year_2.to_excel(writer, sheet_name="Year 2010-2011", index=False)

    df = load_online_retail_ii(path)

    assert len(df) == 2
    assert list(df.columns) == RETAIL_COLUMNS
    assert set(df["Invoice"].astype(str)) == {"489434", "536365"}
    assert str(df["Customer ID"].dtype) == "Int64"
    assert df["InvoiceDate"].dtype == "string"
