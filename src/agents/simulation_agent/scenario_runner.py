"""Comparaison de plusieurs scénarios d'action pour un client (Agent Simulation)."""
from src.agents.simulation_agent.client_twin import ClientTwin
from src.agents.simulation_agent.rules_engine import ACTIONS, apply_action


def run_scenarios(twin: ClientTwin) -> list[dict]:
    """Teste toutes les actions possibles et retourne un comparatif (action, score avant/après, coût)."""
    results = []
    for action in ACTIONS:
        simulated = apply_action(twin.clone(), action)
        results.append({
            "action": action,
            "score_before": twin.simulated_risk_score,
            "score_after": simulated.simulated_risk_score,
        })
    return results
