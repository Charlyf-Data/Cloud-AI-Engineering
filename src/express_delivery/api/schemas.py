"""Schémas HTTP propres à l'API (contrat Start/openapi.yml)."""
from typing import Literal

from pydantic import BaseModel


class OrderAccepted(BaseModel):
    order_id: str
    status: Literal["accepted"] = "accepted"


class HealthStatus(BaseModel):
    status: Literal["ok"] = "ok"
    service: str
    version: str


class ReadinessStatus(BaseModel):
    status: Literal["ready", "not_ready"]
    checks: dict[str, str]
    version: str | None = None


class ErrorResponse(BaseModel):
    error: str
    message: str
    details: list[str] | None = None
