"""Cas d'usage : collecte des commandes et prédiction asynchrone."""
import logging

from express_delivery.abstractions.storage import OrderStore
from express_delivery.domain.exceptions import OrderNotFoundError
from express_delivery.domain.schemas import OrderFeatures, new_order_id
from express_delivery.ml.predictor import EligibilityPredictor

logger = logging.getLogger(__name__)


class OrderService:
    """Attribue un identifiant, persiste la commande et calcule sa prédiction en différé."""

    def __init__(self, store: OrderStore, predictor: EligibilityPredictor | None) -> None:
        self._store = store
        self._predictor = predictor

    def submit(self, order: OrderFeatures) -> str:
        """Enregistre la commande et retourne son identifiant."""
        order_id = order.order_id or new_order_id()
        self._store.save(order.model_copy(update={"order_id": order_id}))
        return order_id

    def get(self, order_id: str) -> OrderFeatures:
        """Relit une commande ; lève OrderNotFoundError si elle est inconnue."""
        order = self._store.get(order_id)
        if order is None:
            raise OrderNotFoundError(f"Commande inconnue : {order_id}")
        return order

    def predict_stored(self, order_id: str) -> None:
        """Tâche de fond : prédit une commande déjà enregistrée et journalise le résultat."""
        if self._predictor is None:
            logger.warning(
                "Prédiction différée ignorée : modèle indisponible", extra={"context": {"order_id": order_id}}
            )
            return
        prediction = self._predictor.predict(self.get(order_id), order_id)
        logger.info("Prédiction différée calculée", extra={"context": prediction.model_dump(mode="json")})
