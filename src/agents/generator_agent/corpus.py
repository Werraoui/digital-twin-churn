"""Build the RAG corpus from support tickets (patterns only, no Telco join)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from config.settings import TICKETS_RAW_PATH

# Human-readable labels for Decision Agent action ids.
ACTION_LABELS = {
    "offer_two_year_contract": "offer a two-year contract commitment",
    "offer_one_year_contract": "offer a one-year contract commitment",
    "add_online_security": "add the Online Security option",
    "switch_to_autopay": "switch payment to automatic credit-card billing",
    "disable_paperless_billing": "switch to paper billing statements",
}


def _stable_id(text: str) -> str:
    return "issue-" + hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def build_ticket_documents(
    tickets: pd.DataFrame | None = None,
    *,
    path: str | Path | None = None,
    max_rows: int | None = 50_000,
) -> list[dict]:
    """
    One document per unique issue_description (the file only has ~10 canned texts).

    Never maps ticket customer_email / names onto Telco customerID.
    """
    if tickets is None:
        source = Path(path or TICKETS_RAW_PATH)
        usecols = ["ticket_id", "category", "issue_description", "resolution_notes"]
        tickets = pd.read_csv(source, usecols=usecols, nrows=max_rows)

    required = {"ticket_id", "category", "issue_description", "resolution_notes"}
    missing = required - set(tickets.columns)
    if missing:
        raise ValueError(f"tickets missing columns: {sorted(missing)}")

    frame = tickets.dropna(subset=["issue_description"]).copy()
    frame["issue_description"] = frame["issue_description"].astype(str).str.strip()
    frame = frame[frame["issue_description"] != ""]
    unique = frame.drop_duplicates(subset=["issue_description"], keep="first")

    documents = []
    for _, row in unique.iterrows():
        issue = str(row["issue_description"]).strip()
        resolution = str(row.get("resolution_notes") or "").strip()
        category = str(row.get("category") or "").strip()
        text = (
            f"Category: {category}\n"
            f"Customer issue: {issue}\n"
            f"Resolution note: {resolution}"
        )
        documents.append(
            {
                "id": _stable_id(issue),
                "text": text,
                "metadata": {
                    "category": category,
                    "issue_description": issue,
                    "ticket_id": str(row["ticket_id"]),
                    "lineage": "REAL",
                },
            }
        )
    return documents
