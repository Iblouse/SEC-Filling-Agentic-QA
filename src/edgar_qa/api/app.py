from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any, cast
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from edgar_qa.api.models import AnswerRequest, AnswerResponse, HealthResponse
from edgar_qa.api.service import AnswerService, QAService, ServiceDependencyError

LOGGER = logging.getLogger("edgar_qa.api")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

ServiceFactory = Callable[[], AnswerService]


def create_app(service_factory: ServiceFactory | None = None) -> FastAPI:
    """Create the Day 11 API with an injectable service for tests."""

    factory = service_factory or QAService.build

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        try:
            application.state.qa_service = factory()
            application.state.startup_error = None
            LOGGER.info("qa_service_ready")
        except Exception as exc:
            application.state.qa_service = None
            application.state.startup_error = str(exc)
            LOGGER.exception("qa_service_startup_failed")
        yield

    application = FastAPI(
        title="SEC Filing Agentic QA API",
        version="0.1.0",
        lifespan=lifespan,
    )

    @application.middleware("http")
    async def request_context(request: Request, call_next: Any) -> Any:
        request_id = _request_id(request.headers.get("X-Request-ID"))
        request.state.request_id = request_id
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            LOGGER.exception(
                "request_failed request_id=%s method=%s path=%s",
                request_id,
                request.method,
                request.url.path,
            )
            raise
        duration_ms = (time.perf_counter() - started) * 1000
        response.headers["X-Request-ID"] = request_id
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
            return service.answer(request.state.request_id, payload)
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

    return application


def _service(request: Request) -> AnswerService:
    service = getattr(request.app.state, "qa_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="QA service is not ready.")
    return cast(AnswerService, service)


def _request_id(value: str | None) -> str:
    if value is not None:
        cleaned = value.strip()
        if 1 <= len(cleaned) <= 64 and all(
            character.isalnum() or character in "-_." for character in cleaned
        ):
            return cleaned
    return str(uuid4())


app = create_app()
