"""Chargement du modèle dans l'état de l'application."""
import logging
from datetime import datetime

from starlette.datastructures import State

from express_delivery.abstractions.model import ModelRepository
from express_delivery.abstractions.storage import OrderStore
from express_delivery.domain.exceptions import ModelNotLoadedError
from express_delivery.ml.predictor import EligibilityPredictor
from express_delivery.services.orders import OrderService

logger = logging.getLogger(__name__)


class ModelLoader:
    """Installe le prédicteur du dernier modèle entraîné ; ne fait rien si le modèle n'a pas changé."""

    def __init__(self, repository: ModelRepository, store: OrderStore, threshold: float) -> None:
        self._repository = repository
        self._store = store
        self._threshold = threshold
        self._trained_at: datetime | None = None

    def load(self, state: State) -> None:
        """Sans modèle disponible, l'API reste démarrée mais n'est pas prête."""
        try:
            bundle = self._repository.load()
        except ModelNotLoadedError as error:
            if self._trained_at is None:
                logger.warning(str(error))
                state.predictor = None
                state.order_service = OrderService(self._store, None)
            return
        if bundle.trained_at == self._trained_at:
            return
        predictor = EligibilityPredictor(bundle, self._threshold)
        state.predictor = predictor
        state.order_service = OrderService(self._store, predictor)
        self._trained_at = bundle.trained_at
        context = {"model_version": bundle.model_version, "trained_at": bundle.trained_at.isoformat()}
        logger.info("Modèle chargé", extra={"context": context})
