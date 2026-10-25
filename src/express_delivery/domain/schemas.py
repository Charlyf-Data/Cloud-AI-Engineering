"""Schémas métier alignés sur le contrat Start/openapi.yml."""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

TARGET_COLUMN = "express_eligible"

NUMERIC_FEATURES = [
    "hour",
    "day_of_week",
    "weekend",
    "distance_km",
    "order_value_eur",
    "weight_kg",
    "stock_available",
    "preparation_time_min",
    "carrier_capacity",
]

CATEGORICAL_FEATURES = ["weather", "delivery_zone", "customer_type"]

FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES

REQUIRED_COLUMNS = ["order_id", "order_date", *FEATURE_COLUMNS, TARGET_COLUMN]


class Weather(str, Enum):
    NORMAL = "normal"
    PLUIE = "pluie"
    NEIGE = "neige"
    ORAGE = "orage"


class DeliveryZone(str, Enum):
    CENTRE = "centre"
    PROCHE_BANLIEUE = "proche_banlieue"
    BANLIEUE = "banlieue"
    RURALE = "rurale"


class CustomerType(str, Enum):
    STANDARD = "standard"
    PREMIUM = "premium"


class OrderFeatures(BaseModel):
    """Caractéristiques d'une commande ; tout champ en trop est refusé."""

    model_config = ConfigDict(extra="forbid")

    order_id: str | None = None
    hour: int = Field(ge=0, le=23)
    day_of_week: int = Field(ge=0, le=6, description="0 = lundi ... 6 = dimanche")
    weekend: Literal[0, 1]
    distance_km: float = Field(ge=0)
    order_value_eur: float = Field(ge=0)
    weight_kg: float = Field(ge=0)
    stock_available: Literal[0, 1]
    preparation_time_min: float = Field(ge=0)
    carrier_capacity: float = Field(ge=0, le=1)
    weather: Weather
    delivery_zone: DeliveryZone
    customer_type: CustomerType

    def to_feature_row(self) -> dict[str, Any]:
        """Retourne uniquement les features du modèle, enums convertis en chaînes."""
        return self.model_dump(mode="json", include=set(FEATURE_COLUMNS))


class Prediction(BaseModel):
    """Résultat d'une prédiction (schéma Prediction du contrat)."""

    model_config = ConfigDict(protected_namespaces=())

    order_id: str
    express_eligible: bool
    decision: Literal["oui", "non"]
    probability: float = Field(ge=0, le=1)
    model_version: str
    predicted_at: datetime
    latency_ms: float | None = None


@dataclass(frozen=True)
class ModelBundle:
    """Pipeline entraîné et ses métadonnées."""

    pipeline: Any
    model_version: str
    trained_at: datetime
    metrics: dict[str, float]


def new_order_id() -> str:
    """Génère un identifiant de commande côté serveur."""
    return f"CMD-{uuid4().hex[:12].upper()}"
