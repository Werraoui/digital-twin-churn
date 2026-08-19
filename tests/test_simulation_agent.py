import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.agents.data_agent.persona_builder import build_initial_persona
from src.agents.prediction_agent.features import FEATURE_COLUMNS
from src.agents.sentiment_agent.persona_updater import update_persona as apply_sentiment
from src.agents.simulation_agent.client_twin import ClientTwin
from src.agents.simulation_agent.rules_engine import ACTIONS, apply_action
from src.agents.simulation_agent.scenario_runner import run_scenarios


def _telco(**overrides):
    row = {
        "customerID": "7590-VHVEG",
        "gender": "Female",
        "SeniorCitizen": 0,
        "Partner": "Yes",
        "Dependents": "No",
        "tenure": 1,
        "PhoneService": "No",
        "MultipleLines": "No phone service",
        "InternetService": "DSL",
        "OnlineSecurity": "No",
        "OnlineBackup": "Yes",
        "DeviceProtection": "No",
        "TechSupport": "No",
        "StreamingTV": "No",
        "StreamingMovies": "No",
        "Contract": "Month-to-month",
        "PaperlessBilling": "Yes",
        "PaymentMethod": "Electronic check",
        "MonthlyCharges": 29.85,
        "TotalCharges": 29.85,
        "Churn": "No",
    }
    row.update(overrides)
    return pd.Series(row)


def _enriched_persona(**telco_overrides):
    persona = build_initial_persona(_telco(**telco_overrides), [], "billing issue")
    return apply_sentiment(
        persona,
        {
            "sentiment": "neutral",
            "confidence": 0.74,
            "emotions": ["calm"],
            "complaint_topics": ["Payment Problem"],
            "satisfaction_score": 3.0,
        },
    )


def _dummy_model():
    X = pd.DataFrame(0, index=range(40), columns=FEATURE_COLUMNS)
    X["Contract_Two year"] = [1 if i % 2 == 0 else 0 for i in range(40)]
    y = pd.Series([0 if i % 2 == 0 else 1 for i in range(40)])
    model = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=200)),
        ]
    )
    model.fit(X, y)
    return model


def test_client_twin_clone_is_independent():
    persona = _enriched_persona()
    twin = ClientTwin(persona=persona, simulated_risk_score=0.8)
    clone = twin.clone()
    clone.simulated_risk_score = 0.5
    clone.persona.contract["type"] = "Two year"
    assert twin.simulated_risk_score == 0.8
    assert twin.persona.contract["type"] == "Month-to-month"


def test_unknown_action_raises():
    twin = ClientTwin(persona=_enriched_persona(), simulated_risk_score=0.8)
    with pytest.raises(ValueError, match="unknown action"):
        apply_action(twin, "discount_10", model=_dummy_model())


def test_two_year_contract_applies_on_month_to_month():
    twin = ClientTwin(persona=_enriched_persona(), simulated_risk_score=0.8)
    simulated = apply_action(twin, "offer_two_year_contract", model=_dummy_model())
    assert simulated.applied is True
    assert simulated.persona.contract["type"] == "Two year"
    assert twin.persona.contract["type"] == "Month-to-month"
    assert simulated.persona.lineage["simulation_action"] == "SYNTHETIC"
    assert "Churn" not in simulated.persona.to_dict()


def test_two_year_contract_is_noop_if_already_two_year():
    twin = ClientTwin(
        persona=_enriched_persona(Contract="Two year"),
        simulated_risk_score=0.22,
    )
    simulated = apply_action(twin, "offer_two_year_contract", model=_dummy_model())
    assert simulated.applied is False
    assert simulated.simulated_risk_score == 0.22
    assert simulated.persona.contract["type"] == "Two year"


def test_one_year_only_from_month_to_month():
    already = apply_action(
        ClientTwin(persona=_enriched_persona(Contract="One year"), simulated_risk_score=0.4),
        "offer_one_year_contract",
        model=_dummy_model(),
    )
    assert already.applied is False

    moved = apply_action(
        ClientTwin(persona=_enriched_persona(), simulated_risk_score=0.8),
        "offer_one_year_contract",
        model=_dummy_model(),
    )
    assert moved.applied is True
    assert moved.persona.contract["type"] == "One year"


