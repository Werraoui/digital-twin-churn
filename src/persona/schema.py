"""Customer Persona — shared memory between Architecture B agents."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from typing import Any, Optional

import pandas as pd


def _json_safe(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    return str(value)


@dataclass
class Persona:
    customer_id: str
    demographics: dict
    services: dict
    contract: dict
    billing: dict
    behavioral_history: list = field(default_factory=list)
    raw_review_text: Optional[str] = None
    review_tone: Optional[str] = None
    lineage: dict = field(default_factory=dict)

    sentiment: Optional[str] = None
    sentiment_confidence: Optional[float] = None
    emotions: list = field(default_factory=list)
    complaint_topics: list = field(default_factory=list)
    satisfaction_score: Optional[float] = None

    churn_risk_score: Optional[float] = None
    risk_factors: list = field(default_factory=list)
    simulation_scenarios: list = field(default_factory=list)

    recommended_action: Optional[dict] = None
    decision_justification: Optional[str] = None
    contact_channel: Optional[str] = None

    retention_message: Optional[str] = None
    rag_context: list = field(default_factory=list)

    def is_enriched(self) -> bool:
        return self.sentiment is not None

    def is_scored(self) -> bool:
        return self.churn_risk_score is not None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("Churn", None)
        payload.pop("churn", None)
        return json.loads(json.dumps(payload, default=_json_safe))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Persona":
        allowed = {item.name for item in fields(cls)}
        cleaned = {key: value for key, value in data.items() if key in allowed}
        cleaned.pop("Churn", None)
        cleaned.pop("churn", None)
        if isinstance(cleaned.get("behavioral_history"), pd.DataFrame):
            cleaned["behavioral_history"] = cleaned["behavioral_history"].to_dict(orient="records")
        return cls(**cleaned)
