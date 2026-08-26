# Orchestrator (LangGraph)

Coordinates the specialized agents for **one customer**.

## Graph

```
START
  → load_persona
  → sentiment          (skip if already enriched)
  → predict
       ├─ risk < 0.5  → low_risk → persist → END
       └─ risk ≥ 0.5  → simulate → decide
                              ├─ no offer → persist → END
                              └─ generate → persist → END
```

Shared memory = **Persona** (`TwinState` in `src/orchestrator/state.py`).

## Files

| File | Role |
|---|---|
| `state.py` | LangGraph state (`persona`, scenarios, action, message, …) |
| `nodes.py` | Thin wrappers around each agent |
| `router.py` | Conditional edges (risk / decision) |
| `graph.py` | `build_graph()`, `run_for_customer()`, `run_pipeline()` |

## Usage

Warehouse Persona (recommended):

```python
from src.orchestrator.graph import run_for_customer

result = run_for_customer("7590-VHVEG", persist=True)
print(result["status"], result["action"], result["message"])
```

From an in-memory Persona (tests / notebooks):

```python
from src.orchestrator.graph import run_pipeline

result = run_pipeline(persona=persona, persist=False)
```

## Notes

- Does **not** rebuild the Data Agent ETL; it consumes stored Personas.
- Generation uses the free LLM configured in `.env` (Groq/Gemini) or a template fallback.
- Persist writes the updated Persona back to `warehouse.db`.
