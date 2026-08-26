"""Agent Orchestrateur — LangGraph StateGraph (central supervisor).

Flow:
  load_persona → sentiment → predict
       ├─ (risk < 0.5) → low_risk → persist → END
       └─ simulate → decide
              ├─ (no action) → persist → END
              └─ generate → persist → END
"""

from __future__ import annotations

from typing import Any, Optional

from langgraph.graph import END, START, StateGraph

from src.orchestrator import nodes
from src.orchestrator.router import (
    route_after_decide,
    route_after_predict,
    route_after_sentiment,
)
from src.orchestrator.state import TwinState
from src.persona.schema import Persona

_compiled = None


def build_graph():
    """Compile the multi-agent retention graph."""
    graph = StateGraph(TwinState)

    graph.add_node("load_persona", nodes.load_persona_node)
    graph.add_node("sentiment", nodes.sentiment_node)
    graph.add_node("predict", nodes.predict_node)
    graph.add_node("low_risk", nodes.low_risk_node)
    graph.add_node("simulate", nodes.simulate_node)
    graph.add_node("decide", nodes.decide_node)
    graph.add_node("generate", nodes.generate_node)
    graph.add_node("persist", nodes.persist_node)

    graph.add_edge(START, "load_persona")
    graph.add_edge("load_persona", "sentiment")
    graph.add_conditional_edges(
        "sentiment",
        route_after_sentiment,
        {
            "predict": "predict",
            "end_low_risk": "low_risk",
        },
    )
    graph.add_conditional_edges(
        "predict",
        route_after_predict,
        {
            "simulate": "simulate",
            "end_low_risk": "low_risk",
        },
    )
    graph.add_edge("low_risk", "persist")
    graph.add_edge("simulate", "decide")
    graph.add_conditional_edges(
        "decide",
        route_after_decide,
        {
            "generate": "generate",
            "end_no_action": "persist",
        },
    )
    graph.add_edge("generate", "persist")
    graph.add_edge("persist", END)

    return graph.compile()


def get_graph():
    global _compiled
    if _compiled is None:
        _compiled = build_graph()
    return _compiled


def _result_from_state(state: TwinState) -> dict:
    return {
        "persona": state.get("persona"),
        "scenarios": state.get("scenarios") or [],
        "action": state.get("action"),
        "message": state.get("message"),
        "justification": state.get("justification"),
        "status": state.get("status"),
    }


def run_for_customer(
    customer_id: str,
    *,
    persist: bool = True,
    graph=None,
) -> dict:
    """Run the full pipeline for a Persona already stored in the warehouse."""
    app = graph or get_graph()
    final = app.invoke(
        {
            "customer_id": customer_id,
            "persist": persist,
            "scenarios": [],
            "action": None,
            "message": None,
            "justification": None,
            "status": "started",
        }
    )
    return _result_from_state(final)


def run_pipeline(
    telco_client=None,
    behavioral_history=None,
    review_text: str | None = None,
    *,
    review_tone: str | None = None,
    persona: Persona | None = None,
    customer_id: str | None = None,
    persist: bool = False,
    graph=None,
) -> dict:
    """
    Execute the orchestrated pipeline.

    Preferred operational entry: customer_id (warehouse) or persona.
    Legacy entry: telco_client + behavioral_history + review_text.
    """
    app = graph or get_graph()
    initial: TwinState = {
        "persist": persist,
        "scenarios": [],
        "action": None,
        "message": None,
        "justification": None,
        "status": "started",
    }
    if persona is not None:
        initial["persona"] = persona
        initial["customer_id"] = persona.customer_id
    elif customer_id:
        initial["customer_id"] = customer_id
        initial["persist"] = persist if persist is not None else True
    else:
        initial["telco_client"] = telco_client
        initial["behavioral_history"] = behavioral_history or []
        initial["review_text"] = review_text
        initial["review_tone"] = review_tone

    final = app.invoke(initial)
    return _result_from_state(final)
