from __future__ import annotations

from collections.abc import Sequence

from edgar_qa.qa.agentic_models import AgenticAnswer
from edgar_qa.qa.critic import BedrockAnswerCritic
from edgar_qa.qa.generator import BedrockAnswerGenerator
from edgar_qa.qa.models import EvidenceSource
from edgar_qa.qa.reviser import BedrockAnswerReviser


class BoundedCritiqueAgent:
    """Generate, critique, and perform at most one answer revision."""

    def __init__(
        self,
        generator: BedrockAnswerGenerator,
        critic: BedrockAnswerCritic,
        reviser: BedrockAnswerReviser,
    ) -> None:
        self.generator = generator
        self.critic = critic
        self.reviser = reviser

    def answer(
        self,
        question: str,
        sources: Sequence[EvidenceSource],
    ) -> AgenticAnswer:
        initial = self.generator.answer(question, sources)
        initial_critique = self.critic.review(question, sources, initial)
        needs_revision = initial_critique.verdict == "revise" or not initial.citation_valid

        if not needs_revision:
            return AgenticAnswer(
                question=question.strip(),
                initial_answer=initial,
                initial_critique=initial_critique,
                revised=False,
                final_answer=initial,
                final_critique=initial_critique,
                unresolved_after_revision=False,
            )

        revised = self.reviser.revise(question, sources, initial, initial_critique)
        final_critique = self.critic.review(question, sources, revised)
        unresolved = final_critique.verdict == "revise" or not revised.citation_valid
        return AgenticAnswer(
            question=question.strip(),
            initial_answer=initial,
            initial_critique=initial_critique,
            revised=True,
            final_answer=revised,
            final_critique=final_critique,
            unresolved_after_revision=unresolved,
        )
