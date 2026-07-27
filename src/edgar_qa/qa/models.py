from __future__ import annotations

from pydantic import BaseModel, Field


class EvidenceSource(BaseModel):
    """One stable SEC evidence source exposed to the answer model."""

    source_id: str
    chunk_id: str
    document_id: str
    cik: str
    company_name: str | None = None
    form: str
    filing_date: str | None = None
    accession_number: str
    section_label: str
    section_title: str
    rank: int
    retrieval_score: float | None = None
    text: str


class GroundedAnswer(BaseModel):
    """One answer plus deterministic provenance and validation metadata."""

    question: str
    answer: str
    citations: list[str] = Field(default_factory=list)
    cited_chunk_ids: list[str] = Field(default_factory=list)
    abstained: bool = False
    citation_valid: bool = False
    validation_errors: list[str] = Field(default_factory=list)
    model_id: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    stop_reason: str | None = None
