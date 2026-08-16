from pathlib import Path

import pandas as pd
import pytest

from config.settings import RETAIL_RAW_CSV_PATH, TELCO_RAW_PATH, TICKETS_RAW_PATH
from src.agents.data_agent.clean import (
    clean_retail,
    clean_support_tickets,
    clean_telco,
    filter_retail_purchases,
)
from src.agents.data_agent.ingest import (
    TICKET_COLUMNS,
    load_online_retail_ii,
    load_support_tickets,
    load_telco,
)
from src.agents.data_agent.validate import (
    TELCO_OPERATIONAL_COLUMNS,
    DataValidationError,
    raise_if_any_errors,
    validate_cleaned_sources,
    validate_no_unjustified_joins,
    validate_retail,
    validate_support_tickets,
    validate_telco,
)


def _telco_row(**overrides):
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
    return row


def _retail_row(**overrides):
    row = {
        "Invoice": "489434",
        "StockCode": "85048",
        "Description": "GLASS BALL",
        "Quantity": 12,
        "InvoiceDate": pd.Timestamp("2009-12-01 07:45:00"),
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
        "customer_email": "a@b.com",
        "product": "Mobile App",
        "category": "Login Issue",
        "priority": "Low",
        "status": "Closed",
        "channel": "Email",
        "region": "Europe",
        "customer_age": 30,
        "customer_gender": "Female",
        "subscription_type": "Basic",
        "customer_tenure_months": 10,
        "previous_tickets": 1,
        "customer_satisfaction_score": 4,
        "first_response_time_hours": 2.0,
        "resolution_time_hours": 8.0,
        "ticket_created_date": pd.Timestamp("2023-01-01"),
        "ticket_resolved_date": pd.Timestamp("2023-01-02"),
        "escalated": "No",
        "sla_breached": "No",
        "operating_system": "Windows",
        "browser": "Chrome",
        "payment_method": "Credit Card",
        "language": "English",
        "preferred_contact_time": "Morning",
        "issue_complexity_score": 3,
        "customer_segment": "Individual",
    })
    row.update(overrides)
    return row


def test_operational_columns_exclude_churn():
    assert "Churn" not in TELCO_OPERATIONAL_COLUMNS
    assert "customerID" in TELCO_OPERATIONAL_COLUMNS
    assert "MonthlyCharges" in TELCO_OPERATIONAL_COLUMNS


def test_validate_telco_accepts_clean_row():
    report = validate_telco(pd.DataFrame([_telco_row()]))
    assert report.ok


def test_validate_telco_rejects_unknown_contract():
    report = validate_telco(pd.DataFrame([_telco_row(Contract="Weekly")]))
    assert not report.ok
    assert any(issue.check == "allowed_values.Contract" for issue in report.errors)
    with pytest.raises(DataValidationError):
        report.raise_if_errors()


def test_validate_telco_rejects_phone_inconsistency():
    report = validate_telco(pd.DataFrame([
        _telco_row(PhoneService="No", MultipleLines="Yes"),
    ]))
    assert any(issue.check == "phone_consistency" for issue in report.errors)


def test_validate_retail_purchases_reject_guests_and_cancels():
    ok = validate_retail(pd.DataFrame([_retail_row()]), purchases_only=True)
    assert ok.ok

    guests = validate_retail(
        pd.DataFrame([_retail_row(**{"Customer ID": pd.NA})]),
        purchases_only=True,
    )
    assert any(issue.check == "Customer ID" for issue in guests.errors)

    cancels = validate_retail(
        pd.DataFrame([_retail_row(Invoice="C489435", Quantity=-1)]),
        purchases_only=True,
    )
    assert not cancels.ok


def test_validate_tickets_errors_on_reversed_dates_and_warns_on_open_resolved():
    bad = validate_support_tickets(pd.DataFrame([
        _ticket_row(
            ticket_resolved_date=pd.Timestamp("2022-01-01"),
            ticket_created_date=pd.Timestamp("2023-01-01"),
        )
    ]))
    assert any(issue.check == "date_order" for issue in bad.errors)

    warned = validate_support_tickets(pd.DataFrame([
        _ticket_row(status="Open", ticket_resolved_date=pd.Timestamp("2023-01-02")),
    ]))
    assert warned.ok
    assert any(issue.check == "open_with_resolved_date" for issue in warned.warnings)


def test_validate_no_unjustified_joins_detects_overlap():
    telco = pd.DataFrame([_telco_row(customerID="13085")])
    retail = pd.DataFrame([_retail_row(**{"Customer ID": 13085})])
    tickets = pd.DataFrame([_ticket_row()])
    report = validate_no_unjustified_joins(telco, retail, tickets)
    assert any(issue.check == "id_overlap" for issue in report.errors)


@pytest.mark.skipif(not Path(TELCO_RAW_PATH).exists(), reason="raw Telco CSV is not present")
@pytest.mark.skipif(not Path(RETAIL_RAW_CSV_PATH).exists(), reason="raw Retail CSV is not present")
@pytest.mark.skipif(not Path(TICKETS_RAW_PATH).exists(), reason="raw tickets CSV is not present")
def test_real_cleaned_sources_pass_validation_with_known_ticket_warnings():
    telco = clean_telco(load_telco())
    retail = clean_retail(load_online_retail_ii(RETAIL_RAW_CSV_PATH))
    purchases = filter_retail_purchases(retail)
    tickets = clean_support_tickets(load_support_tickets())

    reports = validate_cleaned_sources(telco, retail, tickets, purchases=purchases)
    raise_if_any_errors(reports)

    ticket_report = next(report for report in reports if report.dataset == "support_tickets")
    assert ticket_report.ok
    assert ticket_report.warnings
    assert "Churn" not in TELCO_OPERATIONAL_COLUMNS
