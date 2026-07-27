from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from botocore.exceptions import ClientError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from edgar_qa.qa.agentic_models import CritiqueResult
from edgar_qa.qa.evidence import render_evidence_pack
from edgar_qa.qa.generator import DEFAULT_ANSWER_MODEL
from edgar_qa.qa.models import EvidenceSource, GroundedAnswer
from edgar_qa.qa.validation import validate_answer_citations

DEFAULT_REVISION_MODEL = DEFAULT_ANSWER_MODEL

_REVISION_SYSTEM_PROMPT = (
    "You revise answers to questions about SEC filings. Use ONLY the supplied "
    "evidence. Do not add outside knowledge or guess.\n"
    "Fix only genuine problems identified by the critic and produce a complete, "
    "direct final answer.\n"
    "Every factual claim in a supported answer must include citations in the exact "
    "form [S1], [S2], etc. Cite only supplied source labels.\n"
    "If the evidence is insufficient, begin exactly with INSUFFICIENT_EVIDENCE: "
    "and do not cite sources.\n"
    "Return only the revised answer. Do not discuss the revision process and do "
    "not expose hidden reasoning or chain-of-thought.\n"
)


class RevisionError(RuntimeError):
    """Raised when a revised Bedrock answer cannot be produced."""


class BedrockAnswerReviser:
    """Perform one evidence-grounded revision from a critic decision."""

    def __init__(
        self,
        client: Any,
        model_id: str = DEFAULT_REVISION_MODEL,
        max_tokens: int = 700,
    ) -> None:
        if max_tokens < 64:
            raise ValueError("max_tokens must be at least 64.")
        self._client = client
        self.model_id = model_id
        self.max_tokens = max_tokens

    @retry(
        retry=retry_if_exception_type((ClientError, RevisionError)),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def revise(
        self,
        question: str,
        sources: Sequence[EvidenceSource],
        original: GroundedAnswer,
        critique: CritiqueResult,
    ) -> GroundedAnswer:
        issues = "\n".join(f"- {issue}" for issue in critique.issues) or "- None listed"
        prompt = (
            f"Question:\n{question.strip()}\n\n"
            f"Evidence:\n{render_evidence_pack(sources)}\n\n"
            f"Original answer:\n{original.answer}\n\n"
            f"Critic summary:\n{critique.summary}\n\n"
            f"Critic issues:\n{issues}\n\n"
            f"Critic says the answer should abstain: {critique.should_abstain}\n\n"
            "Produce the final revised answer."
        )
        response = self._client.converse(
            modelId=self.model_id,
            system=[{"text": _REVISION_SYSTEM_PROMPT}],
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": self.max_tokens, "temperature": 0.0},
        )
        answer_text = _response_text(response)
        citations, chunk_ids, abstained, valid, errors = validate_answer_citations(
            answer_text, sources
        )
        usage = response.get("usage", {})
        return GroundedAnswer(
            question=question.strip(),
            answer=answer_text,
            citations=citations,
            cited_chunk_ids=chunk_ids,
            abstained=abstained,
            citation_valid=valid,
            validation_errors=errors,
            model_id=self.model_id,
            input_tokens=_optional_int(usage.get("inputTokens")),
            output_tokens=_optional_int(usage.get("outputTokens")),
            total_tokens=_optional_int(usage.get("totalTokens")),
            stop_reason=(str(response.get("stopReason")) if response.get("stopReason") else None),
        )


def _response_text(response: dict[str, Any]) -> str:
    try:
        content = response["output"]["message"]["content"]
    except (KeyError, TypeError) as exc:
        raise RevisionError("Bedrock revision response is missing message content.") from exc
    if not isinstance(content, list):
        raise RevisionError("Bedrock revision response content is not a list.")
    parts = [item.get("text", "") for item in content if isinstance(item, dict)]
    text = "\n".join(str(part) for part in parts if part).strip()
    if not text:
        raise RevisionError("Bedrock revision returned empty text.")
    return text


def _optional_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None
