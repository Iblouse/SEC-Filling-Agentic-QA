from typing import cast

from edgar_qa.qa.agent import BoundedCritiqueAgent
from edgar_qa.qa.agentic_models import CritiqueResult
from edgar_qa.qa.critic import BedrockAnswerCritic
from edgar_qa.qa.generator import BedrockAnswerGenerator
from edgar_qa.qa.models import EvidenceSource, GroundedAnswer
from edgar_qa.qa.reviser import BedrockAnswerReviser


class StubGenerator:
    def answer(self, question: str, sources: list[EvidenceSource]) -> GroundedAnswer:
        return GroundedAnswer(
            question=question,
            answer="It was filed [S1].",
            citations=["S1"],
            cited_chunk_ids=[sources[0].chunk_id],
            citation_valid=True,
            model_id="generator",
            total_tokens=10,
        )


class StubCritic:
    def __init__(self) -> None:
        self.calls = 0

    def review(
        self,
        question: str,
        sources: list[EvidenceSource],
        answer: GroundedAnswer,
    ) -> CritiqueResult:
        self.calls += 1
        if self.calls == 1:
            return CritiqueResult(
                verdict="revise",
                summary="The answer reverses the filing status.",
                issues=["State that the information was furnished, not filed."],
                should_abstain=False,
                model_id="critic",
                total_tokens=10,
            )
        return CritiqueResult(
            verdict="accept",
            summary="The revision is supported.",
            issues=[],
            should_abstain=False,
            model_id="critic",
            total_tokens=10,
        )


class StubReviser:
    def revise(
        self,
        question: str,
        sources: list[EvidenceSource],
        original: GroundedAnswer,
        critique: CritiqueResult,
    ) -> GroundedAnswer:
        return GroundedAnswer(
            question=question,
            answer="It was furnished, not filed [S1].",
            citations=["S1"],
            cited_chunk_ids=[sources[0].chunk_id],
            citation_valid=True,
            model_id="reviser",
            total_tokens=10,
        )


def _source() -> EvidenceSource:
    return EvidenceSource(
        source_id="S1",
        chunk_id="chunk-a",
        document_id="doc-a",
        cik="0000019617",
        form="8-K",
        accession_number="acc-a",
        section_label="Item 7.01",
        section_title="Regulation FD Disclosure",
        rank=1,
        text="The information is furnished and shall not be deemed filed.",
    )


def test_agent_performs_at_most_one_revision() -> None:
    critic = StubCritic()
    agent = BoundedCritiqueAgent(
        cast(BedrockAnswerGenerator, StubGenerator()),
        cast(BedrockAnswerCritic, critic),
        cast(BedrockAnswerReviser, StubReviser()),
    )

    result = agent.answer("Filed or furnished?", [_source()])

    assert result.revised is True
    assert result.final_answer.answer.startswith("It was furnished")
    assert result.final_critique.verdict == "accept"
    assert result.unresolved_after_revision is False
    assert critic.calls == 2
