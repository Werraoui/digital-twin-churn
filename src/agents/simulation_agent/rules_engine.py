"""Moteur de règles : effet estimé de chaque action de rétention sur un ClientTwin."""
from src.agents.simulation_agent.client_twin import ClientTwin

ACTIONS = ["discount_10", "phone_call", "discount_5_plus_call", "email_only"]


def apply_action(twin: ClientTwin, action: str) -> ClientTwin:
    """Applique une action à une copie du jumeau numérique et retourne le nouvel état simulé.

    TODO : définir l'effet de chaque action selon le niveau de risque initial et l'historique
    (voir docs/architecture.md section Agent Simulation pour la logique attendue).
    """
    raise NotImplementedError
