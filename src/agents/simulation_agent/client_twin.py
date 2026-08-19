"""Classe ClientTwin — jumeau numérique du client (Agent Simulation)."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.persona.schema import Persona


@dataclass
class ClientTwin:
    """Représentation virtuelle et simulable de l'état d'un client."""

    persona: Persona | None
    simulated_risk_score: float
    applied: bool = field(default=False)

    def clone(self) -> "ClientTwin":
        """Copie indépendante (Persona compris) pour un scénario."""
        persona = None
        if self.persona is not None:
            persona = Persona.from_dict(self.persona.to_dict())
        return ClientTwin(
            persona=persona,
            simulated_risk_score=self.simulated_risk_score,
            applied=False,
        )
