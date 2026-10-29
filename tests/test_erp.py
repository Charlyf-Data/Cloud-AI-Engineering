"""Tests de l'intégration des commandes ERP (sans base de données : la CI n'en démarre pas)."""
from datetime import datetime, timedelta
from pathlib import Path

import polars as pl
import pytest

from express_delivery.abstractions.data import DataExtractor
from express_delivery.data.cleaner import OrderDataCleaner
from express_delivery.data.gold_transformer import GoldTransformer
from express_delivery.data.raw_validator import REJECTION_COLUMN, RawOrderValidator
from express_delivery.data.silver_transformer import SilverTransformer
from express_delivery.data.validator import OrderDataValidator
from express_delivery.domain.exceptions import DataValidationError
from express_delivery.domain.schemas import REQUIRED_COLUMNS, TARGET_COLUMN
from express_delivery.infrastructure.dev.file_model_repository import FileModelRepository
from express_delivery.infrastructure.dev.parquet_layer_writer import ParquetLayerWriter
from express_delivery.infrastructure.dev.polars_file_extractor import PolarsFileExtractor
from express_delivery.infrastructure.tracking import NoOpTracker
from express_delivery.ml.trainer import ModelTrainer
from express_delivery.services.etl import MedallionEtl
from express_delivery.services.retraining_policy import RetrainingPolicy
from express_delivery.services.training import TrainingPipeline


def _erp_orders(n: int) -> pl.DataFrame:
    """Commandes au format du simulateur ERP (tp4), dont une ancienne sans preparation_time_min."""
    dates = [datetime(2024, 1, 1) + timedelta(days=i) for i in range(n)]
    return pl.DataFrame({
        "order_id": [f"ERP-{i:08d}" for i in range(1, n + 1)],
        "order_date": dates,
        "hour": [8 + i % 12 for i in range(n)],
        "day_of_week": [d.weekday() for d in dates],
        "weekend": [int(d.weekday() >= 5) for d in dates],
        "distance_km": [1.0 + i % 40 for i in range(n)],
        "order_value_eur": [15.0 + i for i in range(n)],
        "weight_kg": [0.2 + i % 25 for i in range(n)],
        "stock_available": [i % 2 for i in range(n)],
        "preparation_time_min": [None] + [5.0 + i % 40 for i in range(1, n)],
        "carrier_capacity": [5.0 + i % 46 for i in range(n)],
        "weather": [["clear", "rain", "wind", "snow"][i % 4] for i in range(n)],
        "delivery_zone": [["centre", "suburb", "rural"][i % 3] for i in range(n)],
        "customer_type": [["individual", "business"][i % 2] for i in range(n)],
    })


def _set(df: pl.DataFrame, column: str, row: int, value: object) -> pl.DataFrame:
    return df.with_columns(
        pl.when(pl.int_range(pl.len()) == row).then(pl.lit(value)).otherwise(pl.col(column)).alias(column)
    )


class FakeErpExtractor(DataExtractor):
    """Base analytique simulée : renvoie des commandes brutes de l'ERP."""

    def __init__(self, orders: pl.DataFrame) -> None:
        self._orders = orders

    def extract(self) -> pl.DataFrame:
        return self._orders


def _etl(lake: Path, orders: pl.DataFrame) -> pl.DataFrame:
    return MedallionEtl(
        FakeErpExtractor(orders), RawOrderValidator(), SilverTransformer(), GoldTransformer(42),
        ParquetLayerWriter(lake),
    ).run()


