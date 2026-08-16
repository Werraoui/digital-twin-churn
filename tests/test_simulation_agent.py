from src.agents.simulation_agent.client_twin import ClientTwin


def test_client_twin_clone_is_independent():
    twin = ClientTwin(persona=None, simulated_risk_score=0.8)
    clone = twin.clone()
    clone.simulated_risk_score = 0.5
    assert twin.simulated_risk_score == 0.8
