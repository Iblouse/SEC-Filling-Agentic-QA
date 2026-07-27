from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from edgar_qa.qa.models import GroundedAnswer
from edgar_qa.retrieval.models import EvaluationQuestion


class QAQueryEvaluation(BaseModel):
    question_id: str
    question: str
    abstained: bool
    citation_valid: bool
    citations: list[str] = Field(default_factory=list)
    cited_chunk_ids: list[str] = Field(default_factory=list)
    gold_relevant_count: int
    cited_gold_count: int
    cited_gold_precision: float
    cited_gold_recall: float
    cites_at_least_one_gold_chunk: bool
    answer: str


class QAEvaluationReport(BaseModel):
    schema_version: str = "1.0"
    evaluated_at: datetime
    question_count: int
    answered_count: int
    abstention_rate: float
    citation_validity_rate: float
    gold_evidence_hit_rate: float
    mean_cited_gold_precision: float
    mean_cited_gold_recall: float
    model_id: str
    queries: list[QAQueryEvaluation]
    configuration: dict[str, Any] = Field(default_factory=dict)


def evaluate_answer(
    question: EvaluationQuestion,
    answer: GroundedAnswer,
) -> QAQueryEvaluation:
    gold = set(question.relevant_chunk_ids)
    cited = set(answer.cited_chunk_ids)
    cited_gold = cited & gold
    precision = len(cited_gold) / len(cited) if cited else 0.0
    recall = len(cited_gold) / len(gold) if gold else 0.0
    return QAQueryEvaluation(
        question_id=question.question_id,
        question=question.question,
        abstained=answer.abstained,
        citation_valid=answer.citation_valid,
        citations=answer.citations,
        cited_chunk_ids=answer.cited_chunk_ids,
        gold_relevant_count=len(gold),
        cited_gold_count=len(cited_gold),
        cited_gold_precision=precision,
        cited_gold_recall=recall,
        cites_at_least_one_gold_chunk=bool(cited_gold),
        answer=answer.answer,
    )


def build_qa_report(
    results: list[QAQueryEvaluation],
    model_id: str,
    configuration: dict[str, Any],
) -> QAEvaluationReport:
    if not results:
        raise ValueError("QA evaluation requires at least one question.")
    count = len(results)
    answered = sum(not item.abstained for item in results)
    return QAEvaluationReport(
        evaluated_at=datetime.now(UTC),
        question_count=count,
        answered_count=answered,
        abstention_rate=sum(item.abstained for item in results) / count,
        citation_validity_rate=sum(item.citation_valid for item in results) / count,
        gold_evidence_hit_rate=sum(item.cites_at_least_one_gold_chunk for item in results) / count,
        mean_cited_gold_precision=sum(item.cited_gold_precision for item in results) / count,
        mean_cited_gold_recall=sum(item.cited_gold_recall for item in results) / count,
        model_id=model_id,
        queries=results,
        configuration=configuration,
    )
