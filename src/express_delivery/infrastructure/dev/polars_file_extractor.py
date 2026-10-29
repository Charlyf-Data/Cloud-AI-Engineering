"""Lecture d'un CSV de commandes avec Polars."""
from pathlib import Path

import polars as pl

from express_delivery.abstractions.data import DataExtractor


class PolarsCsvExtractor(DataExtractor):
    """Charge les commandes depuis un fichier CSV local."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def extract(self) -> pl.DataFrame:
        if not self._path.exists():
            raise FileNotFoundError(f"Le fichier {self._path} n'existe pas.")
        return pl.read_csv(self._path, try_parse_dates=True)
