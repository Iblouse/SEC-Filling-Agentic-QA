from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any, cast
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from edgar_qa.api.feedback import (
    FeedbackStore,
    FeedbackStoreError,
    build_feedback_store,
)
from edgar_qa.api.metrics import (
    MetricsConfig,
    emit_answer_metrics,
    emit_feedback_metrics,
    emit_request_metrics,
)
from edgar_qa.api.models import (
    AnswerRequest,
    AnswerResponse,
    FeedbackRequest,
    FeedbackResponse,
    HealthResponse,
)
from edgar_qa.api.security import api_key_is_valid, path_requires_api_key
from edgar_qa.api.service import AnswerService, QAService, ServiceDependencyError
from edgar_qa.api.settings import APISettings

LOGGER = logging.getLogger("edgar_qa.api")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

ServiceFactory = Callable[[], AnswerService]
FeedbackStoreFactory = Callable[[], FeedbackStore | None]


def create_app(
    service_factory: ServiceFactory | None = None,
    feedback_store_factory: FeedbackStoreFactory | None = None,
    settings: APISettings | None = None,
) -> FastAPI:
    """Create the API with injectable dependencies for tests."""

    resolved_settings = settings or APISettings()
    factory = service_factory or (lambda: QAService.build(resolved_settings))
    feedback_factory = feedback_store_factory or (lambda: build_feedback_store(resolved_settings))
    metrics_config = MetricsConfig(
        namespace=resolved_settings.qa_metrics_namespace,
        service=resolved_settings.qa_service_name,
        environment=resolved_settings.qa_environment,
    )

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        application.state.metrics_config = metrics_config
        try:
            application.state.qa_service = factory()
            application.state.startup_error = None
            LOGGER.info("qa_service_ready")
        except Exception as exc:
            application.state.qa_service = None
            application.state.startup_error = str(exc)
            LOGGER.exception("qa_service_startup_failed")

        try:
            application.state.feedback_store = feedback_factory()
            application.state.feedback_error = None
            if application.state.feedback_store is not None:
                LOGGER.info("feedback_store_ready")
        except Exception as exc:
            application.state.feedback_store = None
            application.state.feedback_error = str(exc)
            LOGGER.exception("feedback_store_startup_failed")
        yield

    docs_url = None if resolved_settings.qa_disable_docs else "/docs"
    openapi_url = None if resolved_settings.qa_disable_docs else "/openapi.json"
    redoc_url = None if resolved_settings.qa_disable_docs else "/redoc"

    application = FastAPI(
        title="SEC Filing Agentic QA API",
        version="0.3.0",
        lifespan=lifespan,
        docs_url=docs_url,
        openapi_url=openapi_url,
        redoc_url=redoc_url,
    )

    @application.middleware("http")
    async def request_context(request: Request, call_next: Any) -> Any:
        request_id = _request_id(request.headers.get("X-Request-ID"))
        request.state.request_id = request_id
        started = time.perf_counter()

        if path_requires_api_key(request.url.path) and not api_key_is_valid(
            request.headers.get("X-API-Key"),
            resolved_settings.qa_api_key,
        ):
            response = JSONResponse(
                status_code=401,
                content={"detail": "A valid API key is required."},
                headers={"WWW-Authenticate": "ApiKey"},
            )
        else:
            try:
                response = await call_next(request)
            except Exception:
                duration_ms = (time.perf_counter() - started) * 1000
                emit_request_metrics(
                    metrics_config,
                    method=request.method,
                    path=request.url.path,
                    status_code=500,
                    duration_ms=duration_ms,
                )
                LOGGER.exception(
                    "request_failed request_id=%s method=%s path=%s",
                    request_id,
                    request.method,
                    request.url.path,
                )
                raise

        duration_ms = (time.perf_counter() - started) * 1000
        response.headers["X-Request-ID"] = request_id
        emit_request_metrics(
            metrics_config,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        LOGGER.info(
            "request_complete request_id=%s method=%s path=%s status=%s duration_ms=%.2f",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response

    @application.get("/healthz", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse()

    @application.get("/readyz")
    def readiness(request: Request) -> JSONResponse:
        if getattr(request.app.state, "qa_service", None) is None:
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready"},
            )
        return JSONResponse(status_code=200, content={"status": "ready"})

    @application.post("/v1/answer", response_model=AnswerResponse)
    def answer(request: Request, payload: AnswerRequest) -> AnswerResponse:
        service = _service(request)
        try:
            response = service.answer(request.state.request_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except ServiceDependencyError as exc:
            LOGGER.exception(
                "qa_dependency_failed request_id=%s",
                request.state.request_id,
            )
            raise HTTPException(
                status_code=502,
                detail="The QA dependency failed after retries.",
            ) from exc
        emit_answer_metrics(metrics_config, response)
        return response

    @application.post(
        "/v1/feedback",
        response_model=FeedbackResponse,
        status_code=201,
    )
    def feedback(request: Request, payload: FeedbackRequest) -> FeedbackResponse:
        store = _feedback_store(request)
        try:
            response = store.save(request.state.request_id, payload)
        except FeedbackStoreError as exc:
            LOGGER.exception(
                "feedback_dependency_failed feedback_id=%s answer_request_id=%s",
                request.state.request_id,
                payload.request_id,
            )
            raise HTTPException(
                status_code=502,
                detail="Feedback storage failed.",
            ) from exc
        emit_feedback_metrics(
            metrics_config,
            feedback_id=response.feedback_id,
            feedback=payload,
        )
        return response

    return application


def _service(request: Request) -> AnswerService:
    service = getattr(request.app.state, "qa_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="QA service is not ready.")
    return cast(AnswerService, service)


def _feedback_store(request: Request) -> FeedbackStore:
    store = getattr(request.app.state, "feedback_store", None)
    if store is None:
        raise HTTPException(status_code=503, detail="Feedback storage is not ready.")
    return cast(FeedbackStore, store)


def _request_id(value: str | None) -> str:
    if value is not None:
        cleaned = value.strip()
        if 1 <= len(cleaned) <= 64 and all(
            character.isalnum() or character in "-_." for character in cleaned
        ):
            return cleaned
    return str(uuid4())


app = create_app()
