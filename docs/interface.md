# Interface Streamlit

Tableau de bord pour explorer les Personas et lancer l’orchestrateur.

## Lancer

Depuis la **racine** du projet :

```powershell
.\.venv\Scripts\Activate.ps1
streamlit run interface/app.py
```

## Pages

| Page | Rôle |
|---|---|
| Accueil (`app.py`) | KPIs warehouse (scorés, risque, messages) |
| Clients à risque | Tableau filtrable + ouverture fiche |
| Fiche client | Persona, SHAP, scénarios, **Lancer l’orchestrateur**, message |
| Simulateur | What-if sur une action (clone, sans changer le profil réel) |

## Fichiers

- `interface/services.py` — lecture warehouse + appels orchestrateur / simulation  
- `interface/style.py` — CSS (teal / papier, pas de thème violet)  
- `interface/bootstrap.py` — ajoute la racine du repo au `PYTHONPATH`

Le warehouse (`data/processed/warehouse.db`) doit déjà contenir des Personas.
