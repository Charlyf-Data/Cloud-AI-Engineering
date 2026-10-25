"""Construction de l'application FastAPI."""
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from express_delivery.abstractions.model import ModelRepository
from express_delivery.abstractions.storage import OrderStore
from express_delivery.api.routes import router
from express_delivery.config import Settings
from express_delivery.domain.exceptions import ModelNotLoadedError, OrderNotFoundError
from express_delivery.ml.predictor import EligibilityPredictor
from express_delivery.services.orders import OrderService

logger = logging.getLogger(__name__)


class ApiFactory:
    """Assemble l'application : dépendances, routes et gestion centralisée des erreurs."""

    def __init__(self, settings: Settings, store: OrderStore, repository: ModelRepository) -> None:
        self._settings = settings
        self._store = store
        self._repository = repository

    def create(self) -> FastAPI:
        app = FastAPI(
            title=f"{self._settings.service_name} API",
            version=self._settings.model_version,
            lifespan=self._lifespan,
        )
        app.include_router(router)
        app.add_exception_handler(RequestValidationError, self._validation_error)
        app.add_exception_handler(OrderNotFoundError, self._not_found)
        app.add_exception_handler(ModelNotLoadedError, self._model_unavailable)
        app.add_exception_handler(Exception, self._internal_error)
        return app

    @asynccontextmanager
    async def _lifespan(self, app: FastAPI) -> AsyncIterator[None]:
        """Charge le modèle au démarrage ; sans modèle, l'API démarre mais n'est pas prête."""
        predictor = None
        try:
            bundle = self._repository.load()
            predictor = EligibilityPredictor(bundle, self._settings.prediction_threshold)
            logger.info("Modèle chargé", extra={"context": {"model_version": bundle.model_version}})
        except ModelNotLoadedError as error:
            logger.warning(str(error))
        app.state.settings = self._settings
        app.state.store = self._store
        app.state.predictor = predictor
        app.state.order_service = OrderService(self._store, predictor)
        yield

    @staticmethod
    def _error(status_code: int, error: str, message: str, details: list[str] | None = None) -> JSONResponse:
        content = {"error": error, "message": message}
        if details:
            content["details"] = details
        return JSONResponse(status_code=status_code, content=content)

    async def _validation_error(self, request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [f"{'.'.join(str(part) for part in e['loc'])} : {e['msg']}" for e in exc.errors()]
        return self._error(422, "validation_error", "Requête invalide", details)

    async def _not_found(self, request: Request, exc: OrderNotFoundError) -> JSONResponse:
        return self._error(404, "not_found", str(exc))

    async def _model_unavailable(self, request: Request, exc: ModelNotLoadedError) -> JSONResponse:
        return self._error(503, "model_unavailable", str(exc))

    async def _internal_error(self, request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Erreur non gérée", extra={"context": {"path": request.url.path}})
        return self._error(500, "internal_error", "Erreur interne")
