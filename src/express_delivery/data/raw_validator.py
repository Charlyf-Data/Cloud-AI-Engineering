"""Validation ETL : contrôle des commandes brutes de l'ERP avant la couche silver."""
import polars as pl

from express_delivery.domain.exceptions import DataValidationError
from express_delivery.domain.schemas import FEATURE_COLUMNS

# Mêmes colonnes que le domaine, sans la cible que l'ERP ne fournit pas
RAW_COLUMNS = ["order_id", "order_date", *FEATURE_COLUMNS]

ERP_WEATHER = ["clear", "rain", "wind", "snow"]
ERP_DELIVERY_ZONE = ["centre", "suburb", "rural"]
ERP_CUSTOMER_TYPE = ["individual", "business"]
ERP_MAX_CARRIER_CAPACITY = 50.0

REJECTION_COLUMN = "rejection_reason"


class RawOrderValidator:
    """Schéma manquant -> erreur bloquante ; ligne invalide -> quarantaine avec son motif.

    weekend et preparation_time_min peuvent être nuls (migrations de schéma 2015 et 2017).
    """

    def split(self, df: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
        """Retourne (lignes valides, lignes rejetées avec rejection_reason)."""
        missing = set(RAW_COLUMNS) - set(df.columns)
        if missing:
            raise DataValidationError(f"Colonnes ERP absentes : {sorted(missing)}")
        checked = df.with_columns(self._first_violation().alias(REJECTION_COLUMN))
        valid = checked.filter(pl.col(REJECTION_COLUMN).is_null()).drop(REJECTION_COLUMN)
        rejected = checked.filter(pl.col(REJECTION_COLUMN).is_not_null())
        return valid, rejected

    def _first_violation(self) -> pl.Expr:
        """Motif de la première règle violée ; null si la ligne est valide."""
        expression = pl.lit(None, dtype=pl.String)
        for condition, reason in reversed(self._rules()):
            expression = pl.when(~condition.fill_null(False)).then(pl.lit(reason)).otherwise(expression)
        return expression

    @staticmethod
    def _optional(column: str, condition: pl.Expr) -> pl.Expr:
        return pl.col(column).is_null() | condition

    def _rules(self) -> list[tuple[pl.Expr, str]]:
        """Chaque condition vaut True si la ligne respecte la règle."""
        return [
            (pl.col("order_id").is_not_null(), "order_id manquant"),
            (pl.col("order_date").is_not_null(), "order_date manquante"),
            (pl.col("hour").is_between(0, 23), "hour hors de [0, 23]"),
            (pl.col("day_of_week").is_between(0, 6), "day_of_week hors de [0, 6]"),
            (
                pl.col("day_of_week") == pl.col("order_date").dt.weekday() - 1,
                "day_of_week incohérent avec order_date",
            ),
            (
                self._optional("weekend", pl.col("weekend") == (pl.col("day_of_week") >= 5).cast(pl.Int64)),
                "weekend incohérent avec day_of_week",
            ),
            (pl.col("distance_km") >= 0, "distance_km négative ou manquante"),
            (pl.col("order_value_eur") >= 0, "order_value_eur négative ou manquante"),
            (pl.col("weight_kg") >= 0, "weight_kg négatif ou manquant"),
            (pl.col("stock_available").is_in([0, 1]), "stock_available différent de 0/1"),
            (
                self._optional("preparation_time_min", pl.col("preparation_time_min") >= 0),
                "preparation_time_min négatif",
            ),
            (
                pl.col("carrier_capacity").is_between(0, ERP_MAX_CARRIER_CAPACITY),
                "carrier_capacity hors de [0, 50]",
            ),
            (pl.col("weather").is_in(ERP_WEATHER), "weather inconnue"),
            (pl.col("delivery_zone").is_in(ERP_DELIVERY_ZONE), "delivery_zone inconnue"),
            (pl.col("customer_type").is_in(ERP_CUSTOMER_TYPE), "customer_type inconnu"),
        ]
