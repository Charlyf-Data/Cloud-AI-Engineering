"""Lecture des commandes ERP dans MongoDB, la base analytique (ADR 001)."""
import polars as pl
from pymongo import MongoClient

from express_delivery.abstractions.data import DataExtractor


class MongoOrderExtractor(DataExtractor):
    """Lit toute la collection, en lecture seule, telle que l'ETL de l'ERP l'a écrite."""

    def __init__(self, uri: str, database: str, collection: str) -> None:
        self._collection = MongoClient(uri, serverSelectionTimeoutMS=5000)[database][collection]

    def extract(self) -> pl.DataFrame:
        documents = list(self._collection.find({}, {"_id": 0}))
        return pl.DataFrame(documents, infer_schema_length=None)
