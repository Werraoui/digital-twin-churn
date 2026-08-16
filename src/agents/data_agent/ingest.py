"""
Data ingestion layer.

Responsibility:
    - Load raw datasets exactly as they exist on disk.
    - Do NOT clean, encode, scale, join, or generate synthetic data.

This module must have no import-time I/O. Call the load_* functions explicitly.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from config.settings import (
    RETAIL_RAW_CSV_PATH,
    RETAIL_RAW_XLSX_PATH,
    TELCO_RAW_PATH,
    TICKETS_RAW_PATH,
)

logger = logging.getLogger(__name__)

# Column contracts taken from the actual files. Do not invent names.
TELCO_COLUMNS = [
    "customerID",
    "gender",
    "SeniorCitizen",
    "Partner",
    "Dependents",
    "tenure",
    "PhoneService",
    "MultipleLines",
    "InternetService",
    "OnlineSecurity",
    "OnlineBackup",
    "DeviceProtection",
    "TechSupport",
    "StreamingTV",
    "StreamingMovies",
    "Contract",
    "PaperlessBilling",
    "PaymentMethod",
    "MonthlyCharges",
    "TotalCharges",
    "Churn",
]

RETAIL_COLUMNS = [
    "Invoice",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "Price",
    "Customer ID",
    "Country",
]

TICKET_COLUMNS = [
    "ticket_id",
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
    "customer_age",
    "customer_gender",
    "subscription_type",
    "customer_tenure_months",
    "previous_tickets",
    "customer_satisfaction_score",
    "first_response_time_hours",
    "resolution_time_hours",
    "ticket_created_date",
    "ticket_resolved_date",
    "escalated",
    "sla_breached",
    "operating_system",
    "browser",
    "payment_method",
    "language",
    "preferred_contact_time",
    "issue_complexity_score",
    "customer_segment",
]

# Pandas reads Retail Customer ID as float (13085.0). That is a loader artifact,
# not a business transformation. Int64 keeps missing guest checkouts as NA.
_RETAIL_CSV_DTYPES = {
    "Invoice": "string",
    "StockCode": "string",
    "Description": "string",
    "Quantity": "Int64",
    "InvoiceDate": "string",
    "Price": "float64",
    "Customer ID": "Int64",
    "Country": "string",
}


def _as_path(path: str | Path) -> Path:
    return Path(path)


def _require_exists(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    return path


def _require_columns(df: pd.DataFrame, expected: list[str], dataset_name: str) -> None:
    missing = [column for column in expected if column not in df.columns]
    if missing:
        raise ValueError(
            f"{dataset_name} is missing required columns: {missing}. "
            f"Found: {list(df.columns)}"
        )
    extra = [column for column in df.columns if column not in expected]
    if extra:
        logger.warning("%s has unexpected extra columns (kept as-is): %s", dataset_name, extra)


def _load_csv(path: str | Path, expected_columns: list[str], dataset_name: str, **read_csv_kwargs) -> pd.DataFrame:
    path = _require_exists(_as_path(path))
    if path.suffix.lower() != ".csv":
        raise ValueError(f"Expected a CSV file, got: {path.suffix}")

    df = pd.read_csv(path, **read_csv_kwargs)
    _require_columns(df, expected_columns, dataset_name)
    logger.info("Loaded %s: %s rows x %s columns from %s", dataset_name, len(df), df.shape[1], path)
    return df


def _normalize_retail_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Align Excel/CSV dtypes without changing values."""
    df = df.copy()
    _require_columns(df, RETAIL_COLUMNS, "Online Retail II")

    df["Invoice"] = df["Invoice"].astype("string")
    df["StockCode"] = df["StockCode"].astype("string")
    df["Description"] = df["Description"].astype("string")
    df["Country"] = df["Country"].astype("string")
    df["InvoiceDate"] = df["InvoiceDate"].astype("string")
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="raise").astype("Int64")
    df["Price"] = pd.to_numeric(df["Price"], errors="raise")
    df["Customer ID"] = pd.to_numeric(df["Customer ID"], errors="coerce").astype("Int64")
    return df.loc[:, RETAIL_COLUMNS]


def _load_retail_excel(path: Path) -> pd.DataFrame:
    sheets = pd.read_excel(path, sheet_name=None)
    if not sheets:
        raise ValueError(f"No sheets found in Excel file: {path}")

    frames = []
    for sheet_name, sheet_df in sheets.items():
        if sheet_df is None or sheet_df.empty:
            logger.warning("Skipping empty Retail sheet %r in %s", sheet_name, path)
            continue
        frames.append(_normalize_retail_frame(sheet_df))

    if not frames:
        raise ValueError(f"All sheets were empty in Excel file: {path}")

    df = pd.concat(frames, ignore_index=True)
    logger.info(
        "Loaded Online Retail II from Excel: %s rows from %s sheet(s) in %s",
        len(df),
        len(frames),
        path,
    )
    return df


def load_telco(path: str | Path | None = None) -> pd.DataFrame:
    """Load Telco Customer Churn exactly as stored in the raw CSV."""
    return _load_csv(
        path or TELCO_RAW_PATH,
        expected_columns=TELCO_COLUMNS,
        dataset_name="Telco Customer Churn",
    )


def load_online_retail_ii(path: str | Path | None = None) -> pd.DataFrame:
    """
    Load Online Retail II.

    This dataset is NOT joined to Telco. It is only used later to derive
    behavioral distributions.

    Default source is the Excel file (both years). The CSV currently contains
    only 2009-2010 and is used as a fallback, or when a CSV path is passed
    explicitly (tests).
    """
    if path is not None:
        path = _require_exists(_as_path(path))
        suffix = path.suffix.lower()
        if suffix == ".csv":
            df = pd.read_csv(path, dtype=_RETAIL_CSV_DTYPES)
            df = _normalize_retail_frame(df)
            logger.info("Loaded Online Retail II CSV: %s rows from %s", len(df), path)
            return df
        if suffix in {".xlsx", ".xls"}:
            return _load_retail_excel(path)
        raise ValueError(f"Expected a CSV or Excel file, got: {path.suffix}")

    xlsx_path = Path(RETAIL_RAW_XLSX_PATH)
    csv_path = Path(RETAIL_RAW_CSV_PATH)
    if xlsx_path.exists():
        return _load_retail_excel(xlsx_path)
    if csv_path.exists():
        logger.warning(
            "Retail Excel source missing (%s); falling back to CSV, "
            "which may contain only 2009-2010.",
            xlsx_path,
        )
        df = pd.read_csv(csv_path, dtype=_RETAIL_CSV_DTYPES)
        return _normalize_retail_frame(df)

    raise FileNotFoundError(
        f"Online Retail II not found. Looked for {xlsx_path} and {csv_path}."
    )


def load_support_tickets(path: str | Path | None = None) -> pd.DataFrame:
    """
    Load support tickets.

    This dataset is NOT joined to Telco. It is used later to derive
    support/satisfaction patterns and synthetic reviews.
    """
    return _load_csv(
        path or TICKETS_RAW_PATH,
        expected_columns=TICKET_COLUMNS,
        dataset_name="Support tickets",
    )
