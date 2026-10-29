"""Couche silver : commandes ERP validées, au vocabulaire de l'application."""
import polars as pl

from express_delivery.data.raw_validator import ERP_MAX_CARRIER_CAPACITY

# Vocabulaire ERP -> vocabulaire du contrat d'API (Start/openapi.yml)
WEATHER = {"clear": "normal", "rain": "pluie", "snow": "neige", "wind": "orage"}
DELIVERY_ZONE = {"centre": "centre", "suburb": "banlieue", "rural": "rurale"}
CUSTOMER_TYPE = {"individual": "standard", "business": "premium"}


class SilverTransformer:
    """Dédoublonne, traduit les modalités et ramène la capacité transporteur (colis) sur un taux [0, 1]."""

    def transform(self, valid: pl.DataFrame) -> pl.DataFrame:
        """Retourne la couche silver à partir des lignes validées par l'ETL."""
        return (
            valid.unique(subset="order_id", keep="last", maintain_order=True)
            .with_columns(
                pl.col("order_date").cast(pl.Datetime("us")),
                pl.col("weather").replace_strict(WEATHER),
                pl.col("delivery_zone").replace_strict(DELIVERY_ZONE),
                pl.col("customer_type").replace_strict(CUSTOMER_TYPE),
                (pl.col("carrier_capacity") / ERP_MAX_CARRIER_CAPACITY).round(2),
            )
            .sort("order_id")
        )
