"""Exceptions métier, traduites en réponses HTTP par la couche API."""


class ExpressDeliveryError(Exception):
    """Racine des erreurs applicatives."""


class DataValidationError(ExpressDeliveryError):
    """Jeu de données invalide."""


class ModelNotLoadedError(ExpressDeliveryError):
    """Modèle indisponible."""


class OrderNotFoundError(ExpressDeliveryError):
    """Commande inconnue."""
