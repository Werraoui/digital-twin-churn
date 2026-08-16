from src.agents.decision_agent.rules import select_best_action


def test_select_best_action_returns_none_below_threshold():
    result = select_best_action(risk_score=0.2, scenarios=[])
    assert result is None
