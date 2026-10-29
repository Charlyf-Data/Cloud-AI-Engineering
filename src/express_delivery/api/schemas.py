"""Schémas HTTP propres à l'API (contrat Start/openapi.yml)."""
from typing import Literal

from pydantic import BaseModel


class OrderAccepted(BaseModel):
    """Accusé de réception d'une commande."""

    order_id: str
    status: Literal["accepted"] = "accepted"


class HealthStatus(BaseModel):
    """Réponse de la sonde de vivacité."""

    status: Literal["ok"] = "ok"
    service: str
    version: str


class ReadinessStatus(BaseModel):
    """Réponse de la sonde de disponibilité."""

    status: Literal["ready", "not_ready"]
    checks: dict[str, str]
    version: str | None = None


class ErrorResponse(BaseModel):
    """Erreur au format du contrat : code stable, message humain, détails."""

    error: str
    message: str
    details: list[str] | None = None
