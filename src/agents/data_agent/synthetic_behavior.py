"""
SYNTHETIC behavioral history for Telco customers.

Calibrated on Online Retail II RFM *distributions* (Step 5).
Never joins a Retail Customer ID to a Telco customerID.
Never reads Churn.
"""

from __future__ import annotations

import hashlib
import logging

import numpy as np
import pandas as pd

from src.agents.data_agent.behavioral import (
    RFM_COLUMNS,
    compute_retail_rfm,
    summarize_rfm_distributions,
)

logger = logging.getLogger(__name__)

HISTORY_COLUMNS = [
    "event_index",
    "months_before_snapshot",
    "amount",
    "event_type",
    "lineage",
    "profile",
]

_REQUIRED_TELCO_FIELDS = ("customerID", "tenure", "MonthlyCharges")
_MAX_EVENTS = 24


def _stable_rng(customer_id: str, seed: int | None = None) -> np.random.Generator:
    digest = hashlib.md5(str(customer_id).encode("utf-8")).hexdigest()[:8]
    customer_seed = int(digest, 16)
    base = 0 if seed is None else int(seed)
    return np.random.default_rng(base ^ customer_seed)


def extract_rfm_stats(online_retail_df: pd.DataFrame) -> dict:
    """Build RFM distribution stats from Retail transactions or an RFM table."""
    if set(RFM_COLUMNS).issubset(online_retail_df.columns):
        rfm = online_retail_df
    else:
        rfm = compute_retail_rfm(online_retail_df)
    return summarize_rfm_distributions(rfm)


def _require_stats(rfm_stats: dict) -> None:
    for key in ("frequency", "avg_order_value", "recency_days"):
        if key not in rfm_stats or "median" not in rfm_stats[key]:
            raise ValueError(
                f"rfm_stats must contain '{key}.median' from summarize_rfm_distributions"
            )


def generate_behavioral_history(
    telco_client: pd.Series,
    rfm_stats: dict,
    seed: int | None = None,
) -> pd.DataFrame:
    """
    Create a SYNTHETIC event timeline for one Telco customer.

    Count and spacing are inspired by Retail RFM quantiles, then scaled with
    tenure and MonthlyCharges. Churn is ignored even if present on the row.
    """
    missing = [column for column in _REQUIRED_TELCO_FIELDS if column not in telco_client.index]
    if missing:
        raise ValueError(f"generate_behavioral_history requires {list(_REQUIRED_TELCO_FIELDS)}. Missing: {missing}")
    _require_stats(rfm_stats)

    tenure = int(telco_client["tenure"])
    monthly_charges = float(telco_client["MonthlyCharges"])
    customer_id = str(telco_client["customerID"])
    rng = _stable_rng(customer_id, seed)

    if tenure <= 0:
        return pd.DataFrame(columns=HISTORY_COLUMNS)

    freq_median = max(float(rfm_stats["frequency"]["median"]), 1.0)
    # Retail RFM is roughly a 12-month window; scale to Telco tenure in months.
    n_events = int(round(freq_median * tenure / 12.0))
    n_events = int(np.clip(n_events, 1, min(_MAX_EVENTS, tenure)))

    recency_months = int(round(float(rfm_stats["recency_days"]["median"]) / 30.0))
    recency_months = int(np.clip(recency_months, 0, max(tenure - 1, 0)))

    # Spread events over the tenure window, ending near the sampled recency.
    last_event = recency_months
    first_event = tenure - 1
    if first_event < last_event:
        first_event = last_event
    months = np.linspace(first_event, last_event, n_events)
    months = np.clip(np.rint(months), 0, tenure).astype(int)

    aov_median = max(float(rfm_stats["avg_order_value"]["median"]), 1.0)
    aov_low = float(rfm_stats["avg_order_value"]["p25"])
    aov_high = float(rfm_stats["avg_order_value"]["p75"])
    if aov_high <= aov_low:
        aov_sample = aov_low
    else:
        aov_sample = float(rng.uniform(aov_low, aov_high))
    scale = aov_sample / aov_median
    noise = rng.uniform(0.85, 1.15, size=n_events)
    amounts = np.clip(monthly_charges * scale * noise, 0.01, None)

    history = pd.DataFrame({
        "event_index": np.arange(n_events, dtype=int),
        "months_before_snapshot": months,
        "amount": np.round(amounts, 2),
        "event_type": "synthetic_engagement",
        "lineage": "SYNTHETIC",
        "profile": "rfm_distribution",
    })
    logger.debug(
        "synthetic history for %s: %s events over tenure=%s",
        customer_id,
        n_events,
        tenure,
    )
    return history.loc[:, HISTORY_COLUMNS]
