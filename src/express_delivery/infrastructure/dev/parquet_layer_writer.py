"""Écriture des couches du lake en Parquet : <lake_dir>/<couche>/orders.parquet."""
from pathlib import Path

import polars as pl

from express_delivery.abstractions.data import LayerWriter


class ParquetLayerWriter(LayerWriter):
    """Écrit dans un fichier temporaire puis le renomme : jamais de couche à moitié écrite."""

    _FILE = "orders.parquet"

    def __init__(self, lake_dir: Path) -> None:
        self._lake_dir = lake_dir

    def write(self, layer: str, df: pl.DataFrame) -> None:
        directory = self._lake_dir / layer
        directory.mkdir(parents=True, exist_ok=True)
        temporary = directory / f"{self._FILE}.tmp"
        df.write_parquet(temporary)
        temporary.replace(directory / self._FILE)
