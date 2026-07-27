from __future__ import annotations

import math
from collections.abc import Mapping

from edgar_qa.retrieval.embeddings import TextEmbedder
from edgar_qa.retrieval.models import RetrievalChunk, SearchFilters, SearchHit
from edgar_qa.retrieval.vector_cache import EmbeddingCacheRecord


class DenseIndex:
    """Transparent in-memory dense retrieval baseline using cosine similarity."""

    def __init__(
        self,
        chunks: list[RetrievalChunk],
        embeddings: Mapping[str, EmbeddingCacheRecord],
        query_embedder: TextEmbedder,
    ) -> None:
        if not chunks:
            raise ValueError("Dense retrieval requires at least one chunk.")
        self.chunks = chunks
        self.embeddings = embeddings
        self.query_embedder = query_embedder

    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: SearchFilters | None = None,
    ) -> list[SearchHit]:
        if top_k < 1:
            raise ValueError("top_k must be positive.")
        query_result = self.query_embedder.embed(query)
        query_vector = query_result.vector

        scored: list[tuple[float, RetrievalChunk]] = []
        for chunk in self.chunks:
            if not _matches_filters(chunk, filters):
                continue
            cached = self.embeddings.get(chunk.chunk_id)
            if cached is None:
                continue
            score = cosine_similarity(query_vector, cached.vector)
            scored.append((score, chunk))

        scored.sort(key=lambda item: (-item[0], item[1].chunk_id))
        return [
            SearchHit(rank=rank, score=score, chunk=chunk)
            for rank, (score, chunk) in enumerate(scored[:top_k], start=1)
        ]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("Cosine similarity requires equal, non-empty vectors.")
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def _matches_filters(chunk: RetrievalChunk, filters: SearchFilters | None) -> bool:
    if filters is None:
        return True
    if filters.cik and chunk.cik != filters.cik.zfill(10):
        return False
    if filters.form and chunk.form.upper() != filters.form.upper():
        return False
    if filters.accession_number and chunk.accession_number != filters.accession_number:
        return False
    return not (
        filters.section_label and chunk.section_label.lower() != filters.section_label.lower()
    )
