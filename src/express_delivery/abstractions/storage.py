"""Contrat de stockage des commandes collectées."""
from abc import ABC, abstractmethod

from express_delivery.domain.schemas import OrderFeatures


class OrderStore(ABC):
    """Persiste et relit les commandes."""

    @abstractmethod
    def save(self, order: OrderFeatures) -> None:
        """Enregistre une commande (order_id renseigné)."""

    @abstractmethod
    def get(self, order_id: str) -> OrderFeatures | None:
        """Relit une commande ; None si inconnue."""

    @abstractmethod
    def is_reachable(self) -> bool:
        """Indique si le stockage répond."""
