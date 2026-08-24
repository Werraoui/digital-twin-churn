from sqlalchemy import create_engine

from src.agents.data_agent.repository import get_persona, replace_personas
from src.agents.data_agent.warehouse import init_db
from src.agents.decision_agent.justify import build_justification
from src.agents.decision_agent.rules import choose_contact_channel, select_best_action
from src.agents.decision_agent.run import decide_for_persona, decide_stored_persona
from src.persona.schema import Persona


def _scenarios():
    return [
        {
            "action": "offer_two_year_contract",
            "applied": True,
            "score_before": 0.80,
            "score_after": 0.46,
            "delta": 0.34,
            "cost": 3.0,
            "delta_per_cost": 0.34 / 3.0,
        },
        {
            "action": "switch_to_autopay",
            "applied": True,
            "score_before": 0.80,
            "score_after": 0.74,
            "delta": 0.06,
            "cost": 0.5,
            "delta_per_cost": 0.06 / 0.5,
        },
        {
            "action": "disable_paperless_billing",
            "applied": True,
            "score_before": 0.80,
            "score_after": 0.74,
            "delta": 0.06,
            "cost": 0.3,
            "delta_per_cost": 0.06 / 0.3,
        },
        {
            "action": "offer_one_year_contract",
            "applied": False,
            "score_before": 0.80,
            "score_after": 0.80,
            "delta": 0.0,
            "cost": 2.0,
            "delta_per_cost": 0.0,
        },
    ]


def _persona(**overrides):
    data = {
        "customer_id": "7590-VHVEG",
        "demographics": {},
        "services": {},
        "contract": {},
        "billing": {},
        "churn_risk_score": 0.80,
        "risk_factors": [
            {
                "feature": "tenure",
                "shap_value": 1.2,
                "direction": "increases_risk",
            },
            {
                "feature": "Contract_Two year",
                "shap_value": -0.5,
                "direction": "decreases_risk",
            },
        ],
        "simulation_scenarios": _scenarios(),
    }
    data.update(overrides)
    return Persona(**data)


def test_select_best_action_returns_none_below_threshold():
    result = select_best_action(risk_score=0.2, scenarios=_scenarios())
    assert result is None


def test_select_best_action_picks_best_delta_per_cost():
    # paperless: 0.06/0.3 = 0.20 ; autopay: 0.12 ; two-year: ~0.113
    chosen = select_best_action(0.80, _scenarios())
    assert chosen is not None
    assert chosen["action"] == "disable_paperless_billing"
    assert chosen["channel"] == "call"
    assert "offer_one_year_contract" != chosen["action"]


def test_select_best_action_returns_none_when_no_positive_delta():
    scenarios = [
        {
            "action": "add_online_security",
            "applied": True,
            "delta": 0.0,
            "cost": 1.5,
            "delta_per_cost": 0.0,
        }
    ]
    assert select_best_action(0.80, scenarios) is None
    assert select_best_action(0.80, []) is None


def test_choose_contact_channel():
    assert choose_contact_channel(0.55) == "email"
    assert choose_contact_channel(0.70) == "call"
    assert choose_contact_channel(0.90) == "call"


def test_build_justification_with_shap_dicts():
    chosen = select_best_action(0.80, _scenarios())
    text = build_justification(0.80, _persona().risk_factors, chosen)
    assert "0.80" in text
    assert "tenure" in text
    assert "disable_paperless_billing" in text
    assert "call" in text


def test_build_justification_when_no_action():
    text = build_justification(0.2, [], None)
    assert "aucune action" in text.lower()


def test_decide_for_persona_writes_derived_fields():
    persona, chosen = decide_for_persona(_persona())
    assert chosen["action"] == "disable_paperless_billing"
    assert persona.recommended_action["action"] == "disable_paperless_billing"
    assert persona.contact_channel == "call"
    assert persona.decision_justification
    assert persona.lineage["recommended_action"] == "DERIVED"
    assert "Churn" not in persona.to_dict()


def test_decide_stored_persona_persists():
    engine = create_engine("sqlite:///:memory:", future=True)
    init_db(engine)
    replace_personas([_persona()], engine=engine)
    decided, chosen = decide_stored_persona("7590-VHVEG", engine=engine)
    reloaded = get_persona("7590-VHVEG", engine=engine)
    assert chosen["action"] == decided.recommended_action["action"]
    assert reloaded.recommended_action["action"] == "disable_paperless_billing"
    assert reloaded.lineage["decision_justification"] == "DERIVED"
