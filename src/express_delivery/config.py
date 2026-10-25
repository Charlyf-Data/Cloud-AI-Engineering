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

    data_path: Path = Path("data/orders_dataset.csv")
    artifacts_dir: Path = Path("artifacts")
    model_version: str = "1.0.0"
    prediction_threshold: float = Field(default=0.5, ge=0, le=1)

    n_rows: int = Field(default=6000, gt=0)
    random_state: int = 42
    test_size: float = Field(default=0.2, gt=0, lt=1)

    mlflow_tracking_uri: str | None = None
    mlflow_experiment: str = "livraison-express"

    api_host: str = "0.0.0.0"
    api_port: int = 8000
