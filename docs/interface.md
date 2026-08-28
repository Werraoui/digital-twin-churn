# Interface Streamlit — fonctionnalités

Espace de **pilotage rétention** autour du Customer Digital Twin.  
L’interface ne refait pas l’ETL : elle lit les Personas du warehouse, lance l’orchestrateur multi-agents, et suit la file opérationnelle (appel / email / contacté).

Persistance : **Supabase cloud** comme source de vérité pour les Personas (lecture / écriture), avec miroir SQLite optionnel (`LOCAL_MIRROR`).

---

## Lancer

Depuis la **racine** du projet :

```powershell
.\.venv\Scripts\Activate.ps1
streamlit run interface/app.py
```

Prérequis : Personas déjà sur Supabase (table `personas`) — ou sync initiale depuis SQLite.

---

## Backend cloud (`PERSONA_BACKEND`)

| Valeur | Comportement |
|---|---|
| `supabase` (défaut si `.env` configuré) | **Lecture + écriture** cloud ; miroir SQLite si `LOCAL_MIRROR=true` |
| `local` | SQLite uniquement |
| `dual` | Écrit les deux ; lit selon `PERSONA_READ_FROM` |

```env
PERSONA_BACKEND=supabase
PERSONA_READ_FROM=supabase
LOCAL_MIRROR=true
SUPABASE_STRICT=true
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_KEY=...
SUPABASE_ENABLED=true
```

L’orchestrateur, la fiche client, le batch et les analytics passent tous par `get_persona` / `save_persona` → **Supabase**.

---

## Idée générale

| Tu veux… | Page |
|---|---|
| Voir l’état global et les alertes | **Accueil** |
| Trouver qui traiter en priorité | **Clients à risque** |
| Scorer / décider / générer un message pour 1 client | **Fiche client** |
| Tester une offre sans toucher au profil réel | **Simulateur** |
| Traiter plusieurs clients d’un coup | **Batch** |
| Analyser scores, SHAP, funnel | **Analytics** |

Règles métier rappelées dans l’UI :

- score <= **0,5** → pas d’action
- **0,5 ≤ score <= 0,7** → canal **email**
- score ≥ **0,7** → canal **appel**
- une seule offre retenue (meilleur Δ risque / coût relatif)
- un seul canal généré (call **ou** email, jamais les deux)

---

## 1. Accueil (`app.py`) — Vue d’ensemble

**À quoi ça sert** : tableau de bord pour le chef d’équipe / analyste.

### Fonctionnalités

- **KPIs**
  - nombre de Personas
  - clients à traiter (score ≥ 0,5) et critiques (≥ 0,7)
  - file ops (à appeler / à emailer)
  - messages générés, validés, envoyés, clients contactés
- **Alerte** si des clients critiques ne sont pas encore marqués « contactés »
- **File de travail** : aperçu des statuts `to_call` / `to_email` / `postponed`
- **Derniers runs** de l’orchestrateur (historique)
- **Aperçu** des clients scorés récemment
- Sidebar :
  - **Rafraîchir les données** (vide le cache UI)
  - **Sync depuis Supabase** (si configuré) : recharge le local depuis le cloud

---

## 2. Clients à risque — Priorisation

**À quoi ça sert** : construire la liste du jour et exporter / mettre à jour la file.

### Fonctionnalités

- **Filtres avancés**
  - scorés uniquement
  - plage de score (min / max)
  - contrat, sentiment, canal
  - statut de file (`none`, `to_call`, `to_email`, `contacted`, `postponed`)
  - ancienneté (tenure)
  - avec message uniquement
- **Tableau** avec niveau de risque, offre, canal, statut message
- **Export CSV** pour priorisation hors outil
- **Ouvrir la fiche** d’un client sélectionné
- **Mise à jour rapide du statut** file (si rôle `writer`)

---

## 3. Fiche client — Cœur opérationnel

**À quoi ça sert** : travailler un client de bout en bout.

### Fonctionnalités

#### Orchestrateur

- Bouton **Lancer l’orchestrateur** :  
  sentiment → score churn + SHAP → simulation d’offres → décision (1 offre + 1 canal) → génération du message → sauvegarde
- Toggle **Sauvegarder** : écrit SQLite (+ Supabase si activé)
- Panneau **Avant / après** : compare score, offre, canal, file et présence de message avant/après le run

#### Lecture du twin

- Bandeau de risque (faible / élevé / critique)
- Panneaux : contrat & facturation, sentiment, décision
- Justification de la décision
- **Facteurs SHAP locaux** (+ graphique)
- **Scénarios simulés** : avant / après, Δ, coût relatif, ROI (Δ/coût)

#### File opérationnelle

Statuts de file (`ops_status`) :

| Valeur | Signification |
|---|---|
| `none` | — |
| `to_call` | À appeler |
| `to_email` | À emailer |
| `contacted` | Déjà contacté |
| `postponed` | Reporté |

Statuts message (`message_status`) :

| Valeur | Signification |
|---|---|
| `none` | — |
| `draft` | Brouillon (après génération) |
| `validated` | Validé par l’équipe |
| `rejected` | Rejeté |
| `sent` | Envoyé / script utilisé |

