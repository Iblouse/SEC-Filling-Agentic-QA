from __future__ import annotations

import math
from datetime import UTC, datetime
from pathlib import Path

from edgar_qa.retrieval.bm25 import BM25Index
from edgar_qa.retrieval.models import (
    EvaluationQuestion,
    QueryEvaluation,
    RetrievalEvaluationReport,
)


def load_evaluation_questions(path: Path) -> list[EvaluationQuestion]:
    questions: list[EvaluationQuestion] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                question = EvaluationQuestion.model_validate_json(line)
            except ValueError as exc:
                raise ValueError(f"Invalid evaluation question at line {line_number}.") from exc
            if not question.relevant_chunk_ids:
                raise ValueError(
                    f"Question {question.question_id} has no relevant chunk IDs. "
                    "Label the dataset before evaluation."
                )
            questions.append(question)
    if not questions:
        raise ValueError("Evaluation dataset contains no labeled questions.")
    return questions


def evaluate_bm25(
    index: BM25Index,
    questions: list[EvaluationQuestion],
    corpus_path: Path,
    question_path: Path,
    top_k: int = 10,
) -> RetrievalEvaluationReport:
    query_results: list[QueryEvaluation] = []

    for question in questions:
        hits = index.search(question.question, top_k=top_k, filters=question.filters)
        retrieved = [hit.chunk.chunk_id for hit in hits]
        relevant = set(question.relevant_chunk_ids)
        query_results.append(
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

    count = len(query_results)
    return RetrievalEvaluationReport(
        evaluated_at=datetime.now(UTC),
        corpus_path=str(corpus_path),
        question_path=str(question_path),
        question_count=count,
        recall_at_5=sum(item.recall_at_5 for item in query_results) / count,
        recall_at_10=sum(item.recall_at_10 for item in query_results) / count,
        mean_reciprocal_rank=sum(item.reciprocal_rank for item in query_results) / count,
        ndcg_at_10=sum(item.ndcg_at_10 for item in query_results) / count,
        queries=query_results,
        configuration={"model": "bm25", "k1": index.k1, "b": index.b, "top_k": top_k},
    )


def write_evaluation_report(report: RetrievalEvaluationReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.model_dump_json(indent=2), encoding="utf-8")


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
