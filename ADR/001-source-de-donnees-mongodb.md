# ADR 001 — Source des données d'entraînement : MongoDB (base analytique)

- **Statut** : accepté
- **Date** : 2026-10-29
- **Décideurs** : équipe Data / ML du projet Livraison Express

## Contexte

L'application doit entraîner son modèle sur les commandes réelles. Deux bases sont disponibles :

```text
ERP Pro 2015  <── temps réel, logiciel ──>  PostgreSQL (production)  ── temps réel, ETL ──>  MongoDB (analytique)
```

| | PostgreSQL (production) | MongoDB (analytique) |
| --- | --- | --- |
| Rôle | Base du logiciel, partagée avec une **autre application critique** | Montée pour les Data Analysts, pour **protéger la production** |
| Historique | Depuis 2015 | Depuis 2023 (historique antérieur non copié) |
| Schéma | Modifié en 2017 et 2023 : colonnes nulles avant ces dates | Schéma courant, colonnes complètes |
| Exploitation | Plus d'administrateur depuis 2023 | Maintenue par un alternant en fin de contrat |
| Alimentation | Écritures de l'ERP (bilatéral) | ETL unilatéral, temps réel, depuis la production |

Profilage des données (environnement de test, simulateur ERP du tp4) :

- **PostgreSQL** : `weekend` est nul au 1er semestre 2015 et `preparation_time_min` jusqu'en juillet 2017. Cela concerne environ 2 200 commandes sur 10 000.
- **MongoDB** : aucune valeur nulle, des valeurs dans les bornes et une cohérence date / jour / week-end vérifiée. Les deux bases partagent cependant trois écarts avec le contrat de l'API :
  - un vocabulaire différent (`clear`, `suburb`, `business`…) ;
  - une `carrier_capacity` exprimée en colis (de 5 à 50) au lieu d'un taux ;
  - aucune variable cible.

## Décision

Le modèle s'entraîne sur **MongoDB** (`livraison_express.orders`), en **lecture seule**.

Les commandes reçues par l'API sont écrites dans une collection dédiée, `api_orders`, et ne touchent jamais aux données de l'ERP.

## Justification

1. **Ne pas intégrer directement la base de production.** Les lectures massives et répétées de l'entraînement planifié chargeraient une base partagée avec une application critique et dépourvue d'administrateur. MongoDB a justement été créée pour isoler les usages Data. Une erreur côté Data ne peut pas remonter vers la production, car le flux est unilatéral.
2. **La qualité des données.** Le schéma de MongoDB est complet. L'historique PostgreSQL antérieur à 2017 n'a pas toutes les variables du modèle, il faudrait donc l'imputer ou l'écarter. Les données 2023+ reflètent aussi mieux l'activité actuelle, qui est celle que l'API prédit.
3. **La fraîcheur.** L'ETL alimente MongoDB en temps réel, assez vite pour un réentraînement périodique.
4. **Le découplage.** L'application dépend du contrat `OrderStore` (l'`OrderRepository` du cours). Si la source change, seule l'implémentation `MongoOrderStore` est remplacée.

## Conséquences et risques

| Risque | Mesure |
| --- | --- |
| Historique limité à 2023+ | Le volume suffit au modèle actuel. Si besoin, une reprise ponctuelle de l'historique PostgreSQL (2017+) par l'ETL est possible, sans lecture applicative de la production. |
| Maintenance (départ de l'alternant) | Signalé au management. Base déclarée dans les environnements Docker de test et de prod, sonde `/health/ready` qui vérifie la connexion. |
| Données non fiables par principe | Deux validations : **validation ETL** (raw → silver, lignes invalides en quarantaine) et **validation applicative** (gold → entraînement, `OrderDataValidator`). |
| Écarts de format ERP / API | Couche silver : traduction du vocabulaire et capacité ramenée sur [0, 1] (hypothèse : 50 colis = capacité maximale). |
| Pas de cible dans l'ERP | En attendant que l'ERP remonte le résultat réel de livraison, la cible de la couche gold est simulée avec la règle métier du générateur. **À remplacer dès que la donnée existe.** |
| Dépendance à la fréquence de l'ETL | Le réentraînement n'a lieu que si assez de nouvelles commandes sont arrivées (`RETRAIN_MIN_NEW_ORDERS`). |

## Alternatives écartées

- **PostgreSQL directement** : risque pour la production critique, colonnes historiques incomplètes et aucune équipe pour l'administrer.
- **Réplica PostgreSQL dédié aux Data** : c'est la bonne pratique si l'on garde le SQL, mais elle n'existe pas aujourd'hui et demande un administrateur PostgreSQL. C'est une piste pour plus tard.
