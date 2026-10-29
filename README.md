# Cloud-AI-Engineering — Éligibilité à la livraison express

[![CI](https://github.com/Charlyf-Data/Cloud-AI-Engineering/actions/workflows/ci.yml/badge.svg?branch=develop)](https://github.com/Charlyf-Data/Cloud-AI-Engineering/actions/workflows/ci.yml)

Service de machine learning qui prédit si une commande peut être livrée en express (dans la journée).
Il transforme le notebook expérimental `Start/project_test_v1_final_final2.ipynb` en une application Python
exposée par une API FastAPI et conteneurisée avec Docker. Le contrat de l'API est `Start/openapi.yml`.

> Le modèle est une aide à la décision : il ne remplace pas les règles métier. L'ERP ne remonte pas encore
> le résultat réel des livraisons : la cible est simulée (voir [ADR 001](ADR/001-source-de-donnees-mongodb.md)).

## Démarrage rapide (Docker)

Prérequis : Docker Desktop (ou Docker Engine + Compose v2).

```bash
cp .env.example .env          # facultatif : des valeurs par défaut existent
docker compose up -d --build  # génère les données, entraîne le modèle, puis démarre l'API
docker compose ps             # le service api doit être "healthy"
```

L'API est disponible sur <http://localhost:8000> et sa documentation interactive sur <http://localhost:8000/docs>.

```bash
curl -X POST http://localhost:8000/v1/predictions -H "Content-Type: application/json" \
  -d '{"hour":14,"day_of_week":2,"weekend":0,"distance_km":3.5,"order_value_eur":89.9,"weight_kg":2.4,"stock_available":1,"preparation_time_min":18,"carrier_capacity":0.85,"weather":"normal","delivery_zone":"centre","customer_type":"premium"}'
# {"order_id":"CMD-...","express_eligible":true,"decision":"oui","probability":0.9377,"model_version":"1.1.0",...}
```

Arrêt : `docker compose down` (le modèle est conservé dans le volume `artifacts`).

## Environnements test et prod (séance 4)

Les commandes viennent de l'ERP via la base analytique MongoDB. Le choix est justifié dans
[ADR 001](ADR/001-source-de-donnees-mongodb.md). Le simulateur fourni (`tp4/`) joue l'ERP, PostgreSQL et l'ETL.

| Fichier | Contenu |
| --- | --- |
| `docker-compose.test.yml` | Données bornées et éphémères : ERP → `etl` → `train` → `api`, une seule fois |
| `docker-compose.prod.yml` | Volumes persistants, flux ERP continu, premier `etl` + `train`, puis **Airflow** qui réentraîne périodiquement |
| `docker-compose.yml` | Dev : CSV synthétique, sans base de données |

```bash
docker compose -f docker-compose.test.yml up --build      # API : http://localhost:8000
docker compose -f docker-compose.test.yml down -v

docker compose -f docker-compose.prod.yml up -d --build   # Airflow : http://localhost:8080
docker compose -f docker-compose.prod.yml logs airflow | grep -i password   # utilisateur admin
```

### Données : couches raw, silver et gold

La commande `etl` lit MongoDB et écrit des fichiers Parquet dans le volume `lake`. MongoDB reste en lecture seule.

| Couche | Fichier | Contenu |
| --- | --- | --- |
| raw | `lake/raw/orders.parquet` | Copie brute de la collection `orders`, avec `ingested_at` |
| rejected | `lake/rejected/orders.parquet` | Lignes refusées par la **validation ETL**, avec `rejection_reason` |
| silver | `lake/silver/orders.parquet` | Lignes valides, dédoublonnées, au vocabulaire de l'API, capacité ramenée sur [0, 1] |
| gold | `lake/gold/orders.parquet` | Lignes complètes, cible ajoutée, colonnes du modèle uniquement |

Deux validations successives :
1. **Validation ETL** (`data/raw_validator.py`, raw → silver). Une colonne absente bloque l'ETL. Une ligne invalide part en quarantaine. Les motifs possibles : bornes, cohérence date / jour / week-end, modalités inconnues. Les valeurs nulles dues aux migrations de schéma sont tolérées.
2. **Validation applicative** (`data/validator.py`, gold → entraînement). La commande `train` revérifie les colonnes et les règles qualité avant d'entraîner. L'API valide aussi chaque requête avec Pydantic.

### Orchestration : Airflow

Le DAG `airflow/dags/retrain_express_delivery.py` exécute `etl >> train`. Chaque tâche lance l'image d'entraînement dans un conteneur, avec le `DockerOperator`. L'entraînement est un processus d'exécution, pas une étape de la CI/CD.

La tâche `train` ne réentraîne que si au moins `RETRAIN_MIN_NEW_ORDERS` nouvelles commandes sont arrivées. L'API recharge ensuite le nouveau modèle toutes les `MODEL_REFRESH_SECONDS`, sans redémarrer.

## Démarrage en local

Prérequis : Python 3.11. Les commandes se lancent depuis la racine du projet, dans cet ordre.

```bash
pip install -r requirements-train.txt
export PYTHONPATH=src                       # PowerShell : $env:PYTHONPATH = "src"
python -m express_delivery.main generate    # crée data/orders_dataset.csv (données synthétiques)
python -m express_delivery.main train       # entraîne et écrit artifacts/<MODEL_VERSION>/
# avec MongoDB : MONGO_URI=... python -m express_delivery.main etl, puis DATA_PATH=lake/gold/orders.parquet train
python -m express_delivery.main serve       # démarre l'API
```

## Tests et qualité

```bash
pip install -r requirements-dev.txt
pytest          # 50 tests : données, ETL, modèle, contrat de l'API (sans base de données)
pylint src      # seuil minimal : 9/10
```

## Intégration et livraison continues (GitHub Actions)

| Workflow | Déclenchement | Rôle |
| --- | --- | --- |
| `ci.yml` | Pull request ou push vers `develop` / `main` | Pylint, pytest, puis build de l'image Docker |
| `release.yml` | Publication d'une release GitHub (tag `vX.Y.Z`) | Relance la CI, puis publie les images sur GitHub Container Registry |

Images publiées à chaque release :

```bash
docker pull ghcr.io/charlyf-data/cloud-ai-engineering:latest        # API
docker pull ghcr.io/charlyf-data/cloud-ai-engineering-train:latest  # job d'entraînement
```

## Endpoints (séance 1)

| Endpoint | Rôle | Codes |
| --- | --- | --- |
| `GET /health` | Le processus est vivant | 200 |
| `GET /health/ready` | Le modèle est chargé et le stockage répond | 200, 503 |
| `POST /v1/predictions` | Prédiction immédiate pour une commande | 200, 422, 503 |
| `POST /v1/orders` | Enregistre une commande ; la prédiction est calculée en tâche de fond | 202, 422 |
| `GET /v1/orders/{order_id}` | Relit une commande enregistrée | 200, 404 |

## Configuration

Tous les paramètres sont lus depuis les variables d'environnement ou le fichier `.env` (voir `.env.example`).

| Variable | Défaut | Rôle |
| --- | --- | --- |
| `APP_ENV` | `dev` | Environnement courant (dev, test, prod) |
| `LOG_LEVEL` | `INFO` | Niveau des logs (format JSON) |
| `MODEL_VERSION` | `1.1.0` | Version du modèle entraîné et chargé |
| `PREDICTION_THRESHOLD` | `0.5` | Seuil de décision oui/non |
| `API_PORT` | `8000` | Port de l'API |
| `N_ROWS` / `RANDOM_STATE` / `TEST_SIZE` | `6000` / `42` / `0.2` | Paramètres de génération et d'entraînement |
| `DATA_PATH` | `data/orders_dataset.csv` | Jeu d'entraînement (CSV ou couche gold `.parquet`) |
| `LAKE_DIR` | `lake` | Répertoire des couches raw / rejected / silver / gold |
| `MONGO_URI` | vide | Base analytique ; sans elle, commandes de l'API en mémoire |
| `MONGO_DATABASE` / `MONGO_ERP_COLLECTION` / `MONGO_API_COLLECTION` | `livraison_express` / `orders` / `api_orders` | Base et collections |
| `RETRAIN_MIN_NEW_ORDERS` | `0` | Nouvelles commandes nécessaires pour réentraîner (0 : toujours) |
| `MODEL_REFRESH_SECONDS` | `60` | Période de rechargement du modèle par l'API (0 : désactivé) |
| `MLFLOW_TRACKING_URI` | vide | Active le suivi MLflow de l'entraînement |

## Architecture

```text
src/express_delivery/
├── main.py              # CLI generate | etl | train | serve : assemble les dépendances
├── config.py            # configuration (variables d'environnement)
├── abstractions/        # contrats (classes abstraites)
├── domain/              # schémas métier (= contrat OpenAPI) et exceptions
├── data/                # génération (dev), validation ETL et applicative, nettoyage, silver / gold
├── ml/                  # entraînement et prédiction
├── services/            # cas d'usage : ETL médaillon, pipeline d'entraînement, collecte des commandes
├── infrastructure/      # implémentations : MongoDB, fichiers locaux, mémoire, MLflow
└── api/                 # application FastAPI et routes
```

Les services `etl` et `train` sont des jobs ponctuels : ils écrivent le lake puis le modèle versionné dans
des volumes. Le service `api` lit ce modèle et le recharge après chaque réentraînement.

Une classe = une responsabilité (SOLID) ; chaque contrat de `abstractions/` a ses implémentations :

| Contrat | Rôle | Implémentations |
| --- | --- | --- |
| `DataExtractor` | Lire un jeu de commandes | `MongoOrderExtractor` (base ERP, lecture seule), `PolarsFileExtractor` (CSV / gold) |
| `LayerWriter` | Écrire une couche du lake | `ParquetLayerWriter` |
| `OrderStore` | Stocker les commandes de l'API (`OrderRepository` du cours, nom imposé par `Start/openapi.yml`) | `MongoOrderStore`, `InMemoryOrderStore` |
| `ModelRepository` | Sauvegarder / relire le modèle | `FileModelRepository` |

Étapes métier : `RawOrderValidator` (validation ETL), `SilverTransformer`, `GoldTransformer`,
`OrderDataValidator` (validation applicative), `RetrainingPolicy` (faut-il réentraîner ?), `ModelLoader`
(rechargement du modèle par l'API) ; `MedallionEtl` et `TrainingPipeline` ne font qu'enchaîner ces étapes.

## Contribuer

Le projet suit le modèle de branches GitFlow. Voir [CONTRIBUTING.md](CONTRIBUTING.md),
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) et, pour signaler une faille, [SECURITY.md](SECURITY.md).

## Licence

Distribué sous licence MIT, voir [LICENSE](LICENSE).
