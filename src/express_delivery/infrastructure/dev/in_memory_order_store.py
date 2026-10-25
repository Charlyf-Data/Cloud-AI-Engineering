"""Stockage des commandes en mémoire du processus (séance 1)."""
from threading import Lock

from express_delivery.abstractions.storage import OrderStore
from express_delivery.domain.schemas import OrderFeatures


class InMemoryOrderStore(OrderStore):
    """Dictionnaire protégé par un verrou ; les données sont perdues au redémarrage."""

    def __init__(self) -> None:
        self._orders: dict[str, OrderFeatures] = {}
        self._lock = Lock()

    def save(self, order: OrderFeatures) -> None:
        with self._lock:
            self._orders[order.order_id] = order

    def get(self, order_id: str) -> OrderFeatures | None:
        with self._lock:
            return self._orders.get(order_id)

    def is_reachable(self) -> bool:
        return True
