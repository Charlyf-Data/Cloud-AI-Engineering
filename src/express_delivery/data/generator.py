"""Générateur de commandes synthétiques (environnement de dev uniquement)."""
import numpy as np
import polars as pl

from express_delivery.domain.schemas import REQUIRED_COLUMNS


class OrderDataGenerator:
    """Génère des commandes fictives et leur cible à partir d'un score latent logistique."""

    _ZONE_PENALTY = {"centre": 0.0, "proche_banlieue": 0.10, "banlieue": 0.25, "rurale": 0.45}
    _WEATHER_PENALTY = {"normal": 0.0, "pluie": 0.10, "neige": 0.25, "orage": 0.30}
    _CUSTOMER_BONUS = {"standard": 0.0, "premium": 0.15}

    def __init__(self, n_rows: int, random_state: int) -> None:
        self._n_rows = n_rows
        self._random_state = random_state

    def generate(self) -> pl.DataFrame:
        """Retourne un jeu de commandes complet, cible incluse."""
        rng = np.random.default_rng(self._random_state)
        orders = self._base_columns(rng)
        return self._add_target(orders, rng).select(REQUIRED_COLUMNS)

    def _base_columns(self, rng: np.random.Generator) -> pl.DataFrame:
        """Tire les caractéristiques des commandes (ordre des tirages identique au notebook)."""
        n = self._n_rows
        start = np.datetime64("2025-01-01", "us").astype(np.int64)
        end = np.datetime64("2025-12-31", "us").astype(np.int64)
        order_dates = np.linspace(start, end, n).astype(np.int64).astype("datetime64[us]")

        return pl.DataFrame({
            "order_id": [f"CMD-{i:06d}" for i in range(1, n + 1)],
            "order_date": order_dates,
            "hour": rng.integers(7, 23, size=n),
            "distance_km": np.round(rng.gamma(shape=2.0, scale=4.0, size=n), 2),
            "order_value_eur": np.round(rng.uniform(10, 250, size=n), 2),
            "weight_kg": np.round(rng.uniform(0.2, 25, size=n), 2),
            "stock_available": rng.binomial(1, 0.85, size=n),
            "preparation_time_min": np.round(rng.normal(loc=25, scale=10, size=n).clip(5, 90), 1),
            "carrier_capacity": np.round(rng.uniform(0.2, 1.0, size=n), 2),
            "weather": rng.choice(
                ["normal", "pluie", "neige", "orage"], size=n, p=[0.65, 0.20, 0.10, 0.05]
            ),
            "delivery_zone": rng.choice(
                ["centre", "proche_banlieue", "banlieue", "rurale"], size=n, p=[0.30, 0.30, 0.25, 0.15]
            ),
            "customer_type": rng.choice(["standard", "premium"], size=n, p=[0.80, 0.20]),
        }).with_columns(
            day_of_week=(pl.col("order_date").dt.weekday() - 1).cast(pl.Int64),
        ).with_columns(
            weekend=(pl.col("day_of_week") >= 5).cast(pl.Int64),
        )

    def _latent_score(self) -> pl.Expr:
        """Score simulant la décision métier."""
        return (
            2.5
            - 0.18 * pl.col("distance_km")
            - 0.035 * pl.col("preparation_time_min")
            - 0.035 * pl.col("weight_kg")
            - pl.col("delivery_zone").replace_strict(self._ZONE_PENALTY)
            - pl.col("weather").replace_strict(self._WEATHER_PENALTY)
            + 1.8 * pl.col("stock_available")
            + 1.3 * pl.col("carrier_capacity")
            + pl.col("customer_type").replace_strict(self._CUSTOMER_BONUS)
            - 0.40 * pl.col("weekend")
            - 0.08 * (pl.col("hour") - 18).clip(lower_bound=0)
        )

    def _add_target(self, orders: pl.DataFrame, rng: np.random.Generator) -> pl.DataFrame:
        """Tire la cible selon la probabilité logistique du score."""
        score = orders.select(self._latent_score()).to_series().to_numpy()
        probability = 1 / (1 + np.exp(-score))
        return orders.with_columns(express_eligible=pl.Series(rng.binomial(1, probability)))
