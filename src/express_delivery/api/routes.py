"""Endpoints de la séance 1."""
from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response

from express_delivery.abstractions.storage import OrderStore
from express_delivery.api.schemas import ErrorResponse, HealthStatus, OrderAccepted, ReadinessStatus
from express_delivery.config import Settings
from express_delivery.domain.exceptions import ModelNotLoadedError
from express_delivery.domain.schemas import OrderFeatures, Prediction, new_order_id
from express_delivery.ml.predictor import EligibilityPredictor
from express_delivery.services.orders import OrderService

router = APIRouter()


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_store(request: Request) -> OrderStore:
    return request.app.state.store


def get_order_service(request: Request) -> OrderService:
    return request.app.state.order_service


def get_predictor(request: Request) -> EligibilityPredictor:
    predictor = request.app.state.predictor
    if predictor is None:
        raise ModelNotLoadedError("Le modèle n'est pas chargé.")
    return predictor


@router.get("/health", tags=["health"], response_model=HealthStatus, operation_id="getHealth")
def get_health(settings: Settings = Depends(get_settings)) -> HealthStatus:
    return HealthStatus(service=settings.service_name, version=settings.model_version)


@router.get(
    "/health/ready",
    tags=["health"],
    response_model=ReadinessStatus,
    responses={503: {"model": ReadinessStatus}},
    operation_id="getReadiness",
)
def get_readiness(
    request: Request,
    response: Response,
    settings: Settings = Depends(get_settings),
    store: OrderStore = Depends(get_store),
) -> ReadinessStatus:
    checks = {
        "model": "loaded" if request.app.state.predictor is not None else "not_loaded",
        "order_store": "reachable" if store.is_reachable() else "unreachable",
    }
    ready = checks["model"] == "loaded" and checks["order_store"] == "reachable"
    if not ready:
        response.status_code = 503
    return ReadinessStatus(
        status="ready" if ready else "not_ready", checks=checks, version=settings.model_version
    )


@router.post(
    "/v1/orders",
    tags=["orders"],
    status_code=202,
    response_model=OrderAccepted,
    responses={422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    operation_id="createOrder",
)
def create_order(
    order: OrderFeatures,
    background_tasks: BackgroundTasks,
    service: OrderService = Depends(get_order_service),
) -> OrderAccepted:
    order_id = service.submit(order)
    background_tasks.add_task(service.predict_stored, order_id)
    return OrderAccepted(order_id=order_id)


@router.get(
    "/v1/orders/{order_id}",
    tags=["orders"],
    response_model=OrderFeatures,
    responses={404: {"model": ErrorResponse}},
    operation_id="getOrder",
)
def get_order(order_id: str, service: OrderService = Depends(get_order_service)) -> OrderFeatures:
    return service.get(order_id)


@router.post(
    "/v1/predictions",
    tags=["predictions"],
    response_model=Prediction,
    responses={422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
    operation_id="createPrediction",
)
def create_prediction(
    order: OrderFeatures, predictor: EligibilityPredictor = Depends(get_predictor)
) -> Prediction:
    return predictor.predict(order, order.order_id or new_order_id())
