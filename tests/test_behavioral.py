from pathlib import Path

import pandas as pd
import pytest

from config.settings import RETAIL_RAW_CSV_PATH, TELCO_RAW_PATH
from src.agents.data_agent.behavioral import (
    RFM_COLUMNS,
    compute_retail_rfm,
    summarize_rfm_distributions,
)
from src.agents.data_agent.clean import clean_retail, filter_retail_purchases
from src.agents.data_agent.ingest import load_online_retail_ii, load_telco


def _line(customer_id, invoice, day, quantity=1, price=10.0):
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


def test_compute_retail_rfm_one_row_per_customer_and_excludes_cancels():
    retail = pd.DataFrame([
        _line(10001, "1001", "2010-01-01", quantity=2, price=5.0),
        _line(10001, "1002", "2010-01-11", quantity=1, price=10.0),
        _line(10002, "1003", "2010-01-01", quantity=1, price=20.0),
        _line(10001, "C1004", "2010-01-12", quantity=-1, price=5.0),
        _line(None, "1005", "2010-01-02", quantity=3, price=8.0),
    ])

    rfm = compute_retail_rfm(retail, snapshot_date=pd.Timestamp("2010-01-11"))

    assert list(rfm.columns) == RFM_COLUMNS
    assert set(rfm["Customer ID"]) == {10001, 10002}
    assert "customerID" not in rfm.columns
    assert "Churn" not in rfm.columns

    first = rfm.set_index("Customer ID").loc[10001]
    assert first["frequency"] == 2
    assert first["monetary"] == 20.0
    assert first["avg_order_value"] == 10.0
    assert first["recency_days"] == 0

    second = rfm.set_index("Customer ID").loc[10002]
    assert second["frequency"] == 1
    assert second["monetary"] == 20.0
    assert second["recency_days"] == 10
    assert first["r_score"] >= second["r_score"]


def test_summarize_rfm_distributions_has_quantiles_not_ids():
    rfm = compute_retail_rfm(pd.DataFrame([
        _line(1, "2001", "2010-01-10", quantity=1, price=10),
        _line(2, "2002", "2010-01-01", quantity=5, price=10),
    ]))
    stats = summarize_rfm_distributions(rfm)

    assert stats["n_customers"] == 2
    assert "mean" in stats["frequency"]
    assert "p25" in stats["monetary"]
    assert "segment_counts" in stats
    assert "Customer ID" not in stats


def test_compute_retail_rfm_requires_retail_schema():
    with pytest.raises(ValueError, match="requires retail columns"):
        compute_retail_rfm(pd.DataFrame({"Customer ID": [1]}))


@pytest.mark.skipif(not Path(RETAIL_RAW_CSV_PATH).exists(), reason="raw Retail CSV is not present")
def test_real_retail_rfm_has_unique_ids_and_no_telco_overlap():
    retail = clean_retail(load_online_retail_ii(RETAIL_RAW_CSV_PATH))
    purchases = filter_retail_purchases(retail)
    rfm = compute_retail_rfm(purchases)
    stats = summarize_rfm_distributions(rfm)

    assert rfm["Customer ID"].is_unique
    assert rfm["Customer ID"].notna().all()
    assert (rfm["frequency"] >= 1).all()
    assert (rfm["monetary"] > 0).all()
    assert (rfm["recency_days"] >= 0).all()
    assert stats["n_customers"] == len(rfm)
    assert stats["n_customers"] == purchases["Customer ID"].nunique()

    if Path(TELCO_RAW_PATH).exists():
        telco_ids = set(load_telco()["customerID"].astype(str))
        retail_ids = set(rfm["Customer ID"].astype(str))
        assert telco_ids.isdisjoint(retail_ids)
