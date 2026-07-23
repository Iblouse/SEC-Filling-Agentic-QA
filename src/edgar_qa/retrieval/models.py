from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class RetrievalChunk(BaseModel):
    """One stable, section-aware retrieval unit."""

    schema_version: str = "1.0"
    chunk_id: str
    document_id: str
    cik: str
    company_name: str | None = None
    form: str
    filing_date: str | None = None
    accession_number: str
    primary_document: str
    section_id: str
    section_label: str
    section_title: str
    section_occurrence: int
    chunk_index: int
    block_ids: list[str] = Field(default_factory=list)
    text: str
    term_count: int

    @field_validator("text")
    @classmethod
    def require_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Retrieval chunks cannot contain empty text.")
        return cleaned


class SearchFilters(BaseModel):
    cik: str | None = None
    form: str | None = None
    accession_number: str | None = None
    section_label: str | None = None


class SearchHit(BaseModel):
    rank: int
    score: float
    chunk: RetrievalChunk


class EvaluationQuestion(BaseModel):
    question_id: str
    question: str
    relevant_chunk_ids: list[str] = Field(default_factory=list)
    filters: SearchFilters = Field(default_factory=SearchFilters)
    notes: str | None = None


class QueryEvaluation(BaseModel):
    question_id: str
    question: str
    relevant_count: int
    retrieved_chunk_ids: list[str]
    recall_at_5: float
    recall_at_10: float
    reciprocal_rank: float
    ndcg_at_10: float


class RetrievalEvaluationReport(BaseModel):
    schema_version: str = "1.0"
    evaluated_at: datetime
    corpus_path: str
    question_path: str
    question_count: int
    recall_at_5: float
    recall_at_10: float
    mean_reciprocal_rank: float
    ndcg_at_10: float
    queries: list[QueryEvaluation]
    configuration: dict[str, Any] = Field(default_factory=dict)
