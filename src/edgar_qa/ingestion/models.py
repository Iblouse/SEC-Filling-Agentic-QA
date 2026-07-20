from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class FilingReference(BaseModel):
    """The filing fields required by the ingestion worker."""

    model_config = ConfigDict(extra="allow")

    cik: str
    accession_number: str
    form: str
    source_url: HttpUrl
    company_name: str | None = None
    filing_date: str | None = None
    report_date: str | None = None
    primary_document: str | None = None

    @field_validator("cik")
    @classmethod
    def normalize_cik(cls, value: str) -> str:
        digits = "".join(character for character in value if character.isdigit())
        if not digits:
            raise ValueError("CIK must contain digits.")
        return digits.zfill(10)


class IngestionJob(BaseModel):
    """A versioned SQS message produced by Day 3 discovery."""

    model_config = ConfigDict(extra="allow")

    schema_version: str = "1.0"
    job_id: str
    discovered_at: datetime
    filing: FilingReference
    destination_bucket: str
    destination_key: str

    @field_validator("destination_bucket", "destination_key", "job_id")
    @classmethod
    def require_non_empty(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Job identifiers and destinations cannot be empty.")
        return cleaned


class IngestionStatus(StrEnum):
    STORED = "stored"
    ALREADY_EXISTS = "already_exists"


class IngestionResult(BaseModel):
    status: IngestionStatus
    job_id: str
    bucket: str
    key: str
    content_sha256: str | None = None
    bytes_stored: int | None = None
    fetched_at: datetime | None = None
    receipt_key: str | None = None
    response_metadata: dict[str, str | None] = Field(default_factory=dict)
