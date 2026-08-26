# Orchestrateur — workflow (README)

L’**Agent Orchestrateur** ne calcule rien lui-même.  
Il **enchaîne** les autres agents avec **LangGraph**, pour **un client à la fois**.

Mémoire partagée = le **Persona** (passé de nœud en nœud).

Code : `src/orchestrator/`  
Détail technique : `docs/orchestrator.md`

---

## Idée simple

```
Un client entre
    → on enrichit / score
    → si risque bas : on s’arrête
    → si risque haut : on simule des offres
    → on choisit UNE offre + UN canal (call OU email)
    → on génère LE message
    → on sauvegarde le Persona
```

---

## Schéma du graphe

```
START
  │
  ▼
load_persona          Charge le Persona (warehouse) ou le construit
  │
  ▼
sentiment             Analyse l’avis (skip si déjà enrichi)
  │
  ├─ pas d’avis / pas enrichi ──► low_risk ──► persist ──► END
  │
  ▼
predict               Score de churn (logreg + SHAP)
  │
  ├─ risk < 0.5 ──────────────► low_risk ──► persist ──► END
  │
  ▼
simulate              What-if (R1–R5) → liste de scénarios
  │
  ▼
decide                Meilleur delta/cost + canal call|email
  │
  ├─ aucune offre ────────────► persist ──► END
  │
  ▼
generate              Script d’appel OU email (RAG + LLM/template)
  │
  ▼
persist               Écrit le Persona dans warehouse.db
  │
  ▼
END
```

---

## Chaque étape en une phrase

| Nœud | Agent appelé | Fait quoi |
|---|---|---|
| `load_persona` | Data / repository | Récupère le Persona du client |
| `sentiment` | Sentiment | Remplit sentiment, émotions, topics |
| `predict` | Prédiction | Calcule `churn_risk_score` + facteurs SHAP |
| `low_risk` | — | Stop : “aucune action nécessaire” |
| `simulate` | Simulation | Teste les offres, calcule score avant/après |
| `decide` | Décision | Choisit **1 offre** + **1 canal** |
| `generate` | Générateur | Rédige **1 texte** (call **ou** email) |
| `persist` | repository | Sauvegarde dans SQLite |

L’orchestrateur **ne refait pas** l’ETL Data Agent : le warehouse doit déjà contenir les Personas.

---

## Branches importantes

**1. Après le sentiment**  
- Persona enrichi → continuer vers la prédiction  
- Sinon → stop (pas de score fiable sans avis)

**2. Après la prédiction**  
- `churn_risk_score < 0.5` → stop (pas de rétention)  
- `≥ 0.5` → simulation

**3. Après la décision**  
- pas d’offre applicable → stop  
- offre choisie → génération du message

---

## Ce que renvoie le workflow

```python
{
  "persona": ...,          # Persona final
  "scenarios": [...],      # scénarios simulés (si risque haut)
  "action": {...} | None,  # offre + canal (ou None)
  "message": "...",        # texte de rétention ou message d’arrêt
  "justification": "...",  # pourquoi cette décision
  "status": "generated" | "low_risk" | "no_action" | ...
}
```

---

## Comment le lancer

Depuis la racine du projet :

```powershell
.\.venv\Scripts\Activate.ps1
```

```python
from src.orchestrator.graph import run_for_customer

result = run_for_customer("7590-VHVEG", persist=True)
print(result["status"])
print(result["action"])
print(result["message"])
```

Sans sauvegarder (tests) :

```python
from src.orchestrator.graph import run_pipeline

result = run_pipeline(persona=persona, persist=False)
```

---

## Fichiers de l’agent

| Fichier | Rôle |
|---|---|
| `state.py` | État LangGraph (`TwinState`) |
| `nodes.py` | Fonctions de chaque nœud |
| `router.py` | Conditions (risque, décision, sentiment) |
| `graph.py` | Graphe compilé + `run_for_customer` / `run_pipeline` |

---

## Lien avec le reste du PFA

```
Data Agent (ETL, Personas dans warehouse)
    → Orchestrateur (ce workflow)
         → Sentiment → Prédiction → Simulation → Décision → Génération
    → (plus tard) Streamlit pour afficher le résultat
```

Voir aussi : `docs/README_decision_and_generation.md` (détail décision + message).
