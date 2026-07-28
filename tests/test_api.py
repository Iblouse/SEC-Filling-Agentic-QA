from __future__ import annotations

from fastapi.testclient import TestClient

from edgar_qa.api.app import create_app
from edgar_qa.api.models import AnswerRequest, AnswerResponse, CitationSource


class FakeService:
    def answer(self, request_id: str, request: AnswerRequest) -> AnswerResponse:
        return AnswerResponse(
            request_id=request_id,
            question=request.question,
            answer="The filing describes market risk. [S1]",
            abstained=False,
            revised=False,
            unresolved_after_revision=False,
            citation_valid=True,
            critic_verdict="accept",
            citations=[
                CitationSource(
                    source_id="S1",
                    chunk_id="chunk-1",
                    cik="0000019617",
                    company_name="JPMorgan Chase & Co.",
                    form="10-K",
                    filing_date="2026-02-13",
                    accession_number="0000019617-26-000000",
                    section_label="Item 1A",
                    section_title="Risk Factors",
                    excerpt="Market conditions may adversely affect results.",
                )
            ],
            model_calls=2,
            total_tokens=120,
            latency_ms=25.5,
        )


def test_health_and_readiness() -> None:
    app = create_app(service_factory=FakeService)
    with TestClient(app) as client:
        assert client.get("/healthz").json()["status"] == "ok"
        ready = client.get("/readyz")
        assert ready.status_code == 200
        assert ready.json() == {"status": "ready"}


def test_answer_returns_request_id_and_citations() -> None:
    app = create_app(service_factory=FakeService)
    with TestClient(app) as client:
        response = client.post(
            "/v1/answer",
            headers={"X-Request-ID": "portfolio-test-001"},
            json={
                "question": "What risk is described?",
                "filters": {"cik": "0000019617", "form": "10-K"},
            },
        )
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "portfolio-test-001"
    body = response.json()
    assert body["request_id"] == "portfolio-test-001"
    assert body["critic_verdict"] == "accept"
    assert body["citations"][0]["source_id"] == "S1"


def test_answer_request_validation_rejects_short_question() -> None:
    app = create_app(service_factory=FakeService)
    with TestClient(app) as client:
        response = client.post("/v1/answer", json={"question": "x"})
    assert response.status_code == 422
