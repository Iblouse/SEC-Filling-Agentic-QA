from __future__ import annotations

from pathlib import Path
from typing import Any

from edgar_qa.qa.evidence import build_evidence_sources
from edgar_qa.qa.models import EvidenceSource
from edgar_qa.retrieval.bm25 import BM25Index
from edgar_qa.retrieval.corpus import read_corpus_jsonl
from edgar_qa.retrieval.dense import DenseIndex
from edgar_qa.retrieval.embeddings import DEFAULT_TITAN_EMBED_MODEL, TitanTextEmbedder
from edgar_qa.retrieval.hybrid import HybridIndex
from edgar_qa.retrieval.models import SearchFilters
from edgar_qa.retrieval.rerank import BedrockReranker
from edgar_qa.retrieval.vector_cache import read_embedding_cache


def build_hybrid_index(
    corpus: Path,
    cache: Path,
    runtime_client: Any,
    dimensions: int = 512,
    rrf_k: int = 60,
    bm25_weight: float = 1.0,
    dense_weight: float = 1.0,
) -> HybridIndex:
    chunks = read_corpus_jsonl(corpus)
    embeddings = read_embedding_cache(cache)
    missing = [chunk.chunk_id for chunk in chunks if chunk.chunk_id not in embeddings]
    if missing:
        raise ValueError(f"Embedding cache is incomplete: {len(missing)} chunk(s) are missing.")
    embedder = TitanTextEmbedder(
        runtime_client,
        model_id=DEFAULT_TITAN_EMBED_MODEL,
        dimensions=dimensions,
        normalize=True,
    )
    return HybridIndex(
        BM25Index(chunks),
        DenseIndex(chunks, embeddings, embedder),
        rrf_k=rrf_k,
        bm25_weight=bm25_weight,
        dense_weight=dense_weight,
    )


def retrieve_evidence(
    question: str,
    filters: SearchFilters,
    index: HybridIndex,
    reranker: BedrockReranker,
    candidate_k: int = 20,
    rerank_candidates: int = 10,
    evidence_k: int = 5,
) -> list[EvidenceSource]:
    if candidate_k < rerank_candidates:
        raise ValueError("candidate_k must be >= rerank_candidates.")
    if rerank_candidates < evidence_k:
        raise ValueError("rerank_candidates must be >= evidence_k.")
    candidates = index.search(
        question,
        top_k=rerank_candidates,
        candidate_k=candidate_k,
        filters=filters,
    )
    reranked = reranker.rerank(question, candidates, top_k=rerank_candidates)
    return build_evidence_sources(reranked, maximum_sources=evidence_k)
