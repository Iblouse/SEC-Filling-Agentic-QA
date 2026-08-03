from __future__ import annotations

from fastapi.testclient import TestClient

from edgar_qa.api.app import create_app
from edgar_qa.api.models import (
    AnswerRequest,
    AnswerResponse,
    FeedbackRequest,
    FeedbackResponse,
)
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


class FakeFeedbackStore:
    def __init__(self) -> None:
        self.saved: list[tuple[str, FeedbackRequest]] = []

    def save(
        self,
        feedback_id: str,
        feedback: FeedbackRequest,
    ) -> FeedbackResponse:
        self.saved.append((feedback_id, feedback))
        return FeedbackResponse(
            feedback_id=feedback_id,
            request_id=feedback.request_id,
            expires_at="2026-11-01T00:00:00+00:00",
        )


def test_feedback_endpoint_persists_and_returns_created() -> None:
    store = FakeFeedbackStore()
    app = create_app(
        service_factory=FakeAnswerService,
        feedback_store_factory=lambda: store,
        settings=APISettings(),
    )
    with TestClient(app) as client:
        response = client.post(
            "/v1/feedback",
            headers={"X-Request-ID": "feedback-001"},
            json={
                "request_id": "answer-001",
                "helpful": False,
                "reason": "citation_issue",
                "comment": "The second citation did not support the claim.",
                "citation_ids": ["S2", "S2"],
            },
        )

    assert response.status_code == 201
    assert response.json()["feedback_id"] == "feedback-001"
    assert store.saved[0][1].citation_ids == ["S2"]


def test_feedback_endpoint_is_unavailable_without_store() -> None:
    app = create_app(
        service_factory=FakeAnswerService,
        feedback_store_factory=lambda: None,
        settings=APISettings(),
    )
    with TestClient(app) as client:
        response = client.post(
            "/v1/feedback",
            json={"request_id": "answer-001", "helpful": True},
        )
    assert response.status_code == 503
