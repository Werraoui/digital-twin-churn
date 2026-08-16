# Data Agent — components, role, and how it was built

This document describes the **Data Agent** (Agent Données) of Architecture B: a LangGraph orchestrator plus six specialized agents, with the **Persona** as shared memory.

The Data Agent is the first agent. It does **not** predict churn, run sentiment, or generate retention messages. It builds the **initial Persona** from raw data, stores it, and serves it to the other agents.

---

## 1. Place in the system

```
Raw CSV / Excel
    → Data Agent
    → initial Persona
    → Sentiment Agent        (enrich Persona)
    → Prediction Agent       (churn score)
    → Simulation + Generator (if risk is high)
    → Decision Agent
```

**Inputs:** three independent datasets (no shared customer ID).  
**Output:** a Persona per Telco customer, plus a SQLite warehouse other agents can query.

| Source | File | Role |
|---|---|---|
| Telco Customer Churn | `data/raw/telco_churn.csv` | Real customer base (7,043 rows). `Churn` is a **training label only**. |
| Online Retail II | `data/raw/online_retail_II.xlsx` (both years) or `.csv` | Behavioral patterns (RFM). Different people. |
| Support tickets | `data/raw/customer_support_tickets_200k.csv` | Text/category patterns for synthetic reviews. Different people. |

**Hard rules**

- Never row-join Retail or tickets onto Telco (overlap of IDs is 0).
- Never put `Churn` on the operational Persona or in `customers`.
- Mark every important field as `REAL`, `DERIVED`, `SYNTHETIC`, or `PREDICTED`.

---

## 2. How it was developed (10 steps)

Work was done in small slices, each tested before the next.

| Step | What was built | Why |
|---|---|---|
| 1 | Data audit (schemas, quality, no-join policy) | Do not invent columns or false joins |
| 2 | `ingest.py` | Safe loaders, no import-time I/O, both Retail years |
| 3 | `clean_telco` | Keep all 7,043 rows; fill `TotalCharges=0` if `tenure=0`; no ML encoding |
| 4 | `clean_retail` + `clean_tickets` | Dates, duplicates; purchases filter for RFM; no Telco join |
| 5 | `validate.py` | Fail on contract errors; warn on known ticket quirks |
| 6 | `behavioral.py` (RFM) | Learn how *Retail* shoppers behave |
| 7 | `synthetic_behavior.py` + `synthetic_reviews.py` | Borrow **patterns**, not identities; ignore `Churn` |
| 8 | `persona/schema.py` + `persona_builder.py` | Assemble the shared Persona |
| 9 | `warehouse.py` + `pipeline.py` | Persist results in SQLite |
| 10 | `repository.py` | Read API for other agents |

ML preprocessing in `data/ml_data/data_preparing.ipynb` is a **separate** pipeline (encoding, train/test, `Churn` as `y`). It must not be mixed with this agent.

---

## 3. Pipeline (what runs in order)

```
ingest → clean → validate → RFM → synthetic history/review → Persona → warehouse
```

Entry point: `src/agents/data_agent/pipeline.py` → `run_data_agent_pipeline()`.

Other agents should call `src/agents/data_agent/repository.py`, not raw CSVs.

---

## 4. Components

### 4.1 Configuration — `config/settings.py`

Resolves paths from the **project root** (not the current working directory):

- `TELCO_RAW_PATH`, `RETAIL_RAW_CSV_PATH`, `RETAIL_RAW_XLSX_PATH`, `TICKETS_RAW_PATH`
- `DATABASE_URL` (default: `data/processed/warehouse.db`)

Optional env: `DATA_DIR`, `DATABASE_URL` (see `.env.example`).

---

### 4.2 Ingest — `src/agents/data_agent/ingest.py`

**Role:** load raw files only. No cleaning, no joins, no synthetic data.

**How it was built**

- Column lists (`TELCO_COLUMNS`, `RETAIL_COLUMNS`, `TICKET_COLUMNS`) copied from the real files.
- Importing the module does **not** read disk (the old version called `load_*()` at import time; that was removed).
- Retail default = Excel **all sheets** (2009–2010 and 2010–2011). CSV is year 1 only and is a fallback.
- `Customer ID` is read as nullable `Int64` (guest checkouts stay `<NA>`, not `13085.0`).

**Public functions:** `load_telco()`, `load_online_retail_ii()`, `load_support_tickets()`.

---

### 4.3 Clean — `src/agents/data_agent/clean.py`

