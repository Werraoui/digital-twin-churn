"""
Validate cleaned datasets against contracts from the real files.

Does not clean, join sources, or train models.
Errors fail the pipeline. Warnings are recorded but do not fail.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from src.agents.data_agent.ingest import RETAIL_COLUMNS, TELCO_COLUMNS, TICKET_COLUMNS

TELCO_OPERATIONAL_COLUMNS = [column for column in TELCO_COLUMNS if column != "Churn"]

TELCO_ALLOWED_VALUES = {
    "gender": {"Female", "Male"},
    "SeniorCitizen": {0, 1},
    "Partner": {"Yes", "No"},
    "Dependents": {"Yes", "No"},
    "PhoneService": {"Yes", "No"},
    "MultipleLines": {"Yes", "No", "No phone service"},
    "InternetService": {"DSL", "Fiber optic", "No"},
    "OnlineSecurity": {"Yes", "No", "No internet service"},
    "OnlineBackup": {"Yes", "No", "No internet service"},
    "DeviceProtection": {"Yes", "No", "No internet service"},
    "TechSupport": {"Yes", "No", "No internet service"},
    "StreamingTV": {"Yes", "No", "No internet service"},
    "StreamingMovies": {"Yes", "No", "No internet service"},
    "Contract": {"Month-to-month", "One year", "Two year"},
    "PaperlessBilling": {"Yes", "No"},
    "PaymentMethod": {
        "Electronic check",
        "Mailed check",
        "Bank transfer (automatic)",
        "Credit card (automatic)",
    },
    "Churn": {"Yes", "No"},
}

_INTERNET_ADDONS = (
    "OnlineSecurity",
    "OnlineBackup",
    "DeviceProtection",
    "TechSupport",
    "StreamingTV",
    "StreamingMovies",
)

TICKET_ALLOWED_VALUES = {
    "priority": {"High", "Urgent", "Medium", "Low"},
    "status": {"In Progress", "Closed", "Pending Customer", "Resolved", "Open"},
    "channel": {"Web Form", "Chat", "Phone", "Social Media", "Email"},
    "region": {"Africa", "Asia", "South America", "Europe", "North America", "Australia"},
    "customer_gender": {"Male", "Female", "Other"},
    "subscription_type": {"Free", "Basic", "Premium", "Enterprise"},
    "escalated": {"Yes", "No"},
    "sla_breached": {"Yes", "No"},
    "operating_system": {"Android", "iOS", "Linux", "MacOS", "Windows"},
    "browser": {"Safari", "Firefox", "Chrome", "Edge"},
    "payment_method": {"Crypto", "Bank Transfer", "Credit Card", "PayPal", "Debit Card"},
    "language": {"Japanese", "English", "French", "German", "Spanish", "Chinese"},
    "preferred_contact_time": {"Morning", "Afternoon", "Evening", "Night"},
    "customer_segment": {"Individual", "Corporate", "Small Business"},
    "product": {
        "Billing System",
        "CRM Platform",
        "E-commerce Store",
        "Cloud Storage",
        "Mobile App",
        "Analytics Dashboard",
        "Web Portal",
        "Payment Gateway",
        "Subscription Service",
        "API Service",
    },
    "category": {
        "Feature Request",
        "Subscription Cancellation",
        "Performance Issue",
        "Security Concern",
        "Login Issue",
        "Payment Problem",
        "Bug Report",
        "Refund Request",
        "Data Sync Issue",
        "Account Suspension",
    },
}

_OPEN_TICKET_STATUSES = {"Open", "In Progress", "Pending Customer"}


class DataValidationError(ValueError):
    """Raised when a validation report contains errors."""


@dataclass
class ValidationIssue:
    severity: str
    dataset: str
    check: str
    message: str
    n_rows: int | None = None


@dataclass
class ValidationReport:
    dataset: str
    issues: list[ValidationIssue] = field(default_factory=list)

    def add(self, severity: str, check: str, message: str, n_rows: int | None = None) -> None:
        self.issues.append(
            ValidationIssue(
                severity=severity,
                dataset=self.dataset,
                check=check,
                message=message,
                n_rows=n_rows,
            )
        )

    @property
    def errors(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def raise_if_errors(self) -> None:
        if self.ok:
            return
        details = "; ".join(
            f"{issue.check}: {issue.message}" for issue in self.errors
        )
        raise DataValidationError(f"{self.dataset} validation failed: {details}")


def _missing_columns(df: pd.DataFrame, expected: list[str], report: ValidationReport) -> None:
    missing = [column for column in expected if column not in df.columns]
    if missing:
        report.add("error", "schema", f"missing columns: {missing}")


def _duplicate_or_null_key(series: pd.Series, report: ValidationReport, check: str) -> None:
    n_null = int(series.isna().sum())
    if n_null:
        report.add("error", check, "identifier contains nulls", n_rows=n_null)
    n_dup = int(series.duplicated().sum())
    if n_dup:
        report.add("error", check, "identifier contains duplicates", n_rows=n_dup)


def _allowed_values(df: pd.DataFrame, allowed: dict[str, set], report: ValidationReport) -> None:
    for column, values in allowed.items():
        if column not in df.columns:
            continue
        observed = set(df[column].dropna().unique())
        invalid = observed - values
        if invalid:
            n_rows = int((~df[column].isin(values) & df[column].notna()).sum())
            report.add(
                "error",
                f"allowed_values.{column}",
                f"unexpected values: {sorted(invalid, key=str)}",
                n_rows=n_rows,
            )


def validate_telco(df: pd.DataFrame) -> ValidationReport:
    report = ValidationReport("telco")
    _missing_columns(df, TELCO_COLUMNS, report)
    if report.errors:
        return report

    if "Churn" in TELCO_OPERATIONAL_COLUMNS:
        report.add("error", "churn_leakage", "Churn must not be an operational feature")

    _duplicate_or_null_key(df["customerID"], report, "customerID")

    if int(df["TotalCharges"].isna().sum()):
        report.add(
            "error",
            "TotalCharges",
            "null TotalCharges after cleaning",
            n_rows=int(df["TotalCharges"].isna().sum()),
        )
    if int((df["MonthlyCharges"] < 0).sum()):
        report.add("error", "MonthlyCharges", "negative MonthlyCharges", n_rows=int((df["MonthlyCharges"] < 0).sum()))
    if int((df["tenure"] < 0).sum()):
        report.add("error", "tenure", "negative tenure", n_rows=int((df["tenure"] < 0).sum()))

    bad_new = (df["tenure"] == 0) & (df["TotalCharges"] != 0)
    if int(bad_new.sum()):
        report.add(
            "error",
            "tenure0_total_charges",
            "tenure=0 rows must have TotalCharges=0",
            n_rows=int(bad_new.sum()),
        )

    phone_no = df["PhoneService"] == "No"
    bad_phone = phone_no & (df["MultipleLines"] != "No phone service")
    if int(bad_phone.sum()):
        report.add(
            "error",
            "phone_consistency",
            "PhoneService=No must have MultipleLines='No phone service'",
            n_rows=int(bad_phone.sum()),
        )

    internet_no = df["InternetService"] == "No"
    for column in _INTERNET_ADDONS:
        bad_addon = internet_no & (df[column] != "No internet service")
        if int(bad_addon.sum()):
            report.add(
                "error",
                f"internet_consistency.{column}",
                "InternetService=No must have add-on='No internet service'",
                n_rows=int(bad_addon.sum()),
            )

    _allowed_values(df, TELCO_ALLOWED_VALUES, report)
    return report


def validate_retail(df: pd.DataFrame, *, purchases_only: bool = False) -> ValidationReport:
    report = ValidationReport("retail_purchases" if purchases_only else "retail")
    _missing_columns(df, RETAIL_COLUMNS, report)
    if report.errors:
        return report

    if not pd.api.types.is_datetime64_any_dtype(df["InvoiceDate"]):
        report.add("error", "InvoiceDate", "InvoiceDate must be datetime after cleaning")
    n_bad_dates = int(df["InvoiceDate"].isna().sum())
    if n_bad_dates:
        report.add("error", "InvoiceDate", "unparseable InvoiceDate", n_rows=n_bad_dates)

    if purchases_only:
        n_guest = int(df["Customer ID"].isna().sum())
        if n_guest:
            report.add("error", "Customer ID", "purchases cannot include guest checkouts", n_rows=n_guest)
        n_qty = int((df["Quantity"] <= 0).sum())
        if n_qty:
            report.add("error", "Quantity", "purchases must have Quantity > 0", n_rows=n_qty)
        n_price = int((df["Price"] <= 0).sum())
        if n_price:
            report.add("error", "Price", "purchases must have Price > 0", n_rows=n_price)
        invoice = df["Invoice"].astype("string").str.upper()
        n_cancel = int(invoice.str.startswith("C").sum() + invoice.str.startswith("A").sum())
        if n_cancel:
            report.add("error", "Invoice", "purchases cannot include cancel/adjustment invoices", n_rows=n_cancel)
    return report


def validate_support_tickets(df: pd.DataFrame) -> ValidationReport:
    report = ValidationReport("support_tickets")
    _missing_columns(df, TICKET_COLUMNS, report)
    if report.errors:
        return report

    if "customerID" in df.columns:
        report.add("error", "no_telco_join", "tickets must not contain Telco customerID")

    _duplicate_or_null_key(df["ticket_id"], report, "ticket_id")

    if not pd.api.types.is_datetime64_any_dtype(df["ticket_created_date"]):
        report.add("error", "ticket_created_date", "must be datetime after cleaning")
    if not pd.api.types.is_datetime64_any_dtype(df["ticket_resolved_date"]):
        report.add("error", "ticket_resolved_date", "must be datetime after cleaning")

    n_order = int((df["ticket_resolved_date"] < df["ticket_created_date"]).sum())
    if n_order:
        report.add(
            "error",
            "date_order",
            "ticket_resolved_date is before ticket_created_date",
            n_rows=n_order,
        )

    csat = df["customer_satisfaction_score"]
    n_csat = int((~csat.between(1, 5)).sum())
    if n_csat:
        report.add("error", "customer_satisfaction_score", "must be between 1 and 5", n_rows=n_csat)

    _allowed_values(df, TICKET_ALLOWED_VALUES, report)

    open_with_resolved = df["status"].isin(_OPEN_TICKET_STATUSES) & df["ticket_resolved_date"].notna()
    n_open = int(open_with_resolved.sum())
    if n_open:
        report.add(
            "warning",
            "open_with_resolved_date",
            "open/in-progress tickets have a resolved date (known synthetic-data quirk)",
            n_rows=n_open,
        )

    n_sla = int((df["first_response_time_hours"] > df["resolution_time_hours"]).sum())
    if n_sla:
        report.add(
            "warning",
            "response_after_resolution",
            "first_response_time_hours > resolution_time_hours (known synthetic-data quirk)",
            n_rows=n_sla,
        )
    return report


def validate_no_unjustified_joins(
    telco: pd.DataFrame,
    retail: pd.DataFrame,
    tickets: pd.DataFrame,
) -> ValidationReport:
    report = ValidationReport("cross_source")
    if "customerID" not in telco.columns or "Customer ID" not in retail.columns:
        report.add("error", "schema", "cannot check joins without Telco customerID and Retail Customer ID")
        return report

    telco_ids = set(telco["customerID"].dropna().astype(str))
    retail_ids = set(retail["Customer ID"].dropna().astype(str))
    overlap = telco_ids & retail_ids
    if overlap:
        report.add(
            "error",
            "id_overlap",
            "Telco customerID overlaps Retail Customer ID; do not join these tables",
            n_rows=len(overlap),
        )

    if "customerID" in tickets.columns:
        report.add("error", "ticket_telco_key", "support tickets contain Telco customerID")
    return report


def validate_cleaned_sources(
    telco: pd.DataFrame,
    retail: pd.DataFrame,
    tickets: pd.DataFrame,
    purchases: pd.DataFrame | None = None,
) -> list[ValidationReport]:
    reports = [
        validate_telco(telco),
        validate_retail(retail, purchases_only=False),
        validate_support_tickets(tickets),
        validate_no_unjustified_joins(telco, retail, tickets),
    ]
    if purchases is not None:
        reports.append(validate_retail(purchases, purchases_only=True))
        reports.append(validate_no_unjustified_joins(telco, purchases, tickets))
    return reports


def raise_if_any_errors(reports: list[ValidationReport]) -> None:
    failed = [report for report in reports if not report.ok]
    if not failed:
        return
    parts = [f"{report.dataset} ({len(report.errors)} error(s))" for report in failed]
    raise DataValidationError("validation failed: " + ", ".join(parts))
