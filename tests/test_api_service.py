from __future__ import annotations

from edgar_qa.api.service import _excerpt, _model_calls, _total_tokens
from edgar_qa.qa.agentic_models import AgenticAnswer, CritiqueResult
from edgar_qa.qa.models import GroundedAnswer


def _answer(tokens: int) -> GroundedAnswer:
    return GroundedAnswer(
        question="Q",
        answer="A [S1]",
        citations=["S1"],
        cited_chunk_ids=["chunk-1"],
        citation_valid=True,
        model_id="model",
        total_tokens=tokens,
    )


def _critique(tokens: int) -> CritiqueResult:
    return CritiqueResult(
        verdict="accept",
        summary="Supported.",
        model_id="model",
        total_tokens=tokens,
    )


def test_token_accounting_does_not_double_count_unrevised_answer() -> None:
    initial = _answer(100)
    critique = _critique(20)
    result = AgenticAnswer(
        question="Q",
        initial_answer=initial,
        initial_critique=critique,
        revised=False,
        final_answer=initial,
        final_critique=critique,
    )
    assert _model_calls(result) == 2
    assert _total_tokens(result) == 120


def test_excerpt_is_bounded() -> None:
    excerpt = _excerpt("word " * 200, maximum=60)
    assert len(excerpt) <= 60
    assert excerpt.endswith("…")
