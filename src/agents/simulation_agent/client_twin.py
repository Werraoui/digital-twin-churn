"""Classe ClientTwin — jumeau numérique du client (Agent Simulation)."""
from dataclasses import dataclass, replace
from src.persona.schema import Persona


@dataclass
class ClientTwin:
    """Représentation virtuelle et simulable de l'état d'un client."""
    persona: Persona
    simulated_risk_score: float

    def clone(self) -> "ClientTwin":
        """Crée une copie indépendante pour tester une action sans affecter les autres scénarios."""
        return replace(self)
