"""Prédiction d'éligibilité avec seuil de décision."""
import time
from datetime import datetime, timezone

import polars as pl

from express_delivery.domain.schemas import FEATURE_COLUMNS, ModelBundle, OrderFeatures, Prediction


class EligibilityPredictor:
    """Probabilité du modèle -> seuil -> décision oui/non."""

    def __init__(self, bundle: ModelBundle, threshold: float) -> None:
        self._bundle = bundle
        self._threshold = threshold

    def predict(self, order: OrderFeatures, order_id: str) -> Prediction:
        """Prédit l'éligibilité express d'une commande."""
        start = time.perf_counter()
        frame = pl.DataFrame([order.to_feature_row()]).select(FEATURE_COLUMNS)
        probability = float(self._bundle.pipeline.predict_proba(frame)[0, 1])
        eligible = probability >= self._threshold
        return Prediction(
            order_id=order_id,
            express_eligible=eligible,
            decision="oui" if eligible else "non",
            probability=round(probability, 4),
            model_version=self._bundle.model_version,
            predicted_at=datetime.now(timezone.utc),
            latency_ms=round((time.perf_counter() - start) * 1000, 3),
        )
