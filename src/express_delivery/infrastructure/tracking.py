"""Suivi des entraînements."""
from typing import Any

from express_delivery.abstractions.model import ExperimentTracker


class MlflowTracker(ExperimentTracker):
    """Enregistre le run dans MLflow."""

    def __init__(self, tracking_uri: str, experiment_name: str) -> None:
        self._tracking_uri = tracking_uri
        self._experiment_name = experiment_name

    def track(self, params: dict[str, Any], metrics: dict[str, float], model: Any) -> None:
        # Import local : mlflow n'est installé que dans l'image d'entraînement.
        import mlflow  # pylint: disable=import-outside-toplevel,import-error
        import mlflow.sklearn  # pylint: disable=import-outside-toplevel,import-error

        mlflow.set_tracking_uri(self._tracking_uri)
        mlflow.set_experiment(self._experiment_name)
        with mlflow.start_run():
            mlflow.log_params(params)
            mlflow.log_metrics(metrics)
            mlflow.sklearn.log_model(model, name="model", serialization_format="cloudpickle")


class NoOpTracker(ExperimentTracker):
    """Utilisé quand aucun serveur de tracking n'est configuré."""

    def track(self, params: dict[str, Any], metrics: dict[str, float], model: Any) -> None:
        return None
