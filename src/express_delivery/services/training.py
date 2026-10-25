"""Cas d'usage : entraînement de bout en bout."""
import logging

from express_delivery.abstractions.data import DataExtractor
from express_delivery.abstractions.model import ExperimentTracker, ModelRepository
from express_delivery.data.cleaner import OrderDataCleaner
from express_delivery.data.validator import OrderDataValidator
from express_delivery.domain.schemas import ModelBundle
from express_delivery.ml.trainer import ModelTrainer

logger = logging.getLogger(__name__)


class TrainingPipeline:
    """extract -> contrôle des colonnes -> nettoyage -> validation -> entraînement -> suivi -> sauvegarde."""

    def __init__(
        self,
        extractor: DataExtractor,
        validator: OrderDataValidator,
        cleaner: OrderDataCleaner,
        trainer: ModelTrainer,
        tracker: ExperimentTracker,
        repository: ModelRepository,
    ) -> None:
        self._extractor = extractor
        self._validator = validator
        self._cleaner = cleaner
        self._trainer = trainer
        self._tracker = tracker
        self._repository = repository

    def run(self) -> ModelBundle:
        raw = self._extractor.extract()
        self._validator.check_columns(raw)
        orders = self._cleaner.clean(raw)
        self._validator.validate(orders)
        logger.info("Données prêtes", extra={"context": {"raw_rows": raw.height, "clean_rows": orders.height}})

        bundle = self._trainer.train(orders)
        self._tracker.track(self._trainer.params(), bundle.metrics, bundle.pipeline)
        self._repository.save(bundle)
        logger.info(
            "Modèle entraîné et sauvegardé",
            extra={"context": {"model_version": bundle.model_version, "metrics": bundle.metrics}},
        )
        return bundle
