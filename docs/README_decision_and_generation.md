# Decision & Generation — simple guide

This note explains **only** what happens after the churn score is known:
**Decision Agent** then **Generator Agent**.

---

## Big picture

```
Persona already scored (churn_risk_score)
        │
        ▼
   Simulation          ← tests offers (contract, autopay, …)
   (several scenarios)    each with score_before / score_after / cost
        │
        ▼
   Decision            ← picks ONE offer + ONE channel (call OR email)
        │
        ▼
   Generation          ← writes ONE text (call script OR email)
```

The customer profile in the warehouse is **not** changed by simulation clones.
Only the recommendation and the message are stored on the Persona.

---

## 1. Decision Agent

**Role:** choose the best retention offer and how to contact the customer.

**Inputs**
- `churn_risk_score`
- `simulation_scenarios` (from the Simulation Agent)
- optional SHAP `risk_factors` (for the written justification)

**Rules (simple)**

| Situation | Result |
|---|---|
| Score &lt; 0.5 | No action |
| Score ≥ 0.5 | Pick the scenario with the best **delta / cost** |
| Score ≥ 0.7 | Channel = **call** |
| 0.5 ≤ score &lt; 0.7 | Channel = **email** |

- **delta** = how much the churn score drops if we apply the offer  
- **cost** = relative effort of the offer (not euros)

**Output (one package)**
- `recommended_action` → which offer (e.g. `disable_paperless_billing`)
- `contact_channel` → `call` **or** `email` (never both)
- `decision_justification` → short text (score + top SHAP + offer + channel)

Lineage: **DERIVED**.

**Code:** `src/agents/decision_agent/`  
**Run one customer:** `decide_stored_persona("7590-VHVEG")`

---

## 2. Generator Agent

**Role:** write the retention text for the **already chosen** offer and channel.

**Inputs**
- Persona + `recommended_action` + `contact_channel`
- RAG snippets from support tickets (patterns only — **not** the same Telco customer)

**Process**
1. Retrieve a few similar ticket texts (Chroma, or lexical fallback).
2. Build a prompt (Persona + offer + channel + snippets).
3. Call a free LLM if a key is set (Groq / Gemini), otherwise use a template.
4. Produce **either**:
   - a **call script**, or  
   - an **email** (subject + body)

**Output**
- `retention_message` → the text to send / say  
- `rag_context` → snippets used (ticket patterns)

Lineage: message **DERIVED**, RAG snippets **REAL** (ticket corpus).

**Code:** `src/agents/generator_agent/`  
**Details / API keys:** `docs/generator_agent.md`  
**Run one customer:** `generate_stored_persona("7590-VHVEG")`

---

## Call vs email — clear rule

| | |
|---|---|
| **What to offer** | Decision picks **one** simulation action |
| **How to contact** | Decision picks **call** *or* **email** |
| **What to write** | Generator writes **one** text for that channel |

Never: call **and** email for the same decision step.

Example (high risk ≈ 0.80):
- Offer: switch to paper billing  
- Channel: **call**  
- Message: call script only  

---

## Full order for one client

```
Sentiment → Prediction → Simulation → Decision → Generation
```

Skip Generation if Decision returns no action (low risk or no useful scenario).

Quick smoke-test from the project root:

```powershell
.\.venv\Scripts\Activate.ps1
python .\test.py
```

(`test.py` runs prediction → simulation → decision → generation for `7590-VHVEG`.)

---

## Where things live on the Persona

| Field | Agent |
|---|---|
| `churn_risk_score`, `risk_factors` | Prediction |
| `simulation_scenarios` | Simulation |
| `recommended_action`, `contact_channel`, `decision_justification` | Decision |
| `retention_message`, `rag_context` | Generation |

Shared object: `src/persona/schema.py` (never stores the Telco `Churn` label as an operational feature).
