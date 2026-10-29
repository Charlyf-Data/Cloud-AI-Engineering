"""Règle de réentraînement : seulement si assez de nouvelles commandes sont arrivées."""
from express_delivery.abstractions.model import ModelRepository
from express_delivery.domain.exceptions import ModelNotLoadedError


class RetrainingPolicy:
    """Compare le jeu d'entraînement au modèle en place ; min_new_orders = 0 réentraîne toujours."""

    def __init__(self, repository: ModelRepository, min_new_orders: int) -> None:
        self._repository = repository
        self._min_new_orders = min_new_orders

    def new_orders(self, rows: int) -> int:
        """Nombre de commandes en plus depuis le modèle en place (toutes s'il n'y en a pas)."""
        try:
            return rows - self._repository.load().training_rows
        except ModelNotLoadedError:
            return rows

    def should_train(self, rows: int) -> bool:
        """True si le jeu de `rows` lignes justifie un nouvel entraînement."""
        return not self._min_new_orders or self.new_orders(rows) >= self._min_new_orders
