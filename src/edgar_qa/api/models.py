from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


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


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str = "sec-filing-agentic-qa"


class ReadinessResponse(BaseModel):
    status: Literal["ready"] = "ready"
