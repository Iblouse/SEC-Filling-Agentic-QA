from __future__ import annotations

from dataclasses import dataclass

from edgar_qa.retrieval.bm25 import BM25Index
from edgar_qa.retrieval.dense import DenseIndex
from edgar_qa.retrieval.models import RetrievalChunk, SearchFilters


@dataclass(frozen=True)
class HybridSearchHit:
    rank: int
    rrf_score: float
    chunk: RetrievalChunk
    bm25_rank: int | None
    dense_rank: int | None


class HybridIndex:
    """Fuse BM25 and dense rankings with weighted Reciprocal Rank Fusion."""

    def __init__(
        self,
        bm25_index: BM25Index,
        dense_index: DenseIndex,
        rrf_k: int = 60,
        bm25_weight: float = 1.0,
        dense_weight: float = 1.0,
    ) -> None:
        if rrf_k < 1:
            raise ValueError("rrf_k must be positive.")
        if bm25_weight <= 0 or dense_weight <= 0:
            raise ValueError("RRF weights must be positive.")
        self.bm25_index = bm25_index
        self.dense_index = dense_index
        self.rrf_k = rrf_k
        self.bm25_weight = bm25_weight
        self.dense_weight = dense_weight

    def search(
        self,
        query: str,
        top_k: int = 10,
        candidate_k: int = 20,
        filters: SearchFilters | None = None,
    ) -> list[HybridSearchHit]:
        if top_k < 1:
            raise ValueError("top_k must be positive.")
        if candidate_k < top_k:
            raise ValueError("candidate_k must be greater than or equal to top_k.")

        bm25_hits = self.bm25_index.search(query, top_k=candidate_k, filters=filters)
        dense_hits = self.dense_index.search(query, top_k=candidate_k, filters=filters)

        chunks: dict[str, RetrievalChunk] = {}
        bm25_ranks: dict[str, int] = {}
        dense_ranks: dict[str, int] = {}
        scores: dict[str, float] = {}

        for hit in bm25_hits:
            chunk_id = hit.chunk.chunk_id
            chunks[chunk_id] = hit.chunk
            bm25_ranks[chunk_id] = hit.rank
            scores[chunk_id] = scores.get(chunk_id, 0.0) + self.bm25_weight / (
                self.rrf_k + hit.rank
            )

        for hit in dense_hits:
            chunk_id = hit.chunk.chunk_id
            chunks[chunk_id] = hit.chunk
            dense_ranks[chunk_id] = hit.rank
            scores[chunk_id] = scores.get(chunk_id, 0.0) + self.dense_weight / (
                self.rrf_k + hit.rank
            )

        ordered = sorted(
            scores,
            key=lambda chunk_id: (-scores[chunk_id], chunk_id),
        )
        return [
            HybridSearchHit(
                rank=rank,
                rrf_score=scores[chunk_id],
                chunk=chunks[chunk_id],
                bm25_rank=bm25_ranks.get(chunk_id),
                dense_rank=dense_ranks.get(chunk_id),
            )
            for rank, chunk_id in enumerate(ordered[:top_k], start=1)
        ]