def test_online_security_requires_internet_and_absence():
    no_net = apply_action(
        ClientTwin(
            persona=_enriched_persona(
                InternetService="No",
                OnlineSecurity="No internet service",
                OnlineBackup="No internet service",
                DeviceProtection="No internet service",
                TechSupport="No internet service",
                StreamingTV="No internet service",
                StreamingMovies="No internet service",
            ),
            simulated_risk_score=0.5,
        ),
        "add_online_security",
        model=_dummy_model(),
    )
    assert no_net.applied is False

    added = apply_action(
        ClientTwin(persona=_enriched_persona(), simulated_risk_score=0.8),
        "add_online_security",
        model=_dummy_model(),
    )
    assert added.applied is True
    assert added.persona.services["online_security"] == "Yes"


def test_autopay_and_paperless_guards():
    model = _dummy_model()
    switched = apply_action(
        ClientTwin(persona=_enriched_persona(), simulated_risk_score=0.8),
        "switch_to_autopay",
        model=model,
    )
    assert switched.applied is True
    assert switched.persona.contract["payment_method"] == "Credit card (automatic)"

    already_auto = apply_action(
        ClientTwin(
            persona=_enriched_persona(PaymentMethod="Bank transfer (automatic)"),
            simulated_risk_score=0.4,
        ),
        "switch_to_autopay",
        model=model,
    )
    assert already_auto.applied is False

    paper = apply_action(
        ClientTwin(persona=_enriched_persona(), simulated_risk_score=0.8),
        "disable_paperless_billing",
        model=model,
    )
    assert paper.applied is True
    assert paper.persona.contract["paperless_billing"] == "No"


def test_run_scenarios_covers_all_shap_actions():
    twin = ClientTwin(persona=_enriched_persona(), simulated_risk_score=0.8)
    results = run_scenarios(twin, model=_dummy_model(), include_skipped=True)
    assert [row["action"] for row in results] == list(ACTIONS)
    applied = {row["action"]: row["applied"] for row in results}
    assert applied["offer_two_year_contract"] is True
    assert applied["offer_one_year_contract"] is True
    assert applied["add_online_security"] is True
    assert applied["switch_to_autopay"] is True
    assert applied["disable_paperless_billing"] is True
    assert twin.persona.contract["type"] == "Month-to-month"
    two_year = next(row for row in results if row["action"] == "offer_two_year_contract")
    assert two_year["cost"] == 3.0
    assert "delta_per_cost" in two_year


def test_run_scenarios_drops_inapplicable_actions():
    twin = ClientTwin(
        persona=_enriched_persona(Contract="Two year", PaymentMethod="Bank transfer (automatic)"),
        simulated_risk_score=0.3,
    )
    results = run_scenarios(twin, model=_dummy_model())
    actions = [row["action"] for row in results]
    assert "offer_two_year_contract" not in actions
    assert "offer_one_year_contract" not in actions
    assert "switch_to_autopay" not in actions
    assert all(row["applied"] for row in results)


def test_simulate_stored_persona_persists_scenarios_not_mutated_profile():
    from sqlalchemy import create_engine

    from src.agents.data_agent.repository import get_persona, replace_personas
    from src.agents.data_agent.warehouse import init_db
    from src.agents.simulation_agent.run import simulate_stored_persona

    persona = _enriched_persona()
    persona.churn_risk_score = 0.8
    engine = create_engine("sqlite:///:memory:", future=True)
    init_db(engine)
    replace_personas([persona], engine=engine)

    scored, scenarios = simulate_stored_persona(
        "7590-VHVEG", engine=engine, model=_dummy_model()
    )
    reloaded = get_persona("7590-VHVEG", engine=engine)
    assert scenarios
    assert all(row["applied"] for row in scenarios)
    assert reloaded.simulation_scenarios == scored.simulation_scenarios
    assert reloaded.contract["type"] == "Month-to-month"
    assert reloaded.lineage["simulation_scenarios"] == "SYNTHETIC"
    assert "Churn" not in reloaded.to_dict()


def test_simulate_stored_persona_skips_below_threshold():
    from sqlalchemy import create_engine

    from src.agents.data_agent.repository import replace_personas
    from src.agents.data_agent.warehouse import init_db
    from src.agents.simulation_agent.run import simulate_stored_persona

    persona = _enriched_persona()
    persona.churn_risk_score = 0.2
    engine = create_engine("sqlite:///:memory:", future=True)
    init_db(engine)
    replace_personas([persona], engine=engine)
    _, scenarios = simulate_stored_persona(
        "7590-VHVEG", engine=engine, model=_dummy_model()
    )
    assert scenarios == []
