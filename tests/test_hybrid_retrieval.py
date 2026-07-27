from __future__ import annotations

from edgar_qa.retrieval.bm25 import BM25Index
from edgar_qa.retrieval.dense import DenseIndex
from edgar_qa.retrieval.embeddings import EmbeddingResult
from edgar_qa.retrieval.hybrid import HybridIndex
from edgar_qa.retrieval.models import RetrievalChunk
from edgar_qa.retrieval.vector_cache import EmbeddingCacheRecord


class FakeEmbedder:
    model_id = "fake"
    dimensions = 2
    normalize = True

    def embed(self, text: str) -> EmbeddingResult:
        if "liquidity" in text.lower():
            return EmbeddingResult(vector=[1.0, 0.0], input_token_count=1)
        return EmbeddingResult(vector=[0.0, 1.0], input_token_count=1)


def _chunk(chunk_id: str, text: str) -> RetrievalChunk:
    return RetrievalChunk(
        chunk_id=chunk_id,
        document_id="doc",
        cik="0000019617",
        company_name="JPMorgan Chase & Co.",
        form="10-K",
        filing_date="2026-02-13",
        accession_number="0000019617-26-000001",
        primary_document="test.htm",
        section_id="section",
        section_label="Item 1A",
        section_title="Risk Factors",
        section_occurrence=1,
        chunk_index=0,
        text=text,
        term_count=len(text.split()),
    )


def test_rrf_rewards_chunks_found_by_both_retrievers() -> None:
    chunks = [
        _chunk("both", "liquidity risk and funding obligations"),
        _chunk("dense", "funding capacity concerns"),
        _chunk("lexical", "liquidity liquidity unrelated wording"),
    ]
    embeddings = {
        "both": EmbeddingCacheRecord("both", "a", 1, [1.0, 0.0]),
        "dense": EmbeddingCacheRecord("dense", "b", 1, [0.99, 0.01]),
        "lexical": EmbeddingCacheRecord("lexical", "c", 1, [0.0, 1.0]),
    }
    index = HybridIndex(
        BM25Index(chunks),
        DenseIndex(chunks, embeddings, FakeEmbedder()),
        rrf_k=60,
    )

    hits = index.search("liquidity funding", top_k=3, candidate_k=3)

    assert hits[0].chunk.chunk_id == "both"
    assert hits[0].bm25_rank is not None
    assert hits[0].dense_rank is not None


def test_candidate_k_cannot_be_smaller_than_top_k() -> None:
    chunk = _chunk("one", "liquidity risk")
    embeddings = {"one": EmbeddingCacheRecord("one", "a", 1, [1.0, 0.0])}
    index = HybridIndex(BM25Index([chunk]), DenseIndex([chunk], embeddings, FakeEmbedder()))

    try:
        index.search("liquidity", top_k=2, candidate_k=1)
    except ValueError as exc:
        assert "candidate_k" in str(exc)
    else:
        raise AssertionError("Expected candidate_k validation to fail.")