- Enregistrement des statuts
- **Note agent** libre (sauvegardée sur le Persona)

#### Message de rétention

- Affichage / **édition** du texte
- Actions : **Sauver** · **Valider** · **Rejeter** · **Marquer envoyé** (passe aussi la file en `contacted`)
- Modification optionnelle de l’offre recommandée
- Contexte RAG (extraits tickets) en expand

#### Historique

- Liste des **runs** pour ce client (quand, statut, scores, opérateur)

---

## 4. Simulateur — What-if

**À quoi ça sert** : tester une action de rétention **sans écraser** le profil client réel (clone).

### Fonctionnalités

- Choix d’un client déjà scorés + d’une action
- **Simuler cette action** : score avant / après, Δ, coût relatif
- **Recalculer tous les scénarios** : met à jour `simulation_scenarios` sur le Persona (sauvegarde)
- Tableau comparatif des scénarios applicables

Utile avant de valider une offre sur la fiche client.

---

## 5. Batch — Traitement de masse

**À quoi ça sert** : lancer l’orchestrateur sur plusieurs clients (ex. top N du jour).

### Fonctionnalités

- Nombre de clients (N)
- Option **prioriser les non scorés** ou filtrer par score minimum
- Toggle sauvegarde SQLite + Supabase
- Barre de progression + tableau de résultats (statut, score, offre, canal)

Réservé au rôle `writer`. Peut être long (ML + LLM) : commencer par N = 3–5.

---

## 6. Analytics — Pilotage data

**À quoi ça sert** : comprendre le portefeuille scorés et le funnel rétention.

### Fonctionnalités

- **Distribution** des scores (moyenne, médiane, ≥ seuil, critiques)
- **Top facteurs SHAP globaux** (agrégation des |SHAP| sur les Personas scorés)
- **Funnel** : générés → validés → envoyés → contactés
- Répartition des statuts file / message
- **Activité récente** (runs)
- **ROI relatif moyen** des scénarios par type d’action (Δ/coût)

Le « churn évité » réel n’est pas calculé ici : il faudrait un feedback métier (client resté / parti). L’UI suit le funnel opérationnel.

---

## Auth, rôles et sidebar

| Variable `.env` | Rôle |
|---|---|
| `UI_PASSWORD` | Mot de passe d’accès (vide = ouvert) |
| `UI_OPERATOR` | Nom tracé dans `pipeline_runs` |
| `UI_ROLE` | `writer` (défaut) ou `reader` (lecture seule) |
| `UI_CACHE_TTL_SECONDS` | Cache de la table Personas (défaut 15 s) |

La sidebar affiche l’opérateur, le rôle, et l’état Supabase (connecté / désactivé).

---

## Persistance & Supabase

### Comportement (cloud-first)

1. `get_persona` / `list_personas` / `list_pipeline_runs` → **Supabase**
2. `save_persona` / runs orchestrateur → **upsert Supabase** (+ miroir SQLite si `LOCAL_MIRROR`)
3. Tables ETL annexes (customers, RFM, events) restent en SQLite pour l’instant

### Config

1. Créer un projet Supabase.
2. Exécuter `docs/supabase_schema.sql` dans l’éditeur SQL.
3. Renseigner `SUPABASE_*` et `PERSONA_BACKEND=supabase` dans `.env`.

Tables cloud : `personas`, `pipeline_runs`.

---

## Parcours recommandé (équipe rétention)

1. **Accueil** — regarder alertes + file du jour  
2. **Clients à risque** — filtrer, exporter si besoin, ouvrir une fiche  
3. **Fiche client** — lancer l’orchestrateur (si pas encore scorés / pas de message)  
4. Relire SHAP + scénarios, **valider** ou éditer le message  
5. Contacter le client → **Marquer envoyé** / statut `contacted` + note  
6. **Analytics** en fin de journée pour le funnel  
7. **Batch** pour traiter une vague de non scorés ou de hauts risques

---

## Fichiers techniques

| Fichier | Rôle |
|---|---|
| `interface/app.py` | Accueil |
| `interface/pages/1_Clients_a_risque.py` | Priorisation |
| `interface/pages/2_Fiche_client.py` | Fiche + orchestrateur + ops |
| `interface/pages/3_Simulateur.py` | What-if |
| `interface/pages/4_Batch.py` | Batch |
| `interface/pages/5_Analytics.py` | Analytics |
| `interface/services.py` | Accès warehouse, ops, batch, SHAP global |
| `interface/auth.py` | Gate mot de passe |
| `interface/style.py` | CSS / en-têtes de page |
| `src/integrations/supabase_store.py` | Dual-write PostgREST |
| `src/persona/ops.py` | Labels et helpers de statuts |

---

## Limites connues

- Pas d’envoi réel d’email / d’appel (marquage manuel uniquement)
- Streamlit n’écoute pas le Realtime Supabase en continu : rafraîchir via cache court + boutons
- Premier chargement de ~7000 Personas peut prendre quelques secondes
- Le LLM (Groq/Gemini…) doit être configuré pour des messages non template
1