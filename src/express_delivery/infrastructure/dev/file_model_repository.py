"""Stockage du modèle dans un répertoire local, un sous-dossier par version."""
import json
from datetime import datetime
from pathlib import Path

import joblib

from express_delivery.abstractions.model import ModelRepository
from express_delivery.domain.exceptions import ModelNotLoadedError
from express_delivery.domain.schemas import (
    CATEGORICAL_FEATURES,
    FEATURE_COLUMNS,
    NUMERIC_FEATURES,
    TARGET_COLUMN,
    ModelBundle,
)


class FileModelRepository(ModelRepository):
    """artifacts/<version>/model.joblib + metadata.json."""

    _MODEL_FILE = "model.joblib"
    _METADATA_FILE = "metadata.json"

    def __init__(self, artifacts_dir: Path, model_version: str) -> None:
        self._directory = artifacts_dir / model_version

    def save(self, bundle: ModelBundle) -> None:
        self._directory.mkdir(parents=True, exist_ok=True)
        joblib.dump(bundle.pipeline, self._directory / self._MODEL_FILE)
        metadata = {
            "model_version": bundle.model_version,
            "trained_at": bundle.trained_at.isoformat(),
            "target": TARGET_COLUMN,
            "features": FEATURE_COLUMNS,
            "numeric_features": NUMERIC_FEATURES,
            "categorical_features": CATEGORICAL_FEATURES,
            "metrics": bundle.metrics,
        }
        (self._directory / self._METADATA_FILE).write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    def load(self) -> ModelBundle:
        model_path = self._directory / self._MODEL_FILE
        metadata_path = self._directory / self._METADATA_FILE
        if not model_path.exists() or not metadata_path.exists():
            raise ModelNotLoadedError(f"Aucun modèle trouvé dans {self._directory}")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        return ModelBundle(
            pipeline=joblib.load(model_path),
            model_version=metadata["model_version"],
            trained_at=datetime.fromisoformat(metadata["trained_at"]),
            metrics=metadata["metrics"],
        )
