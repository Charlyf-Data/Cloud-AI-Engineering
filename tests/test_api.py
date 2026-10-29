"""Tests de conformité de l'API au contrat Start/openapi.yml (séance 1)."""
import pytest
from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ready_with_model(client: TestClient) -> None:
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["checks"] == {"model": "loaded", "order_store": "reachable"}


def test_prediction(client: TestClient, valid_order: dict) -> None:
    response = client.post("/v1/predictions", json={**valid_order, "order_id": "CMD-42"})
    assert response.status_code == 200
    body = response.json()
    assert body["order_id"] == "CMD-42"
    assert body["decision"] in {"oui", "non"}
    assert 0 <= body["probability"] <= 1
    assert {"model_version", "predicted_at", "latency_ms"} <= body.keys()


@pytest.mark.parametrize(
    ("change", "field"),
    [
        ({"foo": 1}, "foo"),
        ({"weather": "grele"}, "weather"),
        ({"hour": 24}, "hour"),
        ({"carrier_capacity": 1.5}, "carrier_capacity"),
    ],
)
def test_prediction_rejects_invalid_order(client: TestClient, valid_order: dict, change: dict, field: str) -> None:
    response = client.post("/v1/predictions", json={**valid_order, **change})
    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "validation_error"
    assert any(field in detail for detail in body["details"])


def test_prediction_rejects_missing_field(client: TestClient, valid_order: dict) -> None:
    del valid_order["distance_km"]
    response = client.post("/v1/predictions", json=valid_order)
    assert response.status_code == 422
    assert any("distance_km" in detail for detail in response.json()["details"])


def test_create_and_read_order(client: TestClient, valid_order: dict) -> None:
    created = client.post("/v1/orders", json=valid_order)
    assert created.status_code == 202
    order_id = created.json()["order_id"]
    assert created.json()["status"] == "accepted"

    read = client.get(f"/v1/orders/{order_id}")
    assert read.status_code == 200
    assert read.json() == {**valid_order, "order_id": order_id}


def test_order_keeps_client_id(client: TestClient, valid_order: dict) -> None:
    response = client.post("/v1/orders", json={**valid_order, "order_id": "CMD-CLIENT"})
    assert response.json()["order_id"] == "CMD-CLIENT"


def test_unknown_order(client: TestClient) -> None:
    response = client.get("/v1/orders/INCONNU")
    assert response.status_code == 404
    assert response.json()["error"] == "not_found"


def test_without_model(client_without_model: TestClient, valid_order: dict) -> None:
    assert client_without_model.get("/health").status_code == 200
    assert client_without_model.get("/health/ready").status_code == 503
    prediction = client_without_model.post("/v1/predictions", json=valid_order)
    assert prediction.status_code == 503
    assert prediction.json()["error"] == "model_unavailable"
    assert client_without_model.post("/v1/orders", json=valid_order).status_code == 202
