from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from edgar_qa.qa.agentic_models import AgenticAnswer
from edgar_qa.retrieval.models import EvaluationQuestion


class AgenticQueryEvaluation(BaseModel):
    question_id: str
    question: str
    revised: bool
    initial_critic_verdict: str
    final_critic_verdict: str
    unresolved_after_revision: bool
    initial_citation_valid: bool
    final_citation_valid: bool
    initial_gold_hit: bool
    final_gold_hit: bool
    initial_cited_gold_precision: float
    final_cited_gold_precision: float
    initial_cited_gold_recall: float
    final_cited_gold_recall: float
    model_calls: int
    total_model_tokens: int
    initial_answer: str
    final_answer: str


class AgenticEvaluationReport(BaseModel):
    schema_version: str = "1.0"
    evaluated_at: datetime
    question_count: int
    revised_count: int
    revision_rate: float
    initial_critic_accept_rate: float
    final_critic_accept_rate: float
    unresolved_after_revision_rate: float
    initial_citation_validity_rate: float
    final_citation_validity_rate: float
    initial_gold_evidence_hit_rate: float
    final_gold_evidence_hit_rate: float
    initial_mean_cited_gold_precision: float
    final_mean_cited_gold_precision: float
    initial_mean_cited_gold_recall: float
    final_mean_cited_gold_recall: float
    mean_model_calls: float
    mean_model_tokens: float
    generator_model_id: str
    critic_model_id: str
    revision_model_id: str
    queries: list[AgenticQueryEvaluation]
    configuration: dict[str, Any] = Field(default_factory=dict)


def evaluate_agentic_answer(
    question: EvaluationQuestion,
    result: AgenticAnswer,
) -> AgenticQueryEvaluation:
    gold = set(question.relevant_chunk_ids)
    initial_cited = set(result.initial_answer.cited_chunk_ids)
    final_cited = set(result.final_answer.cited_chunk_ids)
    initial_gold = initial_cited & gold
    final_gold = final_cited & gold
    return AgenticQueryEvaluation(
        question_id=question.question_id,
        question=question.question,
        revised=result.revised,
        initial_critic_verdict=result.initial_critique.verdict,
        final_critic_verdict=result.final_critique.verdict,
        unresolved_after_revision=result.unresolved_after_revision,
        initial_citation_valid=result.initial_answer.citation_valid,
        final_citation_valid=result.final_answer.citation_valid,
        initial_gold_hit=bool(initial_gold),
        final_gold_hit=bool(final_gold),
        initial_cited_gold_precision=_precision(initial_gold, initial_cited),
        final_cited_gold_precision=_precision(final_gold, final_cited),
        initial_cited_gold_recall=_recall(initial_gold, gold),
        final_cited_gold_recall=_recall(final_gold, gold),
        model_calls=4 if result.revised else 2,
        total_model_tokens=_total_tokens(result),
        initial_answer=result.initial_answer.answer,
        final_answer=result.final_answer.answer,
    )


def build_agentic_report(
    results: list[AgenticQueryEvaluation],
    generator_model_id: str,
    critic_model_id: str,
    revision_model_id: str,
    configuration: dict[str, Any],
) -> AgenticEvaluationReport:
    if not results:
        raise ValueError("Agentic evaluation requires at least one question.")
    count = len(results)
    revised_count = sum(item.revised for item in results)
    return AgenticEvaluationReport(
        evaluated_at=datetime.now(UTC),
        question_count=count,
        revised_count=revised_count,
        revision_rate=revised_count / count,
        initial_critic_accept_rate=(
            sum(item.initial_critic_verdict == "accept" for item in results) / count
        ),
        final_critic_accept_rate=(
            sum(item.final_critic_verdict == "accept" for item in results) / count
        ),
        unresolved_after_revision_rate=(
            sum(item.unresolved_after_revision for item in results) / count
        ),
        initial_citation_validity_rate=(
            sum(item.initial_citation_valid for item in results) / count
        ),
        final_citation_validity_rate=(sum(item.final_citation_valid for item in results) / count),
        initial_gold_evidence_hit_rate=(sum(item.initial_gold_hit for item in results) / count),
        final_gold_evidence_hit_rate=sum(item.final_gold_hit for item in results) / count,
        initial_mean_cited_gold_precision=(
            sum(item.initial_cited_gold_precision for item in results) / count
        ),
        final_mean_cited_gold_precision=(
            sum(item.final_cited_gold_precision for item in results) / count
        ),
        initial_mean_cited_gold_recall=(
            sum(item.initial_cited_gold_recall for item in results) / count
        ),
        final_mean_cited_gold_recall=(
            sum(item.final_cited_gold_recall for item in results) / count
        ),
        mean_model_calls=sum(item.model_calls for item in results) / count,
        mean_model_tokens=sum(item.total_model_tokens for item in results) / count,
        generator_model_id=generator_model_id,
        critic_model_id=critic_model_id,
        revision_model_id=revision_model_id,
        queries=results,
        configuration=configuration,
    )


def _precision(relevant: set[str], cited: set[str]) -> float:
    return len(relevant) / len(cited) if cited else 0.0


def _recall(relevant: set[str], gold: set[str]) -> float:
    return len(relevant) / len(gold) if gold else 0.0


def _total_tokens(result: AgenticAnswer) -> int:
    total = (result.initial_answer.total_tokens or 0) + (result.initial_critique.total_tokens or 0)
    if result.revised:
        total += (result.final_answer.total_tokens or 0) + (result.final_critique.total_tokens or 0)
    return total
