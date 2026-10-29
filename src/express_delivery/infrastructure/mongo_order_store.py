"""Stockage des commandes reçues par l'API dans MongoDB (collection dédiée, ADR 001)."""
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from express_delivery.abstractions.storage import OrderStore
from express_delivery.domain.schemas import OrderFeatures


class MongoOrderStore(OrderStore):
    """Une collection MongoDB ; les documents sont indexés par order_id."""

    def __init__(self, uri: str, database: str, collection: str) -> None:
        self._client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        self._collection = self._client[database][collection]

    def save(self, order: OrderFeatures) -> None:
        self._collection.replace_one({"order_id": order.order_id}, order.model_dump(mode="json"), upsert=True)

    def get(self, order_id: str) -> OrderFeatures | None:
        document = self._collection.find_one({"order_id": order_id}, {"_id": 0})
        return OrderFeatures(**document) if document else None

    def is_reachable(self) -> bool:
        try:
            self._client.admin.command("ping")
            return True
        except PyMongoError:
            return False
