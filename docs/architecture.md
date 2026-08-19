# Architecture — Digital Twin & Prédiction du Churn (Multi-Agents)

Voir les documents complets fournis précédemment :
- Architecture_MultiAgents.pdf / .tex — description détaillée de chaque agent
- archi_MAS.png — schéma d'architecture

## Résumé

Un agent orchestrateur (LangGraph) supervise 6 agents spécialisés :
Données, Analyse de Sentiments, Prédiction, Simulation (Digital Twin), Générateur (RAG), Décision.

Le Persona client circule entre les agents comme mémoire partagée : construit par l'Agent Données,
enrichi par l'Agent Analyse de Sentiments, puis consommé par la Prédiction et la Simulation.

Jeu de règles du jumeau (effet mesuré sur le score) : `docs/simulation_rules.md`.
