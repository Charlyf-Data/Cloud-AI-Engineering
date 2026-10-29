"""Tests de l'entraînement, de la prédiction et de la persistance du modèle."""
from pathlib import Path

import pytest

from express_delivery.domain.exceptions import ModelNotLoadedError
from express_delivery.domain.schemas import ModelBundle, OrderFeatures
from express_delivery.infrastructure.dev.file_model_repository import FileModelRepository
from express_delivery.ml.predictor import EligibilityPredictor

from conftest import MODEL_VERSION


def test_trainer_returns_metrics(bundle: ModelBundle) -> None:
    assert set(bundle.metrics) == {"accuracy", "precision", "recall", "f1_score", "roc_auc"}
    assert all(0 <= value <= 1 for value in bundle.metrics.values())
    assert bundle.model_version == MODEL_VERSION


def test_prediction_matches_threshold(bundle: ModelBundle, valid_order: dict) -> None:
    order = OrderFeatures(**valid_order)
    prediction = EligibilityPredictor(bundle, threshold=0.5).predict(order, "CMD-1")
    assert prediction.order_id == "CMD-1"
    assert 0 <= prediction.probability <= 1
    assert prediction.express_eligible == (prediction.probability >= 0.5)
    assert prediction.decision == ("oui" if prediction.express_eligible else "non")


@pytest.mark.parametrize(("threshold", "expected"), [(0.0, "oui"), (1.01, "non")])
def test_threshold_drives_decision(bundle: ModelBundle, valid_order: dict, threshold: float, expected: str) -> None:
    prediction = EligibilityPredictor(bundle, threshold=threshold).predict(OrderFeatures(**valid_order), "CMD-1")
    assert prediction.decision == expected


def test_repository_round_trip(bundle: ModelBundle, tmp_path: Path) -> None:
    repository = FileModelRepository(tmp_path, MODEL_VERSION)
    repository.save(bundle)
    loaded = repository.load()
    assert loaded.model_version == bundle.model_version
    assert loaded.metrics == bundle.metrics


def test_repository_without_model(tmp_path: Path) -> None:
    with pytest.raises(ModelNotLoadedError):
        FileModelRepository(tmp_path, "absent").load()
