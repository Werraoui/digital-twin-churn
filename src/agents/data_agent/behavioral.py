"""
Derived RFM features from Online Retail II.

Retail Customer ID is a retail identifier. These rows are never joined to Telco.
Churn is not used. Output is DERIVED, not SYNTHETIC.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from src.agents.data_agent.clean import filter_retail_purchases
from src.agents.data_agent.ingest import RETAIL_COLUMNS

logger = logging.getLogger(__name__)

RFM_COLUMNS = [
    "Customer ID",
    "last_purchase_date",
    "recency_days",
    "frequency",
    "monetary",
    "avg_order_value",
    "r_score",
    "f_score",
    "m_score",
    "rfm_segment",
]


def _require_retail_columns(df: pd.DataFrame) -> None:
    missing = [column for column in RETAIL_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"compute_retail_rfm requires retail columns. Missing: {missing}")


def _score(series: pd.Series, *, higher_is_better: bool) -> pd.Series:
    """Map a metric to 1-4. 4 is best (recent / frequent / high spend)."""
    percentile = series.rank(method="average", pct=True, ascending=higher_is_better)
    values = np.clip(np.ceil(percentile.to_numpy(dtype="float64") * 4), 1, 4).astype("int64")
    return pd.Series(values, index=series.index, dtype="Int64")


def _segment(r_score: int, f_score: int, m_score: int) -> str:
    if r_score >= 3 and f_score >= 3 and m_score >= 3:
        return "champion"
    if r_score >= 3 and f_score <= 2:
        return "new"
    if r_score <= 2 and f_score >= 3:
        return "at_risk"
    if r_score <= 2 and f_score <= 2:
        return "hibernating"
    if f_score >= 3:
        return "loyal"
    return "other"


def compute_retail_rfm(
    retail_df: pd.DataFrame,
    snapshot_date: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """
    One RFM row per retail customer, from purchase lines only.

    Recency  = days between snapshot (default: last invoice date) and last purchase
    Frequency = number of distinct invoices
    Monetary  = sum(Quantity * Price)
    """
    _require_retail_columns(retail_df)
    purchases = filter_retail_purchases(retail_df)
    if purchases.empty:
        return pd.DataFrame(columns=RFM_COLUMNS)

    purchases = purchases.copy()
    purchases["line_value"] = purchases["Quantity"].astype("float64") * purchases["Price"]

    grouped = purchases.groupby("Customer ID", dropna=True)
    rfm = pd.DataFrame({
        "last_purchase_date": grouped["InvoiceDate"].max(),
        "frequency": grouped["Invoice"].nunique(),
        "monetary": grouped["line_value"].sum(),
    }).reset_index()

    snapshot = pd.Timestamp(snapshot_date) if snapshot_date is not None else rfm["last_purchase_date"].max()
    rfm["recency_days"] = (snapshot - rfm["last_purchase_date"]).dt.days.astype("Int64")
    rfm["avg_order_value"] = (rfm["monetary"] / rfm["frequency"]).astype("float64")

    rfm["r_score"] = _score(rfm["recency_days"], higher_is_better=False)
    rfm["f_score"] = _score(rfm["frequency"], higher_is_better=True)
    rfm["m_score"] = _score(rfm["monetary"], higher_is_better=True)
    rfm["rfm_segment"] = [
        _segment(int(r), int(f), int(m))
        for r, f, m in zip(rfm["r_score"], rfm["f_score"], rfm["m_score"])
    ]

    rfm = rfm.loc[:, RFM_COLUMNS]
    logger.info(
        "compute_retail_rfm: %s retail customers; snapshot=%s",
        len(rfm),
        pd.Timestamp(snapshot).date(),
    )
    return rfm.reset_index(drop=True)


def summarize_rfm_distributions(rfm: pd.DataFrame) -> dict:
    """
    Quantiles of RFM metrics. Step 6 samples from these; it does not join IDs.
    """
    if rfm.empty:
        raise ValueError("summarize_rfm_distributions requires a non-empty RFM table")

    def _stats(series: pd.Series) -> dict[str, float]:
        return {
            "min": float(series.min()),
            "p25": float(series.quantile(0.25)),
            "median": float(series.median()),
            "p75": float(series.quantile(0.75)),
            "max": float(series.max()),
            "mean": float(series.mean()),
            "std": float(series.std(ddof=0)),
        }

    snapshot = pd.Timestamp(rfm["last_purchase_date"].max())
    return {
        "n_customers": int(len(rfm)),
        "snapshot_date": snapshot.isoformat(),
        "recency_days": _stats(rfm["recency_days"].astype("float64")),
        "frequency": _stats(rfm["frequency"].astype("float64")),
        "monetary": _stats(rfm["monetary"].astype("float64")),
        "avg_order_value": _stats(rfm["avg_order_value"].astype("float64")),
        "segment_counts": rfm["rfm_segment"].value_counts().to_dict(),
    }