**Role:** operational cleaning per source. **Not** ML one-hot / scaling / split.

| Function | What it does |
|---|---|
| `clean_telco` | `TotalCharges` → numeric; `tenure=0` → fill 0 (new customers, not errors); drop duplicate `customerID`; keep Yes/No as text |
| `clean_retail` | parse `InvoiceDate`; strip text; drop exact duplicate lines; **keep** cancels and guests |
| `filter_retail_purchases` | RFM subset: known customer, qty > 0, price > 0, invoice not `C`/`A` |
| `clean_support_tickets` | parse dates; strip text; lowercase email; drop duplicate `ticket_id`; keep `browser` nulls; Yes/No stay text |

Cancels/guests stay in cleaned Retail because they are real events. RFM uses the **filter**, not a new invented column.

---

### 4.4 Validate — `src/agents/data_agent/validate.py`

**Role:** check cleaned frames against contracts. Does not fix data.

- **Error** → stop (`DataValidationError`)
- **Warning** → record and continue

**Telco:** unique `customerID`, allowed categories, phone/internet consistency, `tenure=0` ⇒ `TotalCharges=0`, `Churn` excluded from `TELCO_OPERATIONAL_COLUMNS`.

**Retail / purchases:** datetime dates; purchases must not include guests or cancels.

**Tickets:** unique `ticket_id`, resolved ≥ created, CSAT 1–5.  
Warnings (known synthetic-file quirks): ~120k “open” tickets already have a resolved date; ~29k rows with response time > resolution time.

**Cross-source:** Telco `customerID` ∩ Retail `Customer ID` must be empty.

---

### 4.5 RFM (derived) — `src/agents/data_agent/behavioral.py`

**Role:** one row per **Retail** shopper. This is **DERIVED**, not synthetic, and never joined to Telco.

| Metric | Meaning |
|---|---|
| Recency | days since last purchase |
| Frequency | number of distinct invoices |
| Monetary | `sum(Quantity × Price)` |

Scores 1–4 (4 = best), then a label:

| Label | Rule (first match) |
|---|---|
| champion | R, F, M all ≥ 3 |
| new | R ≥ 3 and F ≤ 2 |
| at_risk | R ≤ 2 and F ≥ 3 |
| hibernating | R ≤ 2 and F ≤ 2 |
| loyal | F ≥ 3 (not already champion) |
| other | remainder |

`summarize_rfm_distributions()` returns quantiles and segment counts **without IDs**. Step 7 samples from this summary.

---

### 4.6 Synthetic behavior — `src/agents/data_agent/synthetic_behavior.py`

**Role:** invent a short **engagement timeline** for a Telco customer, calibrated on RFM *distributions*.

**How**

- Uses `customerID`, `tenure`, `MonthlyCharges` only.
- Event count ≈ median Retail frequency × tenure / 12 (capped at 24).
- Amounts ≈ `MonthlyCharges` with small noise.
- Every row: `lineage = "SYNTHETIC"`, `event_type = "synthetic_engagement"`.
- `tenure = 0` → empty history.
- Same seed + same customer ⇒ same history.
- **`Churn` is never read** (Yes and No produce the same output).

No Retail `Customer ID` is attached to a Telco person.

---

### 4.7 Synthetic reviews — `src/agents/data_agent/synthetic_reviews.py`

**Role:** attach a plausible review text, sampled from ticket **categories and canned sentences** (the ticket file has only 10 unique texts). No LLM in v1.

Tone from **Contract + TechSupport** only (not `Churn`):

| Tone | When |
|---|---|
| positive | Two year and TechSupport = Yes |
| negative | Month-to-month and TechSupport = No |
| neutral | everything else |

Then `sample_reference_tickets` + `generate_client_review` copies one `issue_description`. That sentence is **not** a real ticket from that Telco customer.

---

### 4.8 Persona — `src/persona/schema.py` + `src/agents/data_agent/persona_builder.py`

**Role:** the shared object Architecture B passes between agents.

| Block | Lineage | Content |
|---|---|---|
| demographics, services, contract, billing | REAL | Telco fields except `Churn` |
| `behavioral_history` | SYNTHETIC | list of event dicts (JSON-serializable, not a DataFrame) |
| `raw_review_text` | SYNTHETIC | sampled ticket sentence |
| `review_tone` | DERIVED | negative / neutral / positive |
| sentiment, emotions, … | empty | Sentiment Agent |
| `churn_risk_score`, `risk_factors` | empty | Prediction Agent (`PREDICTED` later) |

