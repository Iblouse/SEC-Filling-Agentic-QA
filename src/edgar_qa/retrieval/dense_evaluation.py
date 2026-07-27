from __future__ import annotations

import math
from datetime import UTC, datetime
from pathlib import Path

from edgar_qa.retrieval.dense import DenseIndex
from edgar_qa.retrieval.models import (
    EvaluationQuestion,
    QueryEvaluation,
    RetrievalEvaluationReport,
)


def evaluate_dense(
    index: DenseIndex,
    questions: list[EvaluationQuestion],
    corpus_path: Path,
    question_path: Path,
    top_k: int = 10,
) -> RetrievalEvaluationReport:
    results: list[QueryEvaluation] = []
    for question in questions:
        hits = index.search(question.question, top_k=top_k, filters=question.filters)
        retrieved = [hit.chunk.chunk_id for hit in hits]
        relevant = set(question.relevant_chunk_ids)
        results.append(
            QueryEvaluation(
                question_id=question.question_id,
                question=question.question,
                relevant_count=len(relevant),
                retrieved_chunk_ids=retrieved,
                recall_at_5=_recall_at_k(retrieved, relevant, 5),
                recall_at_10=_recall_at_k(retrieved, relevant, 10),
                reciprocal_rank=_reciprocal_rank(retrieved, relevant),
                ndcg_at_10=_ndcg_at_k(retrieved, relevant, 10),
            )
        )

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
        configuration={
            "model": "dense_cosine",
            "embedding_model": index.query_embedder.model_id,
            "dimensions": index.query_embedder.dimensions,
            "normalize": index.query_embedder.normalize,
            "top_k": top_k,
        },
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
