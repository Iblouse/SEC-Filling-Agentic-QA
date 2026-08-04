from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from hashlib import sha256

from pydantic import BaseModel, Field


class BlockKind(StrEnum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    TABLE = "table"


class FilingIdentity(BaseModel):
    cik: str
    accession_number: str
    form: str
    filing_date: str | None = None
    primary_document: str
    company_name: str | None = None

    @property
    def document_id(self) -> str:
        value = f"{self.cik}:{self.accession_number}:{self.primary_document}"
        return sha256(value.encode("utf-8")).hexdigest()


class DocumentBlock(BaseModel):
    block_id: str
    order: int
    kind: BlockKind
    text: str
    table_rows: list[list[str]] | None = None


class ParsedSection(BaseModel):
    section_id: str
    label: str
    title: str
    occurrence: int
    start_block: int
    end_block: int
    block_ids: list[str] = Field(default_factory=list)


class ParsingDiagnostics(BaseModel):
    input_bytes: int
    total_characters: int
    block_count: int
    paragraph_count: int
    heading_count: int
    table_count: int
    section_count: int
    skipped_element_count: int
    duplicate_section_labels: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CuratedFilingDocument(BaseModel):
    schema_version: str = "1.0"
    parser_version: str
    parsed_at: datetime
    source_bucket: str
    source_key: str
    source_sha256: str
    filing: FilingIdentity
    document_title: str | None = None
    blocks: list[DocumentBlock] = Field(default_factory=list)
    sections: list[ParsedSection] = Field(default_factory=list)
    diagnostics: ParsingDiagnostics


class ParsingStatus(StrEnum):
    STORED = "stored"
    ALREADY_EXISTS = "already_exists"


class ParsingResult(BaseModel):
    status: ParsingStatus
    raw_bucket: str
    raw_key: str
    curated_bucket: str
    curated_key: str
    document_id: str
    block_count: int | None = None
    section_count: int | None = None
    warning_count: int | None = None
