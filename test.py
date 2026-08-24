"""Smoke-test Generator Agent for one warehouse Persona.

Order required:
  Prediction → Simulation → Decision → Generation
"""

from src.agents.data_agent.repository import get_persona, save_persona
from src.agents.decision_agent.run import decide_for_persona
from src.agents.generator_agent.run import generate_for_persona
from src.agents.prediction_agent.predict import apply_prediction
from src.agents.simulation_agent.run import simulate_persona

CUSTOMER_ID = "7590-VHVEG"

persona = get_persona(CUSTOMER_ID)
print("loaded", persona.customer_id, "sentiment=", persona.sentiment)

if not persona.is_enriched():
    raise SystemExit("Persona has no sentiment. Run enrich_all_personas() first.")

# 1) Prediction
if persona.churn_risk_score is None:
    persona = apply_prediction(persona)
    print("predicted risk=", round(persona.churn_risk_score, 4))
else:
    print("already scored risk=", round(persona.churn_risk_score, 4))

# 2) Simulation (what-if scenarios)
if not persona.simulation_scenarios and persona.churn_risk_score >= 0.5:
    persona, scenarios = simulate_persona(persona)
    print("scenarios=", len(scenarios))
elif persona.simulation_scenarios:
    print("scenarios already=", len(persona.simulation_scenarios))
else:
    print("risk below 0.5 — no simulation needed")

# 3) Decision
if persona.recommended_action is None:
    persona, chosen = decide_for_persona(persona)
    print("chosen=", chosen)
else:
    print("already decided=", persona.recommended_action)

if persona.recommended_action is None:
    save_persona(persona)
    raise SystemExit("No applicable action — nothing to generate.")

# 4) Generation (Groq/Gemini if key in .env, else template)
persona, message = generate_for_persona(persona)
save_persona(persona)

print("\n--- retention message ---\n")
print(message)
print("\nprovider lineage:", persona.lineage.get("retention_message"))
"""After Simulation, the Decision Agent picks:

One retention offer (ex. disable_paperless_billing, offer_two_year_contract, …)
One contact channel to deliver that offer:
call if churn_risk_score ≥ 0.7
email if 0.5 ≤ score < 0.7
So for 7590-VHVEG (risk ≈ 0.80):
offer = paper billing + channel = call only.

The Generator then writes either:

a CALL SCRIPT, or
an EMAIL (subject + body)
…depending on contact_channel. Not both.

Mental model
Layer	What
Simulation
What to offer (contract, autopay, …)
Decision
Which offer + how to contact (call or email)
Generator
The text for that single channel
Call vs email is the delivery mode, not a second retention action."""