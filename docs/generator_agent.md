# Generator Agent (RAG)

Retention messages are grounded on:
1. the **Persona** (Decision output: action + channel),
2. **retrieved ticket patterns** (not the same customer — no Telco join).

## Flow

```
recommended_action + contact_channel
    → retrieve top-k ticket snippets (Chroma or lexical fallback)
    → free LLM (Groq / Gemini) or template fallback
    → persona.retention_message (DERIVED)
    → persona.rag_context (REAL ticket text patterns)
```

## Free LLM (recommended)

| Provider | Env var | Free key |
|---|---|---|
| **Groq** (default if key set) | `GROQ_API_KEY` | https://console.groq.com |
| **Gemini** | `GEMINI_API_KEY` | https://aistudio.google.com/apikey |
| Anthropic (optional) | `ANTHROPIC_API_KEY` | paid |
| Template (no API) | — | always works |

In `.env`:

```env
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...
# optional override:
# LLM_MODEL=llama-3.1-8b-instant
```

Or Gemini:

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=...
```

Auto-detect order if `LLM_PROVIDER` is empty: Groq → Gemini → Anthropic → template.

## Corpus

`customer_support_tickets_200k.csv` has only **~10 unique** `issue_description` values.
`build_ticket_documents()` indexes **one document per unique issue**.

Never maps ticket emails/names onto Telco `customerID`.

## Usage

```python
from src.agents.generator_agent.run import generate_stored_persona

persona, message = generate_stored_persona("7590-VHVEG")  # uses free LLM if key set
# persona, message = generate_stored_persona("7590-VHVEG", use_llm=False)  # template only
print(message)
```
