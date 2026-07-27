from __future__ import annotations

from edgar_qa.retrieval.dense import DenseIndex, cosine_similarity
from edgar_qa.retrieval.embeddings import EmbeddingResult
from edgar_qa.retrieval.models import RetrievalChunk, SearchFilters
from edgar_qa.retrieval.vector_cache import EmbeddingCacheRecord


class FakeEmbedder:
    model_id = "fake-embedder"
    dimensions = 3
    normalize = True

    def embed(self, text: str) -> EmbeddingResult:
        if "liquidity" in text.lower():
            return EmbeddingResult([1.0, 0.0, 0.0], 1)
        return EmbeddingResult([0.0, 1.0, 0.0], 1)


def chunk(chunk_id: str, form: str = "10-K") -> RetrievalChunk:
    return RetrievalChunk(
        chunk_id=chunk_id,
        document_id="doc-1",
        cik="0000019617",
        company_name="JPMORGAN CHASE & CO",
        form=form,
        filing_date="2026-02-15",
        accession_number="0000019617-26-000001",
        primary_document="jpm.htm",
        section_id="section-1",
        section_label="item-1a",
        section_title="Risk Factors",
        section_occurrence=1,
        chunk_index=0,
        block_ids=["block-1"],
        text=f"text for {chunk_id}",
        term_count=3,
    )


def test_cosine_similarity() -> None:
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_dense_index_ranks_semantically_closest_chunk() -> None:
    chunks = [chunk("liquidity"), chunk("capital")]
    cache = {
        "liquidity": EmbeddingCacheRecord("liquidity", "a", 1, [1.0, 0.0, 0.0]),
        "capital": EmbeddingCacheRecord("capital", "b", 1, [0.0, 1.0, 0.0]),
    }
    index = DenseIndex(chunks, cache, FakeEmbedder())

    hits = index.search("liquidity funding risk", top_k=2)

    assert hits[0].chunk.chunk_id == "liquidity"
    assert hits[0].score == 1.0


def test_dense_index_respects_filters() -> None:
    chunks = [chunk("ten-k", "10-K"), chunk("eight-k", "8-K")]
    cache = {
        "ten-k": EmbeddingCacheRecord("ten-k", "a", 1, [1.0, 0.0, 0.0]),
        "eight-k": EmbeddingCacheRecord("eight-k", "b", 1, [1.0, 0.0, 0.0]),
    }
    index = DenseIndex(chunks, cache, FakeEmbedder())

    hits = index.search("liquidity", filters=SearchFilters(form="8-K"))

    assert [hit.chunk.chunk_id for hit in hits] == ["eight-k"]
