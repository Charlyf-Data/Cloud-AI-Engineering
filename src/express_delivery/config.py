"""Configuration unique, lue depuis les variables d'environnement ou un fichier .env."""
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Paramètres de l'application ; chaque environnement (dev, test, prod) fournit ses valeurs."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", protected_namespaces=())

    app_env: str = "dev"
    service_name: str = "eligibilite-livraison-express"
    log_level: str = "INFO"

    # Jeu d'entraînement : CSV synthétique en dev, couche gold du lake (lake/gold/orders.parquet) en test/prod.
    data_path: Path = Path("data/orders_dataset.csv")
    lake_dir: Path = Path("lake")
    artifacts_dir: Path = Path("artifacts")
    model_version: str = "1.0.0"
    prediction_threshold: float = Field(default=0.5, ge=0, le=1)

    n_rows: int = Field(default=6000, gt=0)
    random_state: int = 42
    test_size: float = Field(default=0.2, gt=0, lt=1)

    # Base analytique : source de l'ETL et stockage des commandes de l'API ; sans MONGO_URI, stockage en mémoire.
    mongo_uri: str | None = None
    mongo_database: str = "livraison_express"
    mongo_erp_collection: str = "orders"
    mongo_api_collection: str = "api_orders"

    # Réentraînement planifié (Airflow) : ignoré tant qu'il n'y a pas assez de nouvelles commandes.
    retrain_min_new_orders: int = Field(default=0, ge=0)
    # Période de rechargement du modèle par l'API ; 0 désactive.
    model_refresh_seconds: int = Field(default=60, ge=0)

    mlflow_tracking_uri: str | None = None
    mlflow_experiment: str = "livraison-express"

    api_host: str = "0.0.0.0"
    api_port: int = 8000
