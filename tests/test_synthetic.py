import pandas as pd
import pytest

from src.agents.data_agent.synthetic_behavior import (
    HISTORY_COLUMNS,
    extract_rfm_stats,
    generate_behavioral_history,
)
from src.agents.data_agent.synthetic_reviews import (
    generate_client_review,
    infer_review_tone,
    sample_reference_tickets,
)


def _retail_line(customer_id, invoice, day, quantity=2, price=10.0):
    return {
        "Invoice": invoice,
        "StockCode": "85048",
        "Description": "GLASS BALL",
        "Quantity": quantity,
        "InvoiceDate": pd.Timestamp(day),
        "Price": price,
        "Customer ID": customer_id,
        "Country": "United Kingdom",
    }


def _rfm_stats():
    retail = pd.DataFrame([
        _retail_line(10001, "1001", "2010-01-01", quantity=2, price=5.0),
        _retail_line(10001, "1002", "2010-06-01", quantity=1, price=10.0),
        _retail_line(10002, "1003", "2010-03-01", quantity=4, price=8.0),
        _retail_line(10003, "1004", "2010-12-01", quantity=1, price=20.0),
    ])
    return extract_rfm_stats(retail)


def _telco(**overrides):
    row = {
        "customerID": "7590-VHVEG",
        "tenure": 24,
        "MonthlyCharges": 70.0,
        "Contract": "Month-to-month",
        "TechSupport": "No",
        "gender": "Female",
    }
    row.update(overrides)
    return pd.Series(row)


def test_extract_rfm_stats_has_quantiles_not_customer_ids():
    stats = _rfm_stats()
    assert "frequency" in stats
    assert "median" in stats["avg_order_value"]
    assert "Customer ID" not in stats


def test_synthetic_history_is_marked_and_ignores_churn():
    stats = _rfm_stats()
    without_churn = generate_behavioral_history(_telco(), stats, seed=42)
    with_yes = generate_behavioral_history(_telco(Churn="Yes"), stats, seed=42)
    with_no = generate_behavioral_history(_telco(Churn="No"), stats, seed=42)

    assert list(without_churn.columns) == HISTORY_COLUMNS
    assert (without_churn["lineage"] == "SYNTHETIC").all()
    assert "Customer ID" not in without_churn.columns
    assert "Churn" not in without_churn.columns
    pd.testing.assert_frame_equal(with_yes, with_no)
    pd.testing.assert_frame_equal(without_churn, with_yes)


def test_synthetic_history_is_deterministic_and_empty_for_new_customers():
    stats = _rfm_stats()
    first = generate_behavioral_history(_telco(), stats, seed=7)
    second = generate_behavioral_history(_telco(), stats, seed=7)
    pd.testing.assert_frame_equal(first, second)

    empty = generate_behavioral_history(_telco(tenure=0), stats, seed=7)
    assert list(empty.columns) == HISTORY_COLUMNS
    assert len(empty) == 0


def test_longer_tenure_gets_at_least_as_many_events():
    stats = _rfm_stats()
    short = generate_behavioral_history(_telco(tenure=6), stats, seed=1)
    long = generate_behavioral_history(_telco(tenure=48), stats, seed=1)
    assert len(long) >= len(short)
    assert len(short) >= 1


def test_review_tone_does_not_use_churn():
    assert infer_review_tone(_telco(Contract="Two year", TechSupport="Yes", Churn="Yes")) == "positive"
    assert infer_review_tone(_telco(Contract="Two year", TechSupport="Yes", Churn="No")) == "positive"
    assert infer_review_tone(_telco(Contract="Month-to-month", TechSupport="No")) == "negative"
    assert infer_review_tone(_telco(Contract="One year", TechSupport="No")) == "neutral"


def test_generate_review_samples_ticket_text_without_churn():
    tickets = pd.DataFrame({
        "category": ["Payment Problem", "Feature Request", "Login Issue"],
        "issue_description": [
            "There seems to be a discrepancy in my billing statement for this month.",
            "I found a bug in the latest update affecting report generation.",
            "I am unable to access my account after entering the correct credentials.",
        ],
        "customer_satisfaction_score": [2, 5, 4],
    })
    refs = sample_reference_tickets(tickets, "negative", n=10, seed=0)
    assert set(refs["category"]) <= {"Payment Problem"}

    text_yes = generate_client_review(_telco(Churn="Yes"), refs, seed=3)
    text_no = generate_client_review(_telco(Churn="No"), refs, seed=3)
    assert text_yes == text_no
    assert text_yes in set(tickets["issue_description"])


def test_sample_reference_tickets_rejects_unknown_tone():
    with pytest.raises(ValueError, match="tone must be one of"):
        sample_reference_tickets(
            pd.DataFrame({
                "category": ["Login Issue"],
                "issue_description": ["x"],
                "customer_satisfaction_score": [3],
            }),
            "angry",
        )
