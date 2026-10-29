# Cloud-AI-Engineering — Éligibilité à la livraison express

Service de machine learning qui prédit si une commande peut être livrée en express (dans la journée).
Il transforme le notebook expérimental `Start/project_test_v1_final_final2.ipynb` en une application Python
exposée par une API FastAPI et conteneurisée avec Docker. Le contrat de l'API est `Start/openapi.yml`.

> Le modèle est une aide à la décision : il ne remplace pas les règles métier. Il est entraîné sur des
> données synthétiques, ses réponses reflètent donc la simulation et non la réalité.

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
# {"order_id":"CMD-...","express_eligible":true,"decision":"oui","probability":0.9377,"model_version":"1.0.0",...}
```

Arrêt : `docker compose down` (le modèle est conservé dans le volume `artifacts`).

## Démarrage en local

Prérequis : Python 3.11. Les commandes se lancent depuis la racine du projet, dans cet ordre.

```bash
pip install -r requirements-train.txt
export PYTHONPATH=src                       # PowerShell : $env:PYTHONPATH = "src"
python -m express_delivery.main generate    # crée data/orders_dataset.csv (données synthétiques)
python -m express_delivery.main train       # entraîne et écrit artifacts/<MODEL_VERSION>/
python -m express_delivery.main serve       # démarre l'API
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
| `MODEL_VERSION` | `1.0.0` | Version du modèle entraîné et chargé |
| `PREDICTION_THRESHOLD` | `0.5` | Seuil de décision oui/non |
| `API_PORT` | `8000` | Port de l'API |
| `N_ROWS` / `RANDOM_STATE` / `TEST_SIZE` | `6000` / `42` / `0.2` | Paramètres de génération et d'entraînement |
| `MLFLOW_TRACKING_URI` | vide | Active le suivi MLflow de l'entraînement |

## Architecture

```text
src/express_delivery/
├── main.py              # CLI generate | train | serve : assemble les dépendances
├── config.py            # configuration (variables d'environnement)
├── abstractions/        # contrats (classes abstraites)
├── domain/              # schémas métier (= contrat OpenAPI) et exceptions
├── data/                # génération (dev), validation, nettoyage
├── ml/                  # entraînement et prédiction
├── services/            # cas d'usage : pipeline d'entraînement, collecte des commandes
├── infrastructure/      # implémentations : fichiers locaux, mémoire, MLflow
└── api/                 # application FastAPI et routes
```

Le service `train` de `docker-compose.yml` est un job ponctuel qui écrit le modèle versionné dans un volume.
Le service `api` relit ce modèle à chaque démarrage, sans réentraîner.

## Contribuer

Le projet suit le modèle de branches GitFlow. Voir [CONTRIBUTING.md](CONTRIBUTING.md),
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) et, pour signaler une faille, [SECURITY.md](SECURITY.md).

## Licence

Distribué sous licence MIT, voir [LICENSE](LICENSE).
