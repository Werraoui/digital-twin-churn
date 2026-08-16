# Digital Twin Client & Prédiction du Churn — Architecture Multi-Agents

Prototype PFA : Digital Twin client combiné à une IA hybride (prédictive, générative, agentique)
pour anticiper le churn et recommander des actions de rétention.

## Architecture

Un agent orchestrateur (LangGraph) supervise 6 agents spécialisés. Le Persona client circule
entre eux comme mémoire partagée, construit par l'Agent Données puis enrichi par l'Agent Analyse
de Sentiments avant d'alimenter la Prédiction et la Simulation. Voir `docs/architecture.md`.

## Structure du projet

```
src/orchestrator/       Agent orchestrateur (LangGraph, routage)
src/agents/data_agent/          Agent Données (ETL, construction du Persona initial)
src/agents/sentiment_agent/     Agent Analyse de Sentiments (enrichit le Persona)
src/agents/prediction_agent/    Agent Prédiction (XGBoost, SHAP)
src/agents/simulation_agent/    Agent Simulation (Digital Twin, moteur de règles)
src/agents/generator_agent/     Agent Générateur (RAG, ChromaDB, messages)
src/agents/decision_agent/      Agent Décision (recommandation finale justifiée)
src/persona/             Schéma et modèle de données du Persona client
interface/                Application Streamlit (tableau de bord)
pipelines/                Exemple de DAG Airflow
tests/                     Tests unitaires (pytest)
docs/                       Documentation (architecture, guide des données)
notebooks/                  Exploration et prototypage
```

## Démarrage rapide

```bash
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # renseigner ta clé API Claude
streamlit run interface/app.py
```

## Jeux de données

Voir `docs/data_guide.md` pour la méthodologie des sources, et `docs/data_agent.md` pour
le détail de l'Agent Données (composants, pipeline, Persona, warehouse).

## Tests

```bash
pytest tests/
```
