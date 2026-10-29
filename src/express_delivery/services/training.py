"""Cas d'usage : entraînement de bout en bout."""
import logging

from express_delivery.abstractions.data import DataExtractor
from express_delivery.abstractions.model import ExperimentTracker, ModelRepository
from express_delivery.data.cleaner import OrderDataCleaner
from express_delivery.data.validator import OrderDataValidator
from express_delivery.domain.schemas import ModelBundle
from express_delivery.ml.trainer import ModelTrainer
from express_delivery.services.retraining_policy import RetrainingPolicy

logger = logging.getLogger(__name__)


class TrainingPipeline:
    """extract -> contrôle des colonnes -> nettoyage -> validation -> [règle de réentraînement]
    -> entraînement -> suivi -> sauvegarde."""

    def __init__(
        self,
        extractor: DataExtractor,
        validator: OrderDataValidator,
        cleaner: OrderDataCleaner,
        trainer: ModelTrainer,
        tracker: ExperimentTracker,
        repository: ModelRepository,
        policy: RetrainingPolicy | None = None,
    ) -> None:
        self._extractor = extractor
        self._validator = validator
        self._cleaner = cleaner
        self._trainer = trainer
        self._tracker = tracker
        self._repository = repository
        self._policy = policy

    def run(self) -> ModelBundle | None:
        """Exécute le pipeline et retourne le modèle entraîné ; None si l'entraînement est ignoré."""
        raw = self._extractor.extract()
        self._validator.check_columns(raw)
        orders = self._cleaner.clean(raw)
        self._validator.validate(orders)
        logger.info("Données prêtes", extra={"context": {"raw_rows": raw.height, "clean_rows": orders.height}})

        if self._policy and not self._policy.should_train(orders.height):
            context = {"new_orders": self._policy.new_orders(orders.height)}
            logger.info("Entraînement ignoré : pas assez de nouvelles commandes", extra={"context": context})
            return None

        bundle = self._trainer.train(orders)
        self._tracker.track(self._trainer.params(), bundle.metrics, bundle.pipeline)
        self._repository.save(bundle)
        logger.info(
            "Modèle entraîné et sauvegardé",
            extra={"context": {"model_version": bundle.model_version, "metrics": bundle.metrics}},
        )
        return bundle
