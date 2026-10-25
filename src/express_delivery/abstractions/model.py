"""Contrats de persistance et de suivi du modèle."""
from abc import ABC, abstractmethod
from typing import Any

from express_delivery.domain.schemas import ModelBundle


class ModelRepository(ABC):
    """Sauvegarde et recharge un modèle entraîné avec ses métadonnées."""

    @abstractmethod
    def save(self, bundle: ModelBundle) -> None:
        """Persiste le bundle."""

    @abstractmethod
    def load(self) -> ModelBundle:
        """Recharge le bundle ; lève ModelNotLoadedError s'il est absent."""


class ExperimentTracker(ABC):
    """Trace un run d'entraînement."""

    @abstractmethod
    def track(self, params: dict[str, Any], metrics: dict[str, float], model: Any) -> None:
        """Enregistre paramètres, métriques et modèle."""
