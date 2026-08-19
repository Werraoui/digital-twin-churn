"""Règles de rétention alignées sur le beeswarm SHAP de la logreg.

On ne change que des champs Persona qui existent dans le vecteur ML.
Le nouveau score est recalculé par le même modèle (pas un delta magique).

Inclus (signe beeswarm clair + levier métier tenable) :
- contrat 1 an / 2 ans  → baisse le churn
- Online Security Yes   → baisse le churn
- quitter Electronic check → baisse le churn
- PaperlessBilling Yes  → augmente le churn, donc le désactiver le baisse

Exclus volontairement :
- tenure / TotalCharges : pas un levier campagne
- MonthlyCharges : dans CE modèle, une facture élevée baisse le churn (colinéarité)
- Fiber optic / Streaming / MultipleLines : les couper baisserait le score mais c'est un downsell
"""

from __future__ import annotations

from pathlib import Path

from src.agents.prediction_agent.predict import apply_prediction
from src.agents.simulation_agent.client_twin import ClientTwin
from src.persona.schema import Persona

ACTIONS = (
    "offer_two_year_contract",
    "offer_one_year_contract",
    "add_online_security",
    "switch_to_autopay",
    "disable_paperless_billing",
)

# Coûts relatifs (unité arbitraire) pour le rapport delta/coût de l'Agent Décision.
ACTION_COSTS = {
    "offer_two_year_contract": 3.0,
    "offer_one_year_contract": 2.0,
    "add_online_security": 1.5,
    "switch_to_autopay": 0.5,
    "disable_paperless_billing": 0.3,
}

AUTOPAY_METHOD = "Credit card (automatic)"


def _has_internet(persona: Persona) -> bool:
    return str((persona.services or {}).get("internet_service", "")).strip() not in {"", "No"}


def _offer_two_year_contract(persona: Persona) -> bool:
    if str(persona.contract.get("type")) == "Two year":
        return False
    persona.contract["type"] = "Two year"
    return True


def _offer_one_year_contract(persona: Persona) -> bool:
    if str(persona.contract.get("type")) != "Month-to-month":
        return False
    persona.contract["type"] = "One year"
    return True


def _add_online_security(persona: Persona) -> bool:
    current = str(persona.services.get("online_security", ""))
    if not _has_internet(persona) or current == "Yes":
        return False
    persona.services["online_security"] = "Yes"
    return True


def _switch_to_autopay(persona: Persona) -> bool:
    current = str(persona.contract.get("payment_method", ""))
    if current != "Electronic check":
        return False
    persona.contract["payment_method"] = AUTOPAY_METHOD
    return True


def _disable_paperless_billing(persona: Persona) -> bool:
    current = str(persona.contract.get("paperless_billing", ""))
    if current != "Yes":
        return False
    persona.contract["paperless_billing"] = "No"
    return True


_MUTATORS = {
    "offer_two_year_contract": _offer_two_year_contract,
    "offer_one_year_contract": _offer_one_year_contract,
    "add_online_security": _add_online_security,
    "switch_to_autopay": _switch_to_autopay,
    "disable_paperless_billing": _disable_paperless_billing,
}


def apply_action(
    twin: ClientTwin,
    action: str,
    *,
    model=None,
    models_dir: str | Path | None = None,
) -> ClientTwin:
    """Clone the twin, apply one SHAP-aligned rule, rescore churn. Never uses Churn."""
    if action not in _MUTATORS:
        raise ValueError(f"unknown action {action!r}; expected one of {ACTIONS}")

    simulated = twin.clone()
    persona = simulated.persona
    if persona is None:
        raise ValueError("ClientTwin.persona is required")

    applied = _MUTATORS[action](persona)
    lineage = dict(persona.lineage or {})
    lineage["simulation_action"] = "SYNTHETIC"
    persona.lineage = lineage

    if not applied:
        simulated.simulated_risk_score = float(twin.simulated_risk_score)
        simulated.applied = False
        return simulated

    scored = apply_prediction(
        persona,
        model=model,
        models_dir=models_dir,
        explain=False,
    )
    simulated.persona = scored
    simulated.simulated_risk_score = float(scored.churn_risk_score)
    simulated.applied = True
    return simulated
