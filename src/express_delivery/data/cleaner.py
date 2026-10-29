"""Nettoyage du jeu de commandes."""
import polars as pl


class OrderDataCleaner:
    """Dédoublonne, convertit les dates et retire les lignes invalides."""

    _ESSENTIAL_COLUMNS = [
        "order_id",
        "distance_km",
        "weight_kg",
        "stock_available",
        "preparation_time_min",
        "carrier_capacity",
        "express_eligible",
    ]

    def clean(self, df: pl.DataFrame) -> pl.DataFrame:
        """Retourne une copie nettoyée."""
        return (
            df.unique(subset="order_id", keep="last", maintain_order=True)
            .pipe(self._parse_dates)
            .drop_nulls(subset=self._ESSENTIAL_COLUMNS)
            .filter(
                pl.col("distance_km") >= 0,
                pl.col("weight_kg") >= 0,
                pl.col("preparation_time_min") >= 0,
                pl.col("carrier_capacity").is_between(0, 1),
                pl.col("stock_available").is_in([0, 1]),
            )
        )

    @staticmethod
    def _parse_dates(df: pl.DataFrame) -> pl.DataFrame:
        """Convertit order_date en datetime ; les valeurs illisibles deviennent nulles."""
        if df.schema["order_date"] == pl.String:
            return df.with_columns(pl.col("order_date").str.to_datetime(strict=False))
        return df
