from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class AnswerFilters(BaseModel):
    """Optional SEC metadata filters supplied with an API question."""

    cik: str | None = None
    form: str | None = None
    accession_number: str | None = None
    section_label: str | None = None


class AnswerRequest(BaseModel):
    """Public request contract for one grounded SEC question."""

    question: str = Field(min_length=3, max_length=2000)
    filters: AnswerFilters = Field(default_factory=AnswerFilters)


class CitationSource(BaseModel):
    """Evidence metadata returned for a source cited in the final answer."""

    source_id: str
    chunk_id: str
    cik: str
    company_name: str | None = None
    form: str
    filing_date: str | None = None
    accession_number: str
    section_label: str
    section_title: str
    excerpt: str


class AnswerResponse(BaseModel):
    """Stable API response for the bounded agentic QA workflow."""

    request_id: str
    question: str
    answer: str
    abstained: bool
    revised: bool
    unresolved_after_revision: bool
    citation_valid: bool
    critic_verdict: Literal["accept", "revise"]
    citations: list[CitationSource] = Field(default_factory=list)
    model_calls: int
    total_tokens: int | None = None
    latency_ms: float


FeedbackReason = Literal[
    "relevant",
    "incomplete",
    "incorrect",
    "citation_issue",
    "other",
]


class FeedbackRequest(BaseModel):
    """User evaluation linked to a prior answer request ID."""

    request_id: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9._-]+$",
    )
    helpful: bool
    reason: FeedbackReason | None = None
    comment: str | None = Field(default=None, max_length=2000)
    citation_ids: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("comment")
    @classmethod
    def normalize_comment(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("citation_ids")
    @classmethod
    def normalize_citation_ids(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            cleaned = value.strip()
            if not cleaned:
                continue
            if len(cleaned) > 64:
                raise ValueError("citation_ids must be at most 64 characters each.")
            if cleaned not in normalized:
                normalized.append(cleaned)
        return normalized


class FeedbackResponse(BaseModel):
    """Acknowledgement returned after durable feedback storage."""

    status: Literal["accepted"] = "accepted"
    feedback_id: str
    request_id: str
    expires_at: str


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str = "sec-filing-agentic-qa"


class ReadinessResponse(BaseModel):
    status: Literal["ready"] = "ready"
