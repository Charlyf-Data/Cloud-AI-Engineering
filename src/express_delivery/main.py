"""Point d'entrée : config, logging, assemblage des dépendances, lancement.

    python -m express_delivery.main generate   # dev : génère le CSV synthétique
    python -m express_delivery.main etl        # MongoDB -> lake raw / silver / gold
    python -m express_delivery.main train      # job d'entraînement -> artefacts
    python -m express_delivery.main serve      # API (charge les artefacts)
"""
import argparse
import logging
import sys

import uvicorn

from express_delivery.abstractions.model import ExperimentTracker
from express_delivery.abstractions.storage import OrderStore
from express_delivery.api.app import ApiFactory
from express_delivery.config import Settings
from express_delivery.data.cleaner import OrderDataCleaner
from express_delivery.data.generator import OrderDataGenerator
from express_delivery.data.gold_transformer import GoldTransformer
from express_delivery.data.raw_validator import RawOrderValidator
from express_delivery.data.silver_transformer import SilverTransformer
from express_delivery.data.validator import OrderDataValidator
from express_delivery.infrastructure.dev.file_model_repository import FileModelRepository
from express_delivery.infrastructure.dev.in_memory_order_store import InMemoryOrderStore
from express_delivery.infrastructure.dev.parquet_layer_writer import ParquetLayerWriter
from express_delivery.infrastructure.dev.polars_file_extractor import PolarsFileExtractor
from express_delivery.infrastructure.mongo_order_extractor import MongoOrderExtractor
from express_delivery.infrastructure.mongo_order_store import MongoOrderStore
from express_delivery.infrastructure.tracking import MlflowTracker, NoOpTracker
from express_delivery.logging_config import configure_logging
from express_delivery.ml.trainer import ModelTrainer
from express_delivery.services.etl import MedallionEtl
from express_delivery.services.retraining_policy import RetrainingPolicy
from express_delivery.services.training import TrainingPipeline

logger = logging.getLogger("express_delivery")


class Application:
    """Instancie les implémentations concrètes et les injecte."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def generate(self) -> None:
        """Génère le jeu de données synthétique (environnement de dev)."""
        orders = OrderDataGenerator(self._settings.n_rows, self._settings.random_state).generate()
        self._settings.data_path.parent.mkdir(parents=True, exist_ok=True)
        orders.write_csv(self._settings.data_path)
        context = {"path": str(self._settings.data_path), "rows": orders.height}
        logger.info("Jeu de données généré", extra={"context": context})

    def etl(self) -> None:
        """Copie la base analytique dans le lake puis produit les couches silver et gold."""
        if not self._settings.mongo_uri:
            raise ValueError("MONGO_URI est requis pour l'ETL.")
        MedallionEtl(
            source=MongoOrderExtractor(
                self._settings.mongo_uri, self._settings.mongo_database, self._settings.mongo_erp_collection
            ),
            validator=RawOrderValidator(),
            silver=SilverTransformer(),
            gold=GoldTransformer(self._settings.random_state),
            writer=ParquetLayerWriter(self._settings.lake_dir),
        ).run()

    def train(self) -> None:
        """Entraîne le modèle et sauvegarde les artefacts."""
        TrainingPipeline(
            extractor=PolarsFileExtractor(self._settings.data_path),
            validator=OrderDataValidator(),
            cleaner=OrderDataCleaner(),
            trainer=ModelTrainer(self._settings.test_size, self._settings.random_state, self._settings.model_version),
            tracker=self._tracker(),
            repository=self._repository(),
            policy=RetrainingPolicy(self._repository(), self._settings.retrain_min_new_orders),
        ).run()

    def serve(self) -> None:
        """Démarre l'API."""
        app = ApiFactory(self._settings, self._order_store(), self._repository()).create()
        uvicorn.run(app, host=self._settings.api_host, port=self._settings.api_port, log_config=None)

    def _order_store(self) -> OrderStore:
        """Commandes reçues par l'API : collection dédiée, séparée des données de l'ERP."""
        if self._settings.mongo_uri:
            return MongoOrderStore(
                self._settings.mongo_uri, self._settings.mongo_database, self._settings.mongo_api_collection
            )
        return InMemoryOrderStore()

    def _repository(self) -> FileModelRepository:
        return FileModelRepository(self._settings.artifacts_dir, self._settings.model_version)

    def _tracker(self) -> ExperimentTracker:
        if self._settings.mlflow_tracking_uri:
            return MlflowTracker(self._settings.mlflow_tracking_uri, self._settings.mlflow_experiment)
        return NoOpTracker()


def main() -> None:
    """Analyse la commande CLI, configure le logging et exécute la commande."""
    parser = argparse.ArgumentParser(prog="express_delivery")
    parser.add_argument("command", choices=["generate", "etl", "train", "serve"])
    command = parser.parse_args().command

    settings = Settings()
    configure_logging(settings.log_level)
    logger.info("Démarrage", extra={"context": {"command": command, "env": settings.app_env}})

    try:
        getattr(Application(settings), command)()
    except Exception:  # pylint: disable=broad-exception-caught  # point unique de gestion des erreurs
        logger.exception("Échec de la commande", extra={"context": {"command": command}})
        sys.exit(1)


if __name__ == "__main__":
    main()
