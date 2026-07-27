from edgar_qa.qa.evaluation import build_qa_report, evaluate_answer
from edgar_qa.qa.models import GroundedAnswer
from edgar_qa.retrieval.models import EvaluationQuestion


def test_qa_evaluation_scores_gold_citations() -> None:
    question = EvaluationQuestion(
        question_id="q001",
        question="What risk is discussed?",
        relevant_chunk_ids=["chunk-a", "chunk-b"],
    )
    answer = GroundedAnswer(
        question=question.question,
        answer="Credit risk is discussed [S1].",
        citations=["S1"],
        cited_chunk_ids=["chunk-a"],
        citation_valid=True,
        model_id="test-model",
    )

    result = evaluate_answer(question, answer)
    report = build_qa_report([result], "test-model", {"evidence_k": 5})

    assert result.cited_gold_precision == 1.0
    assert result.cited_gold_recall == 0.5
    assert result.cites_at_least_one_gold_chunk is True
    assert report.gold_evidence_hit_rate == 1.0
    assert report.citation_validity_rate == 1.0
