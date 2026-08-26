"""Shared LangGraph state for the multi-agent orchestrator."""

from __future__ import annotations

from typing import Any, Optional, TypedDict

from src.persona.schema import Persona


class TwinState(TypedDict, total=False):
    """State that circulates between orchestrator nodes."""

    customer_id: str
    persona: Persona
    scenarios: list[dict]
    action: Optional[dict]
    message: Optional[str]
    justification: Optional[str]
    status: str
    error: Optional[str]
    persist: bool
    # Optional raw inputs when building a Persona from scratch (not warehouse).
    telco_client: Any
    behavioral_history: Any
    review_text: Optional[str]
    review_tone: Optional[str]
