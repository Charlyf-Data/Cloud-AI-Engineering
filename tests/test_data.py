"""Tests de la génération, de la validation et du nettoyage des données."""
import polars as pl
import pytest

from express_delivery.data.cleaner import OrderDataCleaner
from express_delivery.data.generator import OrderDataGenerator
from express_delivery.data.validator import OrderDataValidator
from express_delivery.domain.exceptions import DataValidationError
from express_delivery.domain.schemas import REQUIRED_COLUMNS, TARGET_COLUMN


def _set_value(df: pl.DataFrame, column: str, row: int, value: object) -> pl.DataFrame:
    """Remplace la valeur d'une cellule."""
    return df.with_columns(
        pl.when(pl.int_range(pl.len()) == row).then(pl.lit(value)).otherwise(pl.col(column)).alias(column)
    )


class TestGenerator:
    def test_columns_and_size(self, orders: pl.DataFrame) -> None:
        assert orders.columns == REQUIRED_COLUMNS
        assert orders.height == 500

    def test_is_reproducible(self, orders: pl.DataFrame) -> None:
        assert OrderDataGenerator(n_rows=500, random_state=42).generate().equals(orders)

    def test_target_is_binary(self, orders: pl.DataFrame) -> None:
        assert set(orders[TARGET_COLUMN].unique().to_list()) <= {0, 1}

    def test_generated_data_is_valid(self, orders: pl.DataFrame) -> None:
        OrderDataValidator().validate(orders)


class TestValidator:
    @pytest.mark.parametrize(
        ("column", "value", "message"),
        [
            ("distance_km", -1.0, "distance"),
            ("weight_kg", -1.0, "poids"),
            ("preparation_time_min", -1.0, "préparation"),
            ("carrier_capacity", 1.5, "capacité"),
            ("hour", 24, "heures"),
            ("stock_available", 2, "stock_available"),
            (TARGET_COLUMN, None, "cible"),
        ],
    )
    def test_detects_invalid_value(self, orders: pl.DataFrame, column: str, value: object, message: str) -> None:
        with pytest.raises(DataValidationError, match=message):
            OrderDataValidator().validate(_set_value(orders, column, 3, value))

    def test_detects_duplicates(self, orders: pl.DataFrame) -> None:
        with pytest.raises(DataValidationError, match="dupliqués"):
            OrderDataValidator().validate(pl.concat([orders, orders.head(1)]))

    def test_detects_missing_column(self, orders: pl.DataFrame) -> None:
        with pytest.raises(DataValidationError, match="distance_km"):
            OrderDataValidator().validate(orders.drop("distance_km"))


class TestCleaner:
    def test_removes_duplicates(self, orders: pl.DataFrame) -> None:
        cleaned = OrderDataCleaner().clean(pl.concat([orders, orders.head(1)]))
        assert cleaned.height == orders.height
        OrderDataValidator().validate(cleaned)

    def test_removes_invalid_rows(self, orders: pl.DataFrame) -> None:
        dirty = _set_value(_set_value(orders, "distance_km", 3, -1.0), "carrier_capacity", 7, 1.5)
        cleaned = OrderDataCleaner().clean(dirty)
        assert cleaned.height == orders.height - 2
        OrderDataValidator().validate(cleaned)

    def test_parses_string_dates(self, orders: pl.DataFrame) -> None:
        as_text = orders.with_columns(pl.col("order_date").dt.to_string("%Y-%m-%d %H:%M:%S"))
        cleaned = OrderDataCleaner().clean(as_text)
        assert cleaned.schema["order_date"] == pl.Datetime("us")
