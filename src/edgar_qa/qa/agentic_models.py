from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from edgar_qa.qa.models import GroundedAnswer


class CritiquePayload(BaseModel):
    """Structured critic decision returned by the model."""

    verdict: Literal["accept", "revise"]
    summary: str
    issues: list[str] = Field(default_factory=list)
    should_abstain: bool = False


class CritiqueResult(CritiquePayload):
    """Critic decision plus model and usage metadata."""

    model_id: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


class AgenticAnswer(BaseModel):
    """One bounded critic/revision execution."""

    question: str
    initial_answer: GroundedAnswer
    initial_critique: CritiqueResult
    revised: bool
    final_answer: GroundedAnswer
    final_critique: CritiqueResult
    max_revisions: int = 1
    unresolved_after_revision: bool = False
