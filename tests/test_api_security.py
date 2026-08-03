from __future__ import annotations

from fastapi.testclient import TestClient

from edgar_qa.api.app import create_app
from edgar_qa.api.models import AnswerRequest, AnswerResponse
from edgar_qa.api.settings import APISettings


class FakeAnswerService:
    def answer(self, request_id: str, request: AnswerRequest) -> AnswerResponse:
        return AnswerResponse(
            request_id=request_id,
            question=request.question,
            answer="Supported answer.",
            abstained=False,
            revised=False,
            unresolved_after_revision=False,
            citation_valid=True,
            critic_verdict="accept",
            citations=[],
            model_calls=2,
            total_tokens=50,
            latency_ms=10.0,
        )


def secured_app() -> object:
    return create_app(
        service_factory=FakeAnswerService,
        feedback_store_factory=lambda: None,
        settings=APISettings(
            qa_api_key="a" * 64,
            qa_disable_docs=True,
        ),
    )


def test_health_and_readiness_do_not_require_api_key() -> None:
    with TestClient(secured_app()) as client:
        assert client.get("/healthz").status_code == 200
        assert client.get("/readyz").status_code == 200


def test_protected_endpoint_rejects_missing_key() -> None:
    with TestClient(secured_app()) as client:
        response = client.post(
            "/v1/answer",
            json={"question": "What risks were disclosed?"},
        )
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "ApiKey"


def test_protected_endpoint_rejects_wrong_key() -> None:
    with TestClient(secured_app()) as client:
        response = client.post(
            "/v1/answer",
            headers={"X-API-Key": "b" * 64},
            json={"question": "What risks were disclosed?"},
        )
    assert response.status_code == 401


def test_protected_endpoint_accepts_valid_key() -> None:
    with TestClient(secured_app()) as client:
        response = client.post(
            "/v1/answer",
            headers={"X-API-Key": "a" * 64},
            json={"question": "What risks were disclosed?"},
        )
    assert response.status_code == 200


def test_documentation_is_disabled_in_deployed_mode() -> None:
    with TestClient(secured_app()) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/openapi.json").status_code == 404
