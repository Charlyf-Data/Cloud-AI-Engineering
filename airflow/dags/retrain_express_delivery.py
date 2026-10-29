"""Réentraînement planifié du modèle d'éligibilité express : etl >> train.

Airflow n'embarque pas le code ML : il lance l'image d'entraînement publiée par la CI/CD
(processus d'exécution, pas de construction).
- etl   : MongoDB -> lake raw / rejected / silver / gold (validation ETL) ;
- train : couche gold -> modèle (validation applicative), ignoré tant qu'il n'y a pas
          RETRAIN_MIN_NEW_ORDERS nouvelles commandes. L'API recharge ensuite le modèle.
"""
import os
from datetime import datetime, timedelta

from airflow.providers.docker.operators.docker import DockerOperator
from airflow.sdk import DAG
from docker.types import Mount


def _job(task_id: str, mounts: list[Mount], environment: dict[str, str]) -> DockerOperator:
    """Exécute une commande de l'application dans l'image d'entraînement."""
    return DockerOperator(
        task_id=task_id,
        image=os.environ["TRAIN_IMAGE"],
        command=task_id,
        docker_url="unix://var/run/docker.sock",
        network_mode=os.environ["APP_NETWORK"],
        mounts=mounts,
        environment={"APP_ENV": os.environ.get("APP_ENV", "prod"), **environment},
        mount_tmp_dir=False,
        auto_remove="success",
    )


with DAG(
    dag_id="retrain_express_delivery",
    schedule=timedelta(minutes=int(os.environ.get("RETRAIN_INTERVAL_MINUTES", "60"))),
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 1, "retry_delay": timedelta(minutes=1)},
    tags=["ml", "express-delivery"],
) as dag:
    lake = os.environ["LAKE_VOLUME"]
    etl = _job(
        "etl",
        [Mount(source=lake, target="/app/lake", type="volume")],
        {"MONGO_URI": os.environ["MONGO_URI"]},
    )
    train = _job(
        "train",
        [
            Mount(source=lake, target="/app/lake", type="volume", read_only=True),
            Mount(source=os.environ["ARTIFACTS_VOLUME"], target="/app/artifacts", type="volume"),
        ],
        {
            "DATA_PATH": "lake/gold/orders.parquet",
            "MODEL_VERSION": os.environ.get("MODEL_VERSION", "1.1.0"),
            "RETRAIN_MIN_NEW_ORDERS": os.environ.get("RETRAIN_MIN_NEW_ORDERS", "100"),
        },
    )
    etl >> train  # pylint: disable=pointless-statement
