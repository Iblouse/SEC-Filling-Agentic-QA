from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from botocore.exceptions import ClientError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from edgar_qa.qa.evidence import render_evidence_pack
from edgar_qa.qa.models import EvidenceSource, GroundedAnswer
from edgar_qa.qa.validation import validate_answer_citations

DEFAULT_ANSWER_MODEL = "us.amazon.nova-2-lite-v1:0"

_SYSTEM_PROMPT = (
    "You are a financial research assistant answering questions about SEC filings.\n"
    "Use ONLY the supplied evidence. Do not use outside knowledge or guess.\n"
    "Every factual claim in a supported answer must include one or more citations "
    "in the exact form [S1], [S2], etc.\n"
    "Cite only source labels that appear in the supplied evidence.\n"
    "Give a direct answer first, then a concise explanation when needed.\n"
    "If the supplied evidence is insufficient to answer reliably, respond with "
    "exactly this prefix:\n"
    "INSUFFICIENT_EVIDENCE:\n"
    "Then briefly state what evidence is missing. Do not cite sources in an "
    "insufficient-evidence response.\n"
    "Do not expose hidden reasoning or chain-of-thought.\n"
)


class AnswerGenerationError(RuntimeError):
    """Raised when a Bedrock answer cannot be produced or validated."""


class BedrockAnswerGenerator:
    """Generate citation-grounded answers with the Amazon Bedrock Converse API."""

    def __init__(
        self,
        client: Any,
        model_id: str = DEFAULT_ANSWER_MODEL,
        max_tokens: int = 700,
    ) -> None:
        if max_tokens < 64:
            raise ValueError("max_tokens must be at least 64.")
        self._client = client
        self.model_id = model_id
        self.max_tokens = max_tokens

    @retry(
        retry=retry_if_exception_type((ClientError, AnswerGenerationError)),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def answer(
        self,
        question: str,
        sources: Sequence[EvidenceSource],
    ) -> GroundedAnswer:
        cleaned = question.strip()
        if not cleaned:
            raise ValueError("Question cannot be empty.")
        if not sources:
            return GroundedAnswer(
                question=cleaned,
                answer="INSUFFICIENT_EVIDENCE: No retrieval evidence was supplied.",
                abstained=True,
                citation_valid=True,
                model_id=self.model_id,
            )

        prompt = (
            f"Question:\n{cleaned}\n\n"
            "Evidence:\n"
            f"{render_evidence_pack(sources)}\n\n"
            "Answer the question using only the evidence above."
        )
        response = self._client.converse(
            modelId=self.model_id,
            system=[{"text": _SYSTEM_PROMPT}],
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={
                "maxTokens": self.max_tokens,
                "temperature": 0.0,
            },
        )
        answer_text = _response_text(response)
        citations, chunk_ids, abstained, valid, errors = validate_answer_citations(
            answer_text, sources
        )
        usage = response.get("usage", {})
        return GroundedAnswer(
            question=cleaned,
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
            stop_reason=str(response.get("stopReason")) if response.get("stopReason") else None,
        )


def _response_text(response: dict[str, Any]) -> str:
    try:
        content = response["output"]["message"]["content"]
    except (KeyError, TypeError) as exc:
        raise AnswerGenerationError(
            "Bedrock Converse response is missing message content."
        ) from exc
    if not isinstance(content, list):
        raise AnswerGenerationError("Bedrock Converse response content is not a list.")
    text_parts = [item.get("text", "") for item in content if isinstance(item, dict)]
    answer = "\n".join(part for part in text_parts if part).strip()
    if not answer:
        raise AnswerGenerationError("Bedrock Converse returned an empty text answer.")
    return answer


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
