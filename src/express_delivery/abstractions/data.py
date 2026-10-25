"""Contrat d'accès aux données."""
from abc import ABC, abstractmethod

import polars as pl


class DataExtractor(ABC):
    """Lit un jeu de commandes brut."""

    @abstractmethod
    def extract(self) -> pl.DataFrame:
        """Retourne les commandes."""
