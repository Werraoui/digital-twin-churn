from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine

from src.agents.data_agent.ingest import TELCO_COLUMNS, TICKET_COLUMNS
from src.agents.data_agent.pipeline import run_data_agent_pipeline
from src.agents.data_agent.repository import (
    CustomerNotFoundError,
    get_customer,
    get_persona,
    get_rfm_distributions,
    list_customers,
)
from src.agents.data_agent.warehouse import init_db


def _write_mini_sources(tmp_path: Path) -> dict:
    telco = pd.DataFrame([
        {
            "customerID": "0001-AAAAA",
            "gender": "Female",
            "SeniorCitizen": 0,
            "Partner": "Yes",
            "Dependents": "No",
            "tenure": 12,
            "PhoneService": "Yes",
            "MultipleLines": "No",
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
            "MonthlyCharges": 50.0,
            "TotalCharges": "600.0",
            "Churn": "Yes",
        },
        {
            "customerID": "0002-BBBBB",
            "gender": "Male",
            "SeniorCitizen": 0,
            "Partner": "No",
            "Dependents": "No",
            "tenure": 36,
            "PhoneService": "Yes",
            "MultipleLines": "Yes",
            "InternetService": "Fiber optic",
            "OnlineSecurity": "Yes",
            "OnlineBackup": "Yes",
            "DeviceProtection": "Yes",
            "TechSupport": "Yes",
            "StreamingTV": "Yes",
            "StreamingMovies": "Yes",
            "Contract": "Two year",
            "PaperlessBilling": "No",
            "PaymentMethod": "Credit card (automatic)",
            "MonthlyCharges": 90.0,
            "TotalCharges": "3000.0",
            "Churn": "No",
        },
    ], columns=TELCO_COLUMNS)

    retail = pd.DataFrame([
        {
            "Invoice": "1001",
            "StockCode": "85048",
            "Description": "GLASS BALL",
            "Quantity": 2,
            "InvoiceDate": "2010-01-01 10:00:00",
            "Price": 5.0,
            "Customer ID": 13085,
            "Country": "United Kingdom",
        },
        {
            "Invoice": "1002",
            "StockCode": "85048",
            "Description": "GLASS BALL",
            "Quantity": 3,
            "InvoiceDate": "2010-06-01 10:00:00",
            "Price": 8.0,
            "Customer ID": 13085,
            "Country": "United Kingdom",
        },
        {
            "Invoice": "1003",
            "StockCode": "85123A",
            "Description": "HEART",
            "Quantity": 1,
            "InvoiceDate": "2010-03-01 10:00:00",
            "Price": 20.0,
            "Customer ID": 17850,
            "Country": "United Kingdom",
        },
    ])

    tickets = pd.DataFrame([
        {**{column: "x" for column in TICKET_COLUMNS},
         "ticket_id": 1,
         "category": "Payment Problem",
         "issue_description": "There seems to be a discrepancy in my billing statement for this month.",
         "customer_satisfaction_score": 2,
         "customer_email": "a@b.com",
         "customer_age": 30,
         "customer_tenure_months": 10,
         "previous_tickets": 1,
         "first_response_time_hours": 2.0,
         "resolution_time_hours": 8.0,
         "ticket_created_date": "2023-01-01",
         "ticket_resolved_date": "2023-01-03",
         "escalated": "No",
         "sla_breached": "No",
         "product": "Billing System",
         "priority": "High",
         "status": "Closed",
         "channel": "Email",
         "region": "Europe",
         "customer_gender": "Female",
         "subscription_type": "Basic",
         "operating_system": "Windows",
         "browser": "Chrome",
         "payment_method": "Credit Card",
         "language": "English",
         "preferred_contact_time": "Morning",
         "issue_complexity_score": 4,
         "customer_segment": "Individual",
         },
        {**{column: "x" for column in TICKET_COLUMNS},
         "ticket_id": 2,
         "category": "Feature Request",
         "issue_description": "I found a bug in the latest update affecting report generation.",
         "customer_satisfaction_score": 5,
         "customer_email": "c@d.com",
         "customer_age": 40,
         "customer_tenure_months": 20,
         "previous_tickets": 0,
         "first_response_time_hours": 1.0,
         "resolution_time_hours": 5.0,
         "ticket_created_date": "2023-02-01",
         "ticket_resolved_date": "2023-02-02",
         "escalated": "No",
         "sla_breached": "No",
         "product": "Mobile App",
         "priority": "Low",
         "status": "Closed",
         "channel": "Chat",
         "region": "Asia",
         "customer_gender": "Male",
         "subscription_type": "Premium",
         "operating_system": "MacOS",
         "browser": "Safari",
         "payment_method": "PayPal",
         "language": "English",
         "preferred_contact_time": "Afternoon",
         "issue_complexity_score": 2,
         "customer_segment": "Individual",
         },
    ], columns=TICKET_COLUMNS)

    telco_path = tmp_path / "telco.csv"
    retail_path = tmp_path / "retail.csv"
    tickets_path = tmp_path / "tickets.csv"
    telco.to_csv(telco_path, index=False)
    retail.to_csv(retail_path, index=False)
    tickets.to_csv(tickets_path, index=False)
    return {"telco": telco_path, "retail": retail_path, "tickets": tickets_path}


def test_pipeline_loads_warehouse_without_churn_or_false_joins(tmp_path):
    paths = _write_mini_sources(tmp_path)
    engine = create_engine("sqlite:///:memory:", future=True)
    init_db(engine)

    counts = run_data_agent_pipeline(
        telco_path=paths["telco"],
        retail_path=paths["retail"],
        tickets_path=paths["tickets"],
        engine=engine,
        seed=42,
    )

    assert counts["customers"] == 2
    assert counts["personas"] == 2
    assert counts["retail_rfm"] == 2

    customers = list_customers(engine=engine)
    assert [row["customer_id"] for row in customers] == ["0001-AAAAA", "0002-BBBBB"]
    assert "churn" not in customers[0]

    persona = get_persona("0001-AAAAA", engine=engine)
    assert persona.lineage["raw_review_text"] == "SYNTHETIC"
    assert "Churn" not in persona.to_dict()
    assert get_customer("0001-AAAAA", engine=engine)["monthly_charges"] == 50.0
    stats = get_rfm_distributions(engine=engine)
    assert stats["n_customers"] == 2
    assert "Customer ID" not in stats

    with pytest.raises(CustomerNotFoundError):
        get_persona("does-not-exist", engine=engine)