class TestRawOrderValidator:
    @pytest.mark.parametrize(
        ("column", "value", "reason"),
        [
            ("hour", 24, "hour"),
            ("day_of_week", 3, "day_of_week incohérent"),
            ("weekend", 1, "weekend incohérent"),
            ("distance_km", -1.0, "distance_km"),
            ("carrier_capacity", 80.0, "carrier_capacity"),
            ("weather", "fog", "weather"),
            ("stock_available", 2, "stock_available"),
        ],
    )
    def test_quarantines_invalid_row(self, column: str, value: object, reason: str) -> None:
        orders = _erp_orders(10)
        valid, rejected = RawOrderValidator().split(_set(orders, column, 0 if column != "day_of_week" else 1, value))
        assert valid.height == 9
        assert reason in rejected[REJECTION_COLUMN][0]

    def test_accepts_nulls_from_schema_migrations(self) -> None:
        orders = _set(_erp_orders(10), "weekend", 2, None)
        valid, rejected = RawOrderValidator().split(orders)
        assert (valid.height, rejected.height) == (10, 0)

    def test_missing_column_is_blocking(self) -> None:
        with pytest.raises(DataValidationError, match="weather"):
            RawOrderValidator().split(_erp_orders(5).drop("weather"))


class TestTransformers:
    def test_silver_uses_api_vocabulary(self) -> None:
        silver = SilverTransformer().transform(pl.concat([_erp_orders(12), _erp_orders(12).head(1)]))
        assert silver.height == 12
        assert set(silver["weather"]) <= {"normal", "pluie", "neige", "orage"}
        assert set(silver["delivery_zone"]) <= {"centre", "banlieue", "rurale"}
        assert set(silver["customer_type"]) <= {"standard", "premium"}
        assert silver["carrier_capacity"].is_between(0, 1).all()

    def test_gold_is_complete_and_labelled(self) -> None:
        gold = GoldTransformer(random_state=42).transform(SilverTransformer().transform(_erp_orders(12)))
        assert gold.columns == REQUIRED_COLUMNS
        assert gold.height == 11
        assert set(gold[TARGET_COLUMN].unique()) <= {0, 1}


class TestMedallion:
    def test_writes_every_layer(self, tmp_path: Path) -> None:
        orders = _set(_erp_orders(20), "weather", 5, "fog")
        _etl(tmp_path, orders)
        heights = {layer: pl.read_parquet(tmp_path / layer / "orders.parquet").height
                   for layer in ["raw", "rejected", "silver", "gold"]}
        assert heights == {"raw": 20, "rejected": 1, "silver": 19, "gold": 18}

    def test_gold_passes_application_validation(self, tmp_path: Path) -> None:
        gold = _etl(tmp_path, _erp_orders(50))
        OrderDataValidator().validate(OrderDataCleaner().clean(gold))


class TestTrainingFromGold:
    def _pipeline(self, lake: Path, n: int, min_new_orders: int) -> TrainingPipeline:
        _etl(lake, _erp_orders(n))
        repository = FileModelRepository(lake, "model")
        return TrainingPipeline(
            extractor=PolarsFileExtractor(lake / "gold" / "orders.parquet"),
            validator=OrderDataValidator(),
            cleaner=OrderDataCleaner(),
            trainer=ModelTrainer(test_size=0.2, random_state=42, model_version="erp"),
            tracker=NoOpTracker(),
            repository=repository,
            policy=RetrainingPolicy(repository, min_new_orders),
        )

    def test_trains_on_gold(self, tmp_path: Path) -> None:
        bundle = self._pipeline(tmp_path, 300, min_new_orders=0).run()
        assert bundle is not None
        assert FileModelRepository(tmp_path, "model").load().training_rows == 299

    def test_skips_when_not_enough_new_orders(self, tmp_path: Path) -> None:
        self._pipeline(tmp_path, 300, min_new_orders=50).run()
        assert self._pipeline(tmp_path, 320, min_new_orders=50).run() is None
        assert self._pipeline(tmp_path, 400, min_new_orders=50).run() is not None



class TestRetrainingPolicy:
    def test_always_trains_without_threshold(self, tmp_path: Path) -> None:
        assert RetrainingPolicy(FileModelRepository(tmp_path, "absent"), 0).should_train(1)

    def test_counts_every_row_without_model(self, tmp_path: Path) -> None:
        policy = RetrainingPolicy(FileModelRepository(tmp_path, "absent"), 100)
        assert policy.new_orders(150) == 150
        assert policy.should_train(150)
