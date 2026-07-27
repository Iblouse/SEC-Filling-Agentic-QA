from __future__ import annotations

import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from edgar_qa.retrieval.hybrid import HybridIndex
from edgar_qa.retrieval.models import (
    EvaluationQuestion,
    QueryEvaluation,
    RetrievalEvaluationReport,
)
from edgar_qa.retrieval.rerank import Reranker


def evaluate_hybrid(
    index: HybridIndex,
    questions: list[EvaluationQuestion],
    corpus_path: Path,
    question_path: Path,
    top_k: int = 10,
    candidate_k: int = 20,
) -> RetrievalEvaluationReport:
    results: list[QueryEvaluation] = []
    for question in questions:
        hits = index.search(
            question.question,
            top_k=top_k,
            candidate_k=candidate_k,
            filters=question.filters,
        )
        results.append(_query_evaluation(question, [hit.chunk.chunk_id for hit in hits]))

    return _report(
        results,
        corpus_path,
        question_path,
        configuration={
            "model": "weighted_rrf",
            "rrf_k": index.rrf_k,
            "bm25_weight": index.bm25_weight,
            "dense_weight": index.dense_weight,
            "candidate_k": candidate_k,
            "top_k": top_k,
        },
    )


def evaluate_reranked_hybrid(
    index: HybridIndex,
    reranker: Reranker,
    questions: list[EvaluationQuestion],
    corpus_path: Path,
    question_path: Path,
    top_k: int = 10,
    candidate_k: int = 20,
    rerank_candidates: int = 20,
) -> RetrievalEvaluationReport:
    if rerank_candidates < top_k:
        raise ValueError("rerank_candidates must be greater than or equal to top_k.")
    if candidate_k < rerank_candidates:
        raise ValueError("candidate_k must be greater than or equal to rerank_candidates.")

    results: list[QueryEvaluation] = []
    for question in questions:
        hybrid_hits = index.search(
            question.question,
            top_k=rerank_candidates,
            candidate_k=candidate_k,
            filters=question.filters,
        )
        hits = reranker.rerank(question.question, hybrid_hits, top_k=top_k)
        results.append(_query_evaluation(question, [hit.chunk.chunk_id for hit in hits]))

    return _report(
        results,
        corpus_path,
        question_path,
        configuration={
            "model": "weighted_rrf_then_bedrock_rerank",
            "reranker_model": reranker.model_id,
            "rrf_k": index.rrf_k,
            "bm25_weight": index.bm25_weight,
            "dense_weight": index.dense_weight,
            "candidate_k": candidate_k,
            "rerank_candidates": rerank_candidates,
            "top_k": top_k,
        },
    )


def _query_evaluation(
    question: EvaluationQuestion,
    retrieved: list[str],
) -> QueryEvaluation:
    relevant = set(question.relevant_chunk_ids)
    return QueryEvaluation(
        question_id=question.question_id,
        question=question.question,
        relevant_count=len(relevant),
        retrieved_chunk_ids=retrieved,
        recall_at_5=_recall_at_k(retrieved, relevant, 5),
        recall_at_10=_recall_at_k(retrieved, relevant, 10),
        reciprocal_rank=_reciprocal_rank(retrieved, relevant),
        ndcg_at_10=_ndcg_at_k(retrieved, relevant, 10),
    )


def _report(
    results: list[QueryEvaluation],
    corpus_path: Path,
    question_path: Path,
    configuration: dict[str, Any],
) -> RetrievalEvaluationReport:
    if not results:
        raise ValueError("Evaluation requires at least one question.")
    count = len(results)
    return RetrievalEvaluationReport(
        evaluated_at=datetime.now(UTC),
        corpus_path=str(corpus_path),
        question_path=str(question_path),
        question_count=count,
        recall_at_5=sum(item.recall_at_5 for item in results) / count,
        recall_at_10=sum(item.recall_at_10 for item in results) / count,
        mean_reciprocal_rank=sum(item.reciprocal_rank for item in results) / count,
        ndcg_at_10=sum(item.ndcg_at_10 for item in results) / count,
        queries=results,
        configuration=configuration,
    )


def _recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    return len(set(retrieved[:k]) & relevant) / len(relevant)


def _reciprocal_rank(retrieved: list[str], relevant: set[str]) -> float:
    for rank, chunk_id in enumerate(retrieved, start=1):
        if chunk_id in relevant:
            return 1.0 / rank
    return 0.0


def _ndcg_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    dcg = sum(
        1.0 / math.log2(rank + 1)
        for rank, chunk_id in enumerate(retrieved[:k], start=1)
        if chunk_id in relevant
    )
    ideal_count = min(len(relevant), k)
    ideal = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_count + 1))
    return dcg / ideal if ideal else 0.0
