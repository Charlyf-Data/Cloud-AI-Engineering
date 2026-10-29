"""Fixtures partagées : petit jeu de données, modèle entraîné et clients API."""
from collections.abc import Iterator
from pathlib import Path

import polars as pl
import pytest
from fastapi.testclient import TestClient

from express_delivery.api.app import ApiFactory
from express_delivery.config import Settings
from express_delivery.data.generator import OrderDataGenerator
from express_delivery.domain.schemas import ModelBundle
from express_delivery.infrastructure.dev.file_model_repository import FileModelRepository
from express_delivery.infrastructure.dev.in_memory_order_store import InMemoryOrderStore
from express_delivery.ml.trainer import ModelTrainer

MODEL_VERSION = "test"


@pytest.fixture(scope="session")
def orders() -> pl.DataFrame:
    """Jeu de commandes synthétiques réduit pour des tests rapides."""
    return OrderDataGenerator(n_rows=500, random_state=42).generate()


@pytest.fixture(scope="session")
def bundle(orders: pl.DataFrame) -> ModelBundle:
    """Modèle entraîné une seule fois pour toute la session."""
    return ModelTrainer(test_size=0.2, random_state=42, model_version=MODEL_VERSION).train(orders)


@pytest.fixture(scope="session")
def artifacts_dir(bundle: ModelBundle, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Répertoire d'artefacts contenant le modèle de test."""
    directory = tmp_path_factory.mktemp("artifacts")
    FileModelRepository(directory, MODEL_VERSION).save(bundle)
    return directory


@pytest.fixture
def valid_order() -> dict:
    """Commande valide, identique à l'exemple du notebook."""
    return {
        "hour": 14,
        "day_of_week": 2,
        "weekend": 0,
        "distance_km": 3.5,
        "order_value_eur": 89.9,
        "weight_kg": 2.4,
        "stock_available": 1,
        "preparation_time_min": 18,
        "carrier_capacity": 0.85,
        "weather": "normal",
        "delivery_zone": "centre",
        "customer_type": "premium",
    }


def _client(artifacts_dir: Path, model_version: str) -> Iterator[TestClient]:
    settings = Settings(artifacts_dir=artifacts_dir, model_version=model_version, _env_file=None)
    repository = FileModelRepository(artifacts_dir, model_version)
    with TestClient(ApiFactory(settings, InMemoryOrderStore(), repository).create()) as client:
        yield client


@pytest.fixture
def client(artifacts_dir: Path) -> Iterator[TestClient]:
    """API avec un modèle chargé."""
    yield from _client(artifacts_dir, MODEL_VERSION)


@pytest.fixture
def client_without_model(tmp_path: Path) -> Iterator[TestClient]:
    """API démarrée sans modèle disponible."""
    yield from _client(tmp_path, "absent")
