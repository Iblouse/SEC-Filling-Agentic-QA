from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from edgar_qa.parsing.models import CuratedFilingDocument
from edgar_qa.retrieval.chunking import SectionAwareChunker
from edgar_qa.retrieval.models import EvaluationQuestion, RetrievalChunk, SearchFilters


class S3CuratedCorpusReader:
    """Reads curated filing documents and creates a local retrieval corpus."""

    def __init__(self, s3_client: Any, curated_bucket: str) -> None:
        self._s3 = s3_client
        self.curated_bucket = curated_bucket

    def iter_documents(
        self,
        prefix: str = "documents/",
        maximum: int | None = None,
    ) -> Iterable[CuratedFilingDocument]:
        yielded = 0
        paginator = self._s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.curated_bucket, Prefix=prefix):
            for item in page.get("Contents", []):
                key = str(item["Key"])
                if not key.endswith(".json"):
                    continue
                response = self._s3.get_object(Bucket=self.curated_bucket, Key=key)
                payload = json.loads(response["Body"].read())
                document = CuratedFilingDocument.model_validate(payload)
                yield document
                yielded += 1
                if maximum is not None and yielded >= maximum:
                    return


def write_corpus_jsonl(chunks: Iterable[RetrievalChunk], path: Path) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    chunk_list = list(chunks)
    lines = [chunk.model_dump_json() for chunk in chunk_list]
    encoded = ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")
    path.write_bytes(encoded)
    return {
        "schema_version": "1.0",
        "created_at": datetime.now(UTC).isoformat(),
        "path": str(path),
        "chunk_count": len(chunk_list),
        "document_count": len({chunk.document_id for chunk in chunk_list}),
        "sha256": sha256(encoded).hexdigest(),
    }


def read_corpus_jsonl(path: Path) -> list[RetrievalChunk]:
    chunks: list[RetrievalChunk] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                chunks.append(RetrievalChunk.model_validate_json(line))
            except ValueError as exc:
                raise ValueError(f"Invalid corpus record at line {line_number}.") from exc
    if not chunks:
        raise ValueError(f"Corpus contains no chunks: {path}")
    return chunks


def create_question_template(
    chunks: list[RetrievalChunk],
    path: Path,
    maximum_questions: int = 10,
) -> int:
    """Create realistic, unlabeled questions scoped to available filings."""
    path.parent.mkdir(parents=True, exist_ok=True)
    representative: dict[str, RetrievalChunk] = {}
    for chunk in chunks:
        representative.setdefault(chunk.document_id, chunk)

    questions: list[EvaluationQuestion] = []
    for index, chunk in enumerate(representative.values(), start=1):
        company = chunk.company_name or f"CIK {chunk.cik}"
        filing_date = chunk.filing_date or "the selected date"
        if chunk.form.upper().startswith("8-K"):
            question_text = (
                f"What material event or development did {company} report in its "
                f"{chunk.form} filed on {filing_date}?"
            )
        elif chunk.form.upper().startswith("10-Q"):
            question_text = (
                f"What material risks, results, or changes did {company} discuss in its "
                f"{chunk.form} filed on {filing_date}?"
            )
        else:
            question_text = (
                f"What principal risks or business developments did {company} disclose in its "
                f"{chunk.form} filed on {filing_date}?"
            )
        questions.append(
            EvaluationQuestion(
                question_id=f"q{index:03d}",
                question=question_text,
                filters=SearchFilters(
                    cik=chunk.cik,
                    form=chunk.form,
                    accession_number=chunk.accession_number,
                ),
                notes="Review search results and add every supporting chunk ID.",
            )
        )
        if len(questions) >= maximum_questions:
            break

    with path.open("w", encoding="utf-8") as handle:
        for question in questions:
            handle.write(question.model_dump_json() + "\n")
    return len(questions)


def update_question_labels(
    path: Path,
    question_id: str,
    relevant_chunk_ids: list[str],
) -> EvaluationQuestion:
    """Update labels for one question without validating unrelated records."""
    lines = path.read_text(encoding="utf-8").splitlines()

    updated: EvaluationQuestion | None = None
    output_lines: list[str] = []

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue

        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON at line {line_number}.") from exc

        if payload.get("question_id") != question_id:
            # Preserve unrelated questions without validating their schema.
            output_lines.append(json.dumps(payload, separators=(",", ":")))
            continue

        try:
            question = EvaluationQuestion.model_validate(payload)
        except ValueError as exc:
            raise ValueError(
                f"Invalid target question {question_id} at line {line_number}."
            ) from exc

        question.relevant_chunk_ids = list(dict.fromkeys(relevant_chunk_ids))

        updated = question

        output_lines.append(question.model_dump_json())

    if updated is None:
        raise ValueError(f"Question ID {question_id!r} was not found.")

    path.write_text(
        "\n".join(output_lines) + "\n",
        encoding="utf-8",
    )

    return updated


def build_corpus(
    documents: Iterable[CuratedFilingDocument],
    maximum_terms: int,
    overlap_terms: int,
) -> list[RetrievalChunk]:
    chunker = SectionAwareChunker(
        maximum_terms=maximum_terms,
        overlap_terms=overlap_terms,
    )
    chunks: list[RetrievalChunk] = []
    for document in documents:
        chunks.extend(chunker.chunk_document(document))
    return chunks
