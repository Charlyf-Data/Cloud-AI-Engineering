"""Lecture d'un fichier de commandes (CSV ou Parquet) avec Polars."""
from pathlib import Path

import polars as pl

from express_delivery.abstractions.data import DataExtractor


class PolarsFileExtractor(DataExtractor):
    """Charge les commandes depuis un CSV local (dev) ou la couche gold Parquet."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def extract(self) -> pl.DataFrame:
        if not self._path.exists():
            raise FileNotFoundError(f"Le fichier {self._path} n'existe pas.")
        if self._path.suffix == ".parquet":
            return pl.read_parquet(self._path)
        return pl.read_csv(self._path, try_parse_dates=True)