`to_dict()` / `from_dict()` are used to store the Persona in the warehouse.

---

### 4.9 Warehouse — `src/agents/data_agent/warehouse.py`

**Role:** SQLite schema (SQLAlchemy 2). Default file: `data/processed/warehouse.db`.

| Table | Contents |
|---|---|
| `customers` | Telco operational profile, **no Churn** |
| `retail_rfm` | Retail IDs only (`retail_customer_id`) |
| `synthetic_events` | synthetic histories (FK-style `customer_id` = Telco) |
| `synthetic_reviews` | synthetic reviews |
| `personas` | full Persona JSON |
| `pipeline_meta` | e.g. `rfm_stats` (distributions, no IDs) |

Telco string IDs (`7590-VHVEG`) and Retail integer IDs (`13085`) are **never** the same primary key.

---

### 4.10 ETL — `src/agents/data_agent/pipeline.py`

**Role:** run steps 2–8 in one job and load the warehouse.

`run_data_agent_pipeline(telco_path=..., retail_path=..., tickets_path=..., engine=..., seed=42, max_customers=...)`

On the real data this processes 7,043 Telco customers. Tests use tiny fixtures.

---

### 4.11 Repository (API) — `src/agents/data_agent/repository.py`

**Role:** the only way other agents and Streamlit should read Data Agent outputs.

| Function | Returns |
|---|---|
| `get_persona(customer_id)` | `Persona` |
| `get_customer(customer_id)` | customer dict (no Churn) |
| `list_customers(limit, offset)` | list of customers |
| `get_rfm_distributions()` | RFM quantile dict |
| `get_retail_rfm()` | Retail RFM rows |

Missing IDs raise `CustomerNotFoundError`.

---

### 4.12 Supporting files

| File | Role |
|---|---|
| `src/utils/db.py` | exposes the warehouse engine |
| `pytest.ini` | `pythonpath = .` so tests import `src` |
| `tests/test_ingest.py` | ingest, no I/O on import |
| `tests/test_data_agent.py` | Telco clean |
| `tests/test_clean_sources.py` | Retail / tickets clean + no join |
| `tests/test_validate.py` | validation + real-file warnings |
| `tests/test_behavioral.py` | RFM |
| `tests/test_synthetic.py` | history/review ignore `Churn` |
| `tests/test_persona.py` | Persona has no `Churn`, lineage set |
| `tests/test_pipeline.py` | mini ETL → warehouse → repository |

---

## 5. Lineage cheat sheet

| Kind | Examples |
|---|---|
| REAL | Telco demographics, services, contract, billing |
| DERIVED | Retail RFM table; review tone |
| SYNTHETIC | Telco `behavioral_history`, `raw_review_text` |
| PREDICTED | `churn_risk_score` (Prediction Agent, not this agent) |

`Churn` (Yes/No) is REAL **source label** for ML training only. It is not an operational feature.

---

## 6. How to run

From the project root, with the venv:

```powershell
.\.env\Scripts\python.exe -m pytest tests/ -q
```

Full ETL (slow if Excel both years are loaded):

```powershell
.\.env\Scripts\python.exe -c "from src.agents.data_agent.pipeline import run_data_agent_pipeline; print(run_data_agent_pipeline())"
```

Read a Persona after the warehouse is loaded:

```python
from src.agents.data_agent.repository import get_persona, list_customers

print(list_customers(limit=5))
persona = get_persona("7590-VHVEG")
print(persona.lineage)
print(persona.raw_review_text)
```

---

## 7. What this agent does *not* do

| Out of scope | Owner |
|---|---|
| Train XGBoost / SHAP | Prediction Agent |
| Sentiment / emotions | Sentiment Agent |
| Digital Twin scenarios | Simulation Agent |
| RAG / retention emails | Generator Agent |
| Final recommended action | Decision Agent |
| LangGraph routing | Orchestrator |

Those modules still contain stubs. They should consume `get_persona()`, not rebuild data from CSVs.

---

## 8. File map

```
src/agents/data_agent/
    ingest.py
    clean.py
    validate.py
    behavioral.py
    synthetic_behavior.py
    synthetic_reviews.py
    persona_builder.py
    warehouse.py
    pipeline.py
    repository.py
src/persona/schema.py
config/settings.py
data/raw/                  # Telco, Retail, tickets
data/processed/warehouse.db
data/ml_data/              # ML notebook only — not this agent
docs/data_agent.md         # this file
```
