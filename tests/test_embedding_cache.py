from __future__ import annotations

from pathlib import Path

from edgar_qa.retrieval.embeddings import EmbeddingResult
from edgar_qa.retrieval.models import RetrievalChunk
from edgar_qa.retrieval.vector_cache import build_embedding_cache, read_embedding_cache


class FakeEmbedder:
    model_id = "fake-model"
    dimensions = 3
    normalize = True

    def __init__(self) -> None:
        self.calls = 0

    def embed(self, text: str) -> EmbeddingResult:
        self.calls += 1
        return EmbeddingResult([1.0, 0.0, 0.0], 7)


def make_chunk(chunk_id: str) -> RetrievalChunk:
    return RetrievalChunk(
        chunk_id=chunk_id,
        document_id=f"doc-{chunk_id}",
        cik="0000019617",
        company_name="JPMORGAN CHASE & CO",
        form="10-K",
        filing_date="2026-02-15",
        accession_number="0000019617-26-000001",
        primary_document="jpm.htm",
        section_id="section-1",
        section_label="item-1a",
        section_title="Risk Factors",
        section_occurrence=1,
        chunk_index=0,
        block_ids=["block-1"],
        text=f"Relevant filing text {chunk_id}",
        term_count=4,
    )


def test_embedding_cache_is_resumable(tmp_path: Path) -> None:
    corpus_path = tmp_path / "corpus.jsonl"
    corpus_path.write_text("stable corpus", encoding="utf-8")
    cache_path = tmp_path / "embeddings.jsonl"
    manifest_path = tmp_path / "manifest.json"
    chunks = [make_chunk("a"), make_chunk("b")]
    embedder = FakeEmbedder()

    first = build_embedding_cache(
        chunks,
        embedder,
        corpus_path,
        cache_path,
        manifest_path,
        maximum_new=1,
    )
    second = build_embedding_cache(
        chunks,
        embedder,
        corpus_path,
        cache_path,
        manifest_path,
    )

    assert first["embedded_count"] == 1
    assert second["embedded_count"] == 2
    assert second["complete"] is True
    assert embedder.calls == 2
    assert set(read_embedding_cache(cache_path)) == {"a", "b"}
