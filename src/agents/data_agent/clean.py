"""
Operational cleaning for each source dataset.

This is NOT the ML preprocessing pipeline.
Do NOT one-hot encode, scale, train/test split, or join sources here.
"""

from __future__ import annotations

import logging

import pandas as pd

from src.agents.data_agent.ingest import RETAIL_COLUMNS, TICKET_COLUMNS

logger = logging.getLogger(__name__)

_TELCO_REQUIRED_COLUMNS = ("customerID", "tenure", "TotalCharges")
_TICKET_YES_NO_COLUMNS = ("escalated", "sla_breached")
_TICKET_TEXT_COLUMNS = (
    "customer_name",
    "customer_email",
    "product",
    "category",
    "issue_description",
    "resolution_notes",
    "priority",
    "status",
    "channel",
    "region",
    "customer_gender",
    "subscription_type",
    "operating_system",
    "browser",
    "payment_method",
    "language",
    "preferred_contact_time",
    "customer_segment",
    *_TICKET_YES_NO_COLUMNS,
)


def _require_columns(df: pd.DataFrame, required: tuple[str, ...] | list[str], func_name: str) -> None:
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"{func_name} requires columns {list(required)}. Missing: {missing}")


def clean_telco(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean raw Telco without changing its meaning.

    - TotalCharges: string/blank -> numeric
    - tenure == 0 and missing TotalCharges -> 0 (new customer, nothing billed yet)
    - drop duplicate customerID, keep first
    - leave Yes/No, Churn, and service categories as-is
    """
    _require_columns(df, _TELCO_REQUIRED_COLUMNS, "clean_telco")

    df = df.copy()
    n_before = len(df)

    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")

    new_customers = df["tenure"] == 0
    n_filled = int(df.loc[new_customers, "TotalCharges"].isna().sum())
    df.loc[new_customers, "TotalCharges"] = df.loc[new_customers, "TotalCharges"].fillna(0)

    n_duplicate_ids = int(df["customerID"].duplicated().sum())
    df = df.drop_duplicates(subset=["customerID"], keep="first")

    logger.info(
        "clean_telco: %s -> %s rows; filled TotalCharges=0 for %s tenure=0 row(s); "
        "dropped %s duplicate customerID(s)",
        n_before,
        len(df),
        n_filled,
        n_duplicate_ids,
    )
    return df.reset_index(drop=True)


def clean_retail(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean Online Retail II line items without joining to Telco.

    Keeps cancellations, guest checkouts, and zero-price rows. They are real
    events. Use filter_retail_purchases() when you need RFM-eligible lines.
    """
    _require_columns(df, RETAIL_COLUMNS, "clean_retail")

    df = df.copy()
    n_before = len(df)

    df["Invoice"] = df["Invoice"].astype("string").str.strip()
    df["StockCode"] = df["StockCode"].astype("string").str.strip()
    df["Description"] = df["Description"].astype("string").str.strip()
    df["Country"] = df["Country"].astype("string").str.strip()
    df.loc[df["Description"].fillna("").eq(""), "Description"] = pd.NA

    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="raise").astype("Int64")
    df["Price"] = pd.to_numeric(df["Price"], errors="raise")
    df["Customer ID"] = pd.to_numeric(df["Customer ID"], errors="coerce").astype("Int64")

    n_duplicate_rows = int(df.duplicated().sum())
    df = df.drop_duplicates(keep="first")

    logger.info(
        "clean_retail: %s -> %s rows; dropped %s exact duplicate row(s); "
        "unparseable InvoiceDate=%s",
        n_before,
        len(df),
        n_duplicate_rows,
        int(df["InvoiceDate"].isna().sum()),
    )
    return df.reset_index(drop=True)


def filter_retail_purchases(df: pd.DataFrame) -> pd.DataFrame:
    """
    Keep line items that can enter RFM: identified customer, positive qty/price,
    not a cancellation invoice.

    This is a filter, not a join. Retail Customer ID stays a retail identifier.
    """
    _require_columns(df, RETAIL_COLUMNS, "filter_retail_purchases")

    invoice = df["Invoice"].astype("string")
    eligible = (
        df["Customer ID"].notna()
        & (df["Quantity"] > 0)
        & (df["Price"] > 0)
        & ~invoice.str.upper().str.startswith("C")
        & ~invoice.str.upper().str.startswith("A")
    )
    filtered = df.loc[eligible].reset_index(drop=True)
    logger.info(
        "filter_retail_purchases: %s -> %s RFM-eligible rows",
        len(df),
        len(filtered),
    )
    return filtered


def clean_support_tickets(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean support tickets without joining to Telco.

    Parses dates, strips text, drops duplicate ticket_id.
    Keeps browser nulls. Does not encode Yes/No to 0/1.
    """
    _require_columns(df, TICKET_COLUMNS, "clean_support_tickets")

    df = df.copy()
    n_before = len(df)

    for column in _TICKET_TEXT_COLUMNS:
        df[column] = df[column].astype("string").str.strip()

    df["customer_email"] = df["customer_email"].str.lower()

    df["ticket_created_date"] = pd.to_datetime(df["ticket_created_date"], errors="coerce")
    df["ticket_resolved_date"] = pd.to_datetime(df["ticket_resolved_date"], errors="coerce")

    df["ticket_id"] = pd.to_numeric(df["ticket_id"], errors="raise").astype("Int64")
    df["customer_age"] = pd.to_numeric(df["customer_age"], errors="raise").astype("Int64")
    df["customer_tenure_months"] = pd.to_numeric(
        df["customer_tenure_months"], errors="raise"
    ).astype("Int64")
    df["previous_tickets"] = pd.to_numeric(df["previous_tickets"], errors="raise").astype("Int64")
    df["customer_satisfaction_score"] = pd.to_numeric(
        df["customer_satisfaction_score"], errors="raise"
    ).astype("Int64")
    df["issue_complexity_score"] = pd.to_numeric(
        df["issue_complexity_score"], errors="raise"
    ).astype("Int64")
    df["first_response_time_hours"] = pd.to_numeric(
        df["first_response_time_hours"], errors="raise"
    )
    df["resolution_time_hours"] = pd.to_numeric(df["resolution_time_hours"], errors="raise")

    n_duplicate_ids = int(df["ticket_id"].duplicated().sum())
    df = df.drop_duplicates(subset=["ticket_id"], keep="first")

    logger.info(
        "clean_support_tickets: %s -> %s rows; dropped %s duplicate ticket_id(s); "
        "browser nulls kept=%s",
        n_before,
        len(df),
        n_duplicate_ids,
        int(df["browser"].isna().sum()),
    )
    return df.reset_index(drop=True)

