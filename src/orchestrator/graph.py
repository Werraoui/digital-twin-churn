"""Agent Orchestrateur — graphe LangGraph (pattern superviseur centralisé).

Coordonne : Agent Données -> Agent Analyse de Sentiments -> Agent Prédiction
         -> (si risque élevé) Agent Simulation + Agent Générateur -> Agent Décision.

TODO : remplacer ce squelette par un vrai graphe LangGraph (create_supervisor ou StateGraph),
       une fois chaque agent individuellement testé (voir tests/).
"""
from src.agents.data_agent.persona_builder import build_initial_persona
from src.agents.sentiment_agent.sentiment_model import analyze
from src.agents.sentiment_agent.persona_updater import update_persona
from src.agents.prediction_agent.predict import predict_churn
from src.agents.simulation_agent.client_twin import ClientTwin
from src.agents.simulation_agent.scenario_runner import run_scenarios
from src.agents.generator_agent.message_generator import generate_retention_message
from src.agents.decision_agent.rules import select_best_action
from src.agents.decision_agent.justify import build_justification


def run_pipeline(telco_client, behavioral_history, review_text) -> dict:
    """Exécute le pipeline complet pour un client, orchestré étape par étape.

    Retourne un dict prêt à être affiché par l'Interface (score, scénarios, recommandation).
    """
    persona = build_initial_persona(telco_client, behavioral_history, review_text)
    persona = update_persona(persona, analyze(persona))

    risk_score = predict_churn(persona)
    persona.churn_risk_score = risk_score

    if risk_score < 0.5:
        return {"persona": persona, "action": None, "message": "Aucune action nécessaire."}

    twin = ClientTwin(persona=persona, simulated_risk_score=risk_score)
    scenarios = run_scenarios(twin)
    chosen = select_best_action(risk_score, scenarios)
    message = generate_retention_message(persona, chosen["action"])
    justification = build_justification(risk_score, persona.risk_factors, chosen)

    return {
        "persona": persona,
        "scenarios": scenarios,
        "action": chosen,
        "message": message,
        "justification": justification,
    }
