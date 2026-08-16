"""
SYNTHETIC review text for Telco customers.

Calibrated on Support Ticket *patterns* (categories + canned texts).
Never maps a ticket email/name onto a Telco customerID.
Never reads Churn.
"""

from __future__ import annotations

import hashlib
import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

VALID_TONES = ("negative", "neutral", "positive")

_TONE_CATEGORIES = {
    "negative": {
        "Payment Problem",
        "Subscription Cancellation",
        "Performance Issue",
        "Bug Report",
        "Refund Request",
        "Account Suspension",
    },
    "neutral": {
        "Login Issue",
        "Data Sync Issue",
        "Security Concern",
        "Feature Request",
    },
    "positive": {
        "Feature Request",
        "Login Issue",
        "Data Sync Issue",
    },
}

_REQUIRED_TICKET_COLUMNS = ("category", "issue_description", "customer_satisfaction_score")
_REQUIRED_TELCO_FIELDS = ("customerID", "Contract")


def _stable_rng(customer_id: str, seed: int | None = None) -> np.random.Generator:
    digest = hashlib.md5(str(customer_id).encode("utf-8")).hexdigest()[:8]
    customer_seed = int(digest, 16)
    base = 0 if seed is None else int(seed)
    return np.random.default_rng(base ^ customer_seed)


def infer_review_tone(telco_client: pd.Series) -> str:
    """
    Choose a review tone from REAL Telco fields only.

    Uses Contract and TechSupport. Does not use Churn.
    """
    contract = str(telco_client.get("Contract", ""))
    tech = str(telco_client.get("TechSupport", ""))

    if contract == "Two year" and tech == "Yes":
        return "positive"
    if contract == "Month-to-month" and tech == "No":
        return "negative"
    return "neutral"


def sample_reference_tickets(
    support_tickets_df: pd.DataFrame,
    tone: str,
    n: int = 20,
    seed: int | None = None,
) -> pd.DataFrame:
    """Sample real ticket rows whose category matches the requested tone."""
    if tone not in VALID_TONES:
        raise ValueError(f"tone must be one of {VALID_TONES}, got {tone!r}")

    missing = [column for column in _REQUIRED_TICKET_COLUMNS if column not in support_tickets_df.columns]
    if missing:
        raise ValueError(f"sample_reference_tickets requires {list(_REQUIRED_TICKET_COLUMNS)}. Missing: {missing}")

    pool = support_tickets_df.loc[
        support_tickets_df["category"].isin(_TONE_CATEGORIES[tone])
    ].copy()

    if tone == "positive" and not pool.empty:
        high_csat = pool["customer_satisfaction_score"] >= 4
        if int(high_csat.sum()) > 0:
            pool = pool.loc[high_csat]

    if pool.empty:
        logger.warning("No tickets for tone=%s; falling back to the full ticket table", tone)
        pool = support_tickets_df.copy()

    rng = np.random.default_rng(seed)
    take = min(int(n), len(pool))
    chosen = rng.choice(pool.index.to_numpy(), size=take, replace=False)
    return pool.loc[chosen].reset_index(drop=True)


def generate_client_review(
    telco_client: pd.Series,
    reference_tickets: pd.DataFrame,
    seed: int | None = None,
) -> str:
    """
    Pick one canned issue text from the reference tickets.

    The text is SYNTHETIC relative to the Telco customer: it is copied from
    another domain and is not a real review written by that customer.
    Churn is not used.
    """
    missing = [column for column in _REQUIRED_TELCO_FIELDS if column not in telco_client.index]
    if missing:
        raise ValueError(f"generate_client_review requires {list(_REQUIRED_TELCO_FIELDS)}. Missing: {missing}")
    if reference_tickets.empty or "issue_description" not in reference_tickets.columns:
        raise ValueError("reference_tickets must contain issue_description rows")

    rng = _stable_rng(str(telco_client["customerID"]), seed)
    texts = (
        reference_tickets["issue_description"]
        .astype("string")
        .dropna()
        .tolist()
    )
    if not texts:
        raise ValueError("reference_tickets has no issue_description text")

    index = int(rng.integers(0, len(texts)))
    return str(texts[index])
