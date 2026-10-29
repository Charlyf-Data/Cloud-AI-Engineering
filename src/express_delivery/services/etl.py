"""Cas d'usage : ETL médaillon raw -> silver -> gold à partir de la base analytique."""
import logging
from datetime import datetime, timezone

import polars as pl

from express_delivery.abstractions.data import DataExtractor, LayerWriter
from express_delivery.data.gold_transformer import GoldTransformer
from express_delivery.data.raw_validator import REJECTION_COLUMN, RawOrderValidator
from express_delivery.data.silver_transformer import SilverTransformer

logger = logging.getLogger(__name__)


class MedallionEtl:
    """Enchaîne les étapes et écrit les couches raw (copie brute), rejected (quarantaine), silver et gold."""

    def __init__(
        self,
        source: DataExtractor,
        validator: RawOrderValidator,
        silver: SilverTransformer,
        gold: GoldTransformer,
        writer: LayerWriter,
    ) -> None:
        self._source = source
        self._validator = validator
        self._silver = silver
        self._gold = gold
        self._writer = writer

    def run(self) -> pl.DataFrame:
        """Exécute l'ETL et retourne la couche gold."""
        raw = self._source.extract().with_columns(ingested_at=pl.lit(datetime.now(timezone.utc)))
        self._writer.write("raw", raw)

        valid, rejected = self._validator.split(raw)
        self._writer.write("rejected", rejected)
        silver = self._silver.transform(valid.drop("ingested_at"))
        self._writer.write("silver", silver)

        gold = self._gold.transform(silver)
        self._writer.write("gold", gold)
        context = {"raw": raw.height, "rejected": rejected.height, "silver": silver.height, "gold": gold.height}
        logger.info("ETL terminé", extra={"context": context})
        if rejected.height:
            reasons = rejected.group_by(REJECTION_COLUMN).len().rows()
            logger.warning("Commandes mises en quarantaine", extra={"context": dict(reasons)})
        return gold
