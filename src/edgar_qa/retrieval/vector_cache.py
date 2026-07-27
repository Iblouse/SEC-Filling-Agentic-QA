from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from edgar_qa.retrieval.embeddings import TextEmbedder
from edgar_qa.retrieval.models import RetrievalChunk


@dataclass(frozen=True)
class EmbeddingCacheRecord:
    chunk_id: str
    input_sha256: str
    input_token_count: int
    vector: list[float]


def embedding_input(chunk: RetrievalChunk) -> str:
    """Build the retrieval representation while retaining useful SEC metadata."""
    company = chunk.company_name or f"CIK {chunk.cik}"
    return (
        f"Company: {company}\n"
        f"Form: {chunk.form}\n"
        f"Filed: {chunk.filing_date or 'unknown'}\n"
        f"Section: {chunk.section_label} {chunk.section_title}\n"
        f"Text: {chunk.text}"
    )


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_embedding_cache(path: Path) -> dict[str, EmbeddingCacheRecord]:
    records: dict[str, EmbeddingCacheRecord] = {}
    if not path.exists():
        return records
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
                record = EmbeddingCacheRecord(
                    chunk_id=str(payload["chunk_id"]),
                    input_sha256=str(payload["input_sha256"]),
                    input_token_count=int(payload.get("input_token_count", 0)),
                    vector=[float(value) for value in payload["vector"]],
                )
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise ValueError(f"Invalid embedding cache record at line {line_number}.") from exc
            records[record.chunk_id] = record
    return records


def build_embedding_cache(
    chunks: list[RetrievalChunk],
    embedder: TextEmbedder,
    corpus_path: Path,
    cache_path: Path,
    manifest_path: Path,
    maximum_new: int | None = None,
    rebuild: bool = False,
) -> dict[str, Any]:
    if rebuild:
        cache_path.unlink(missing_ok=True)
        manifest_path.unlink(missing_ok=True)

    corpus_hash = file_sha256(corpus_path)
    expected_configuration = {
        "model_id": embedder.model_id,
        "dimensions": embedder.dimensions,
        "normalize": embedder.normalize,
        "corpus_sha256": corpus_hash,
    }
    _validate_existing_manifest(manifest_path, expected_configuration)

    existing = read_embedding_cache(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    new_count = 0
    total_input_tokens = sum(record.input_token_count for record in existing.values())

    with cache_path.open("a", encoding="utf-8") as handle:
        for chunk in chunks:
            text = embedding_input(chunk)
            input_hash = sha256(text.encode("utf-8")).hexdigest()
            previous = existing.get(chunk.chunk_id)
            if previous is not None:
                if previous.input_sha256 != input_hash:
                    raise ValueError(
                        f"Cached embedding input changed for chunk {chunk.chunk_id}. "
                        "Rebuild the embedding cache."
                    )
                continue
            if maximum_new is not None and new_count >= maximum_new:
                break

            result = embedder.embed(text)
            payload = {
                "chunk_id": chunk.chunk_id,
                "input_sha256": input_hash,
                "input_token_count": result.input_token_count,
                "vector": result.vector,
            }
            handle.write(json.dumps(payload, separators=(",", ":")) + "\n")
            handle.flush()
            existing[chunk.chunk_id] = EmbeddingCacheRecord(
                chunk_id=chunk.chunk_id,
                input_sha256=input_hash,
                input_token_count=result.input_token_count,
                vector=result.vector,
            )
            new_count += 1
            total_input_tokens += result.input_token_count
            _write_manifest(
                manifest_path,
                expected_configuration,
                embedded_count=len(existing),
                corpus_chunk_count=len(chunks),
                total_input_tokens=total_input_tokens,
                complete=len(existing) == len(chunks),
            )

    metadata = _write_manifest(
        manifest_path,
        expected_configuration,
        embedded_count=len(existing),
        corpus_chunk_count=len(chunks),
        total_input_tokens=total_input_tokens,
        complete=len(existing) == len(chunks),
    )
    metadata["new_embeddings"] = new_count
    return metadata


def _validate_existing_manifest(path: Path, expected: dict[str, Any]) -> None:
    if not path.exists():
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
    for key, value in expected.items():
        if payload.get(key) != value:
            raise ValueError(
                f"Embedding cache configuration mismatch for {key}. "
                "Use --rebuild to regenerate the cache."
            )


def _write_manifest(
    path: Path,
    configuration: dict[str, Any],
    embedded_count: int,
    corpus_chunk_count: int,
    total_input_tokens: int,
    complete: bool,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "updated_at": datetime.now(UTC).isoformat(),
        **configuration,
        "embedded_count": embedded_count,
        "corpus_chunk_count": corpus_chunk_count,
        "total_input_tokens": total_input_tokens,
        "complete": complete,
    }
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)
    return payload
