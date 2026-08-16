# Guide des données

Voir le document complet fourni précédemment (Guide_Donnees.docx) pour la méthodologie détaillée :

- Telco Customer Churn (IBM) : socle client, entraînement de l'Agent Prédiction
- Online Retail II (UCI) : calibrage statistique de l'Agent Simulation
- Customer Support Ticket Dataset (200K) : corpus RAG + calibrage de l'Agent Analyse de Sentiments

Aucune fusion ligne-à-ligne n'est possible entre ces 3 sources (pas de client commun).
Deux colonnes sont générées par client Telco : historique_comportemental et avis_client
(voir src/agents/data_agent/synthetic_behavior.py et synthetic_reviews.py).

Le détail de l'Agent Données (ingest, clean, RFM, Persona, warehouse, API) est dans `docs/data_agent.md`.
