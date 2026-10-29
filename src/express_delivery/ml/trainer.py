"""Construction, entraînement et évaluation du pipeline."""
from datetime import datetime, timezone
from typing import Any

import numpy as np
import polars as pl
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from express_delivery.domain.schemas import (
    CATEGORICAL_FEATURES,
    FEATURE_COLUMNS,
    NUMERIC_FEATURES,
    TARGET_COLUMN,
    ModelBundle,
)


class ModelTrainer:
    """Entraîne une régression logistique et retourne un ModelBundle évalué."""

    def __init__(self, test_size: float, random_state: int, model_version: str) -> None:
        self._test_size = test_size
        self._random_state = random_state
        self._model_version = model_version

    def train(self, df: pl.DataFrame) -> ModelBundle:
        """Split stratifié, fit et calcul des métriques sur le jeu de test."""
        x = df.select(FEATURE_COLUMNS)
        y = df[TARGET_COLUMN].to_numpy()
        x_train, x_test, y_train, y_test = train_test_split(
            x, y, test_size=self._test_size, random_state=self._random_state, stratify=y
        )
        pipeline = self._build_pipeline()
        pipeline.fit(x_train, y_train)
        return ModelBundle(
            pipeline=pipeline,
            model_version=self._model_version,
            trained_at=datetime.now(timezone.utc),
            metrics=self._evaluate(pipeline, x_test, y_test),
            training_rows=df.height,
        )

    def params(self) -> dict[str, Any]:
        """Paramètres à tracer avec le run."""
        return {
            "model_type": "LogisticRegression",
            "random_state": self._random_state,
            "test_size": self._test_size,
            "feature_count": len(FEATURE_COLUMNS),
        }

    def _build_pipeline(self) -> Pipeline:
        numeric = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ])
        categorical = Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ])
        preprocessor = ColumnTransformer([
            ("numeric", numeric, NUMERIC_FEATURES),
            ("categorical", categorical, CATEGORICAL_FEATURES),
        ])
        classifier = LogisticRegression(
            max_iter=1000, class_weight="balanced", random_state=self._random_state
        )
        return Pipeline([("preprocessor", preprocessor), ("classifier", classifier)])

    @staticmethod
    def _evaluate(pipeline: Pipeline, x_test: pl.DataFrame, y_test: np.ndarray) -> dict[str, float]:
        y_pred = pipeline.predict(x_test)
        y_proba = pipeline.predict_proba(x_test)[:, 1]
        return {
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "precision": float(precision_score(y_test, y_pred, zero_division=0)),
            "recall": float(recall_score(y_test, y_pred, zero_division=0)),
            "f1_score": float(f1_score(y_test, y_pred, zero_division=0)),
            "roc_auc": float(roc_auc_score(y_test, y_proba)),
        }
