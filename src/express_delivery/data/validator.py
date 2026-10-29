"""Contrôles qualité du jeu de commandes."""
import polars as pl

from express_delivery.domain.exceptions import DataValidationError
from express_delivery.domain.schemas import REQUIRED_COLUMNS, TARGET_COLUMN


class OrderDataValidator:
    """Lève DataValidationError à la première règle violée."""

    def check_columns(self, df: pl.DataFrame) -> None:
        """Vérifie la présence des colonnes obligatoires."""
        missing = set(REQUIRED_COLUMNS) - set(df.columns)
        if missing:
            raise DataValidationError(f"Colonnes obligatoires absentes : {sorted(missing)}")

    def validate(self, df: pl.DataFrame) -> None:
        """Applique toutes les règles qualité."""
        self.check_columns(df)
        rules = self._rules()
        violations = df.select([rule.alias(str(i)) for i, (rule, _) in enumerate(rules)]).row(0)
        for violated, (_, message) in zip(violations, rules):
            if violated:
                raise DataValidationError(message)

    def _rules(self) -> list[tuple[pl.Expr, str]]:
        """Chaque expression vaut True si la règle est violée."""
        return [
            (pl.col("order_id").is_duplicated().any(), "Des identifiants de commande sont dupliqués."),
            (pl.col(TARGET_COLUMN).is_null().any(), "La variable cible contient des valeurs manquantes."),
            (self._any_invalid(pl.col("hour").is_between(0, 23)), "Certaines heures sont invalides."),
            (self._any_invalid(pl.col("distance_km") >= 0), "La distance ne peut pas être négative."),
            (self._any_invalid(pl.col("weight_kg") >= 0), "Le poids ne peut pas être négatif."),
            (
                self._any_invalid(pl.col("preparation_time_min") >= 0),
                "Le temps de préparation ne peut pas être négatif.",
            ),
            (
                self._any_invalid(pl.col("carrier_capacity").is_between(0, 1)),
                "La capacité du transporteur doit être comprise entre 0 et 1.",
            ),
            (
                self._any_invalid(pl.col("stock_available").is_in([0, 1])),
                "La variable stock_available doit contenir uniquement 0 ou 1.",
            ),
        ]

    @staticmethod
    def _any_invalid(condition: pl.Expr) -> pl.Expr:
        """True si au moins une ligne ne respecte pas la condition (null compris)."""
        return ~condition.fill_null(False).all()
