from edgar_qa.qa.agentic_evaluation import (
    build_agentic_report,
    evaluate_agentic_answer,
)
from edgar_qa.qa.agentic_models import AgenticAnswer, CritiqueResult
from edgar_qa.qa.models import GroundedAnswer
from edgar_qa.retrieval.models import EvaluationQuestion


def _answer(text: str, chunk_ids: list[str], tokens: int) -> GroundedAnswer:
    return GroundedAnswer(
        question="What happened?",
        answer=text,
        citations=["S1"],
        cited_chunk_ids=chunk_ids,
        citation_valid=True,
        model_id="model",
        total_tokens=tokens,
    )


def _critique(verdict: str, tokens: int) -> CritiqueResult:
    return CritiqueResult(
        verdict=verdict,
        summary="review",
        issues=[] if verdict == "accept" else ["fix answer"],
        should_abstain=False,
        model_id="critic",
        total_tokens=tokens,
    )


def test_agentic_report_tracks_quality_and_cost() -> None:
    question = EvaluationQuestion(
        question_id="q001",
        question="What happened?",
        relevant_chunk_ids=["gold-a", "gold-b"],
    )
    result = AgenticAnswer(
        question=question.question,
        initial_answer=_answer("Initial [S1]", ["wrong"], 10),
        initial_critique=_critique("revise", 5),
        revised=True,
        final_answer=_answer("Final [S1]", ["gold-a"], 12),
        final_critique=_critique("accept", 5),
    )

    query = evaluate_agentic_answer(question, result)
    report = build_agentic_report(
        [query],
        generator_model_id="generator",
        critic_model_id="critic",
        revision_model_id="reviser",
        configuration={"max_revisions": 1},
    )

    assert query.initial_gold_hit is False
    assert query.final_gold_hit is True
    assert query.final_cited_gold_recall == 0.5
    assert query.model_calls == 4
    assert query.total_model_tokens == 32
    assert report.revision_rate == 1.0
    assert report.final_gold_evidence_hit_rate == 1.0
    assert report.mean_model_tokens == 32.0
