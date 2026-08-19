# Jeu de règles de simulation

Cinq actions. Chacune change **un** champ du Persona, puis la **même logreg** recalcule `churn_risk_score`.  
Si la condition n’est pas remplie, l’action est ignorée (score inchangé).

Mesure de référence : client `7590-VHVEG` (month-to-month, e-check, paperless, DSL, pas de sécurité), score initial **0,805**.

---

## R1 — `offer_two_year_contract`

**But.** Passer sur un engagement 2 ans, le levier beeswarm le plus fort après tenure / charges (qui ne sont pas des offres).

**Condition.** `contract.type` ≠ `Two year`.  
S’applique donc au month-to-month **et** au contrat 1 an.

**Effet Persona.** `contract.type ← "Two year"`.

**Effet vecteur ML.** `Contract_Two year = 1`, `Contract_One year = 0`.  
Beeswarm : 🔴 Two year → ↓ churn.

**Fruit sur le score (réf.).** 0,805 → **0,464** (**−0,341**). Le client passe sous le seuil 0,5.

---

## R2 — `offer_one_year_contract`

**But.** Alternative plus légère que le 2 ans, uniquement pour les sans engagement.

**Condition.** `contract.type = "Month-to-month"` seulement.  
Un client déjà en 1 an ou 2 ans : no-op (le 2 ans est testé par R1).

**Effet Persona.** `contract.type ← "One year"`.

**Effet vecteur ML.** `Contract_One year = 1`, `Contract_Two year = 0`.  
Beeswarm : 🔴 One year → ↓ churn (moins fort que le 2 ans).

**Fruit sur le score (réf.).** 0,805 → **0,663** (**−0,142**).

---

## R3 — `add_online_security`

**But.** Activer l’option sécurité, associée à une baisse de churn.

**Condition.**
- `services.internet_service` ≠ `No` (sinon la valeur Telco est `No internet service`, ce n’est pas une option vendable) ;
- `services.online_security` ≠ `Yes`.

**Effet Persona.** `services.online_security ← "Yes"`.

**Effet vecteur ML.** `OnlineSecurity_Yes = 1`.  
Beeswarm : 🔴 OnlineSecurity Yes → ↓ churn.

**Fruit sur le score (réf.).** 0,805 → **0,766** (**−0,039**). Plus faible que le contrat, mais signe stable.

---

## R4 — `switch_to_autopay`

**But.** Sortir du paiement Electronic check, qui **augmente** le churn.

**Condition.** `contract.payment_method = "Electronic check"`.  
Bank transfer / carte déjà en automatique : no-op.

**Effet Persona.** `contract.payment_method ← "Credit card (automatic)"`.

**Effet vecteur ML.** `PaymentMethod_Electronic check = 0`, `PaymentMethod_Credit card (automatic) = 1`.  
Beeswarm : 🔴 Electronic check → ↑ churn.

**Fruit sur le score (réf.).** 0,805 → **0,740** (**−0,065**).

---

## R5 — `disable_paperless_billing`

**But.** Désactiver la facture électronique, associée à plus de churn.

**Condition.** `contract.paperless_billing = "Yes"`.

**Effet Persona.** `contract.paperless_billing ← "No"`.

**Effet vecteur ML.** `PaperlessBilling = 0`.  
Beeswarm : 🔴 PaperlessBilling → ↑ churn.

**Fruit sur le score (réf.).** 0,805 → **0,744** (**−0,061**).

---

## Synthèse des fruits (même client)

| Règle | Appliquée ? | Score après | Δ risque |
|---|---|---|---|
| R1 Two year | oui | 0,464 | **−0,341** |
| R2 One year | oui | 0,663 | **−0,142** |
| R3 Online security | oui | 0,766 | **−0,039** |
| R4 Autopay | oui | 0,740 | **−0,065** |
| R5 Anti-paperless | oui | 0,744 | **−0,061** |

Toutes les cinq **baissent** le score quand elles s’appliquent. Le contrat 2 ans est le seul levier qui, seul, fait passer ce profil sous 0,5.

Les actions sont **indépendantes** (un clone par règle). On ne les empile pas dans un même scénario.

`run_scenarios` ne renvoie par défaut **que** les actions `applied=True`.

## Coûts relatifs (pour l’Agent Décision)

Unité arbitraire, pas des euros. `delta_per_cost = delta / cost`.

| Règle | `cost` |
|---|---|
| R1 Two year | 3.0 |
| R2 One year | 2.0 |
| R3 Online security | 1.5 |
| R4 Autopay | 0.5 |
| R5 Anti-paperless | 0.3 |

Persistance : `simulate_stored_persona(customer_id)` écrit `persona.simulation_scenarios` dans le warehouse **sans** modifier le contrat réel. Lineage `SYNTHETIC`. Sous le seuil 0,5 : liste vide.

---

## Hors jeu (volontairement)

Ces features bougent le beeswarm mais **ne sont pas** des règles, parce qu’elles ne donneraient pas un fruit *métier* acceptable, ou un fruit *inverse* :

| Feature | Si on la changeait… | Pourquoi ce n’est pas dans le jeu |
|---|---|---|
| `tenure` | plus long → ↓ churn | on ne “offre” pas de l’ancienneté |
| `MonthlyCharges` ↓ | *dans ce modèle* ↓ charges → **↑** churn | une remise casserait le fruit |
| `TotalCharges` | élevé → ↑ churn | historique, pas une offre |
| Fibre / streaming / multi-lignes à `No` | ↓ churn | downsell, pas de la rétention |

---

Code : `src/agents/simulation_agent/rules_engine.py` (`ACTIONS` = R1…R5 dans cet ordre).
