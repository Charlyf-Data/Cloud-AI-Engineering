"""Contrats d'accès aux données."""
from abc import ABC, abstractmethod

import polars as pl


class DataExtractor(ABC):
    """Lit un jeu de commandes brut."""

    @abstractmethod
    def extract(self) -> pl.DataFrame:
        """Retourne les commandes."""


class LayerWriter(ABC):
    """Persiste une couche du lake (raw, rejected, silver, gold)."""

    @abstractmethod
    def write(self, layer: str, df: pl.DataFrame) -> None:
        """Remplace le contenu de la couche."""
