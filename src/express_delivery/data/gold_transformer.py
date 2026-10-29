"""Couche gold : jeu d'entraînement prêt pour le modèle."""
import numpy as np
import polars as pl

from express_delivery.data.generator import OrderDataGenerator
from express_delivery.domain.schemas import REQUIRED_COLUMNS, TARGET_COLUMN


class GoldTransformer:
    """Garde les commandes complètes, ajoute la cible et ne conserve que les colonnes du modèle."""

    def __init__(self, random_state: int) -> None:
        self._random_state = random_state

    def transform(self, silver: pl.DataFrame) -> pl.DataFrame:
        """Retourne la couche gold à partir de la couche silver."""
        complete = silver.drop_nulls(subset=["weekend", "preparation_time_min"])
        if TARGET_COLUMN not in complete.columns:
            # L'ERP ne remonte pas le résultat de livraison : il est simulé avec la règle métier du générateur.
            complete = OrderDataGenerator.add_target(complete, np.random.default_rng(self._random_state))
        return complete.select(REQUIRED_COLUMNS)
