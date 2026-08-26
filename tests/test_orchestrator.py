"""Tests for the LangGraph orchestrator (agents mocked)."""

from __future__ import annotations

from unittest.mock import patch

from src.orchestrator.graph import build_graph, run_pipeline
from src.orchestrator.router import (
    route_after_decide,
    route_after_predict,
    route_after_sentiment,
)
from src.persona.schema import Persona


def _persona(**overrides) -> Persona:
    data = {
        "customer_id": "7590-VHVEG",
        "demographics": {},
        "services": {"internet_service": "DSL", "online_security": "No"},
        "contract": {
            "type": "Month-to-month",
            "payment_method": "Electronic check",
            "paperless_billing": "Yes",
            "tenure": 1,
        },
        "billing": {"monthly_charges": 29.85, "total_charges": 29.85},
        "raw_review_text": "payment failed",
        "sentiment": "negative",
        "sentiment_confidence": 0.9,
        "emotions": ["frustration"],
        "complaint_topics": ["Payment Problem"],
    }
    data.update(overrides)
    return Persona(**data)


def test_build_graph_has_expected_nodes():
    app = build_graph()
    # Compiled graph exposes nodes via get_graph_dict / nodes depending on version
    spec = app.get_graph()
    names = set(spec.nodes.keys())
    for required in {
        "load_persona",
        "sentiment",
        "predict",
        "simulate",
        "decide",
        "generate",
        "persist",
        "low_risk",
    }:
        assert required in names


def test_route_after_predict_branches():
    low = {"persona": _persona(churn_risk_score=0.2)}
    high = {"persona": _persona(churn_risk_score=0.8)}
    assert route_after_predict(low) == "end_low_risk"
    assert route_after_predict(high) == "simulate"


def test_route_after_decide_branches():
    assert route_after_decide({"action": None}) == "end_no_action"
    assert route_after_decide({"action": {"action": "x"}}) == "generate"


def test_route_after_sentiment_requires_enrichment():
    assert route_after_sentiment({"persona": _persona(sentiment=None)}) == "end_low_risk"
    assert route_after_sentiment({"persona": _persona()}) == "predict"


def test_run_pipeline_high_risk_path():
    persona = _persona()
    scored = _persona(churn_risk_score=0.82, risk_factors=[{"feature": "tenure"}])
    simulated = _persona(
        churn_risk_score=0.82,
        simulation_scenarios=[
            {
                "action": "disable_paperless_billing",
                "applied": True,
                "delta": 0.06,
                "cost": 0.3,
                "delta_per_cost": 0.2,
            }
        ],
    )
    decided = _persona(
        churn_risk_score=0.82,
        recommended_action={
            "action": "disable_paperless_billing",
            "channel": "call",
            "delta": 0.06,
            "cost": 0.3,
        },
        contact_channel="call",
        decision_justification="test justification",
        simulation_scenarios=simulated.simulation_scenarios,
    )
    generated = _persona(
        churn_risk_score=0.82,
        recommended_action=decided.recommended_action,
        contact_channel="call",
        decision_justification="test justification",
        retention_message="CALL SCRIPT\nHello",
        rag_context=["snippet"],
    )

    with (
        patch("src.orchestrator.nodes.apply_prediction", return_value=scored),
        patch(
            "src.orchestrator.nodes.simulate_persona",
            return_value=(simulated, simulated.simulation_scenarios),
        ),
        patch(
            "src.orchestrator.nodes.decide_for_persona",
            return_value=(decided, decided.recommended_action),
        ),
        patch(
            "src.orchestrator.nodes.generate_for_persona",
            return_value=(generated, generated.retention_message),
        ),
        patch("src.orchestrator.nodes.save_persona"),
    ):
        result = run_pipeline(persona=persona, persist=False)

    assert result["status"] == "generated"
    assert result["action"]["action"] == "disable_paperless_billing"
    assert result["message"].startswith("CALL SCRIPT")
    assert result["justification"] == "test justification"


def test_run_pipeline_low_risk_stops_before_simulation():
    persona = _persona()
    scored = _persona(churn_risk_score=0.2)

    with (
        patch("src.orchestrator.nodes.apply_prediction", return_value=scored) as predict,
        patch("src.orchestrator.nodes.simulate_persona") as simulate,
        patch("src.orchestrator.nodes.save_persona"),
    ):
        result = run_pipeline(persona=persona, persist=False)

    predict.assert_called_once()
    simulate.assert_not_called()
    assert result["status"] == "low_risk"
    assert result["action"] is None
    assert "Aucune action" in result["message"]
