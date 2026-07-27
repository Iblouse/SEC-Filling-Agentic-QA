from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from botocore.exceptions import ClientError
from pydantic import ValidationError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from edgar_qa.qa.agentic_models import CritiquePayload, CritiqueResult
from edgar_qa.qa.evidence import render_evidence_pack
from edgar_qa.qa.generator import DEFAULT_ANSWER_MODEL
from edgar_qa.qa.models import EvidenceSource, GroundedAnswer

DEFAULT_CRITIC_MODEL = DEFAULT_ANSWER_MODEL

_CRITIC_SYSTEM_PROMPT = (
    "You are a strict SEC-filing answer reviewer. Review only observable answer "
    "quality against the supplied evidence. Do not use outside knowledge.\n"
    "Return JSON only with exactly these keys: verdict, summary, issues, "
    "should_abstain.\n"
    'verdict must be either "accept" or "revise".\n'
    "Request revision when the answer is unsupported, materially incomplete, "
    "misstates the evidence, uses citations that do not support its claims, or "
    "should abstain.\n"
    "Accept when the answer directly addresses the question, is supported by the "
    "evidence, and uses appropriate citations.\n"
    "issues must be a JSON array of short, actionable strings.\n"
    "Do not provide hidden reasoning or chain-of-thought.\n"
)


class CritiqueError(RuntimeError):
    """Raised when the critic response cannot be produced or parsed."""


class BedrockAnswerCritic:
    """Review grounded SEC answers with a structured Bedrock critic."""

    def __init__(
        self,
        client: Any,
        model_id: str = DEFAULT_CRITIC_MODEL,
        max_tokens: int = 500,
    ) -> None:
        if max_tokens < 64:
            raise ValueError("max_tokens must be at least 64.")
        self._client = client
        self.model_id = model_id
        self.max_tokens = max_tokens

    @retry(
        retry=retry_if_exception_type((ClientError, CritiqueError)),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def review(
        self,
        question: str,
        sources: Sequence[EvidenceSource],
        answer: GroundedAnswer,
    ) -> CritiqueResult:
        prompt = (
            f"Question:\n{question.strip()}\n\n"
            f"Evidence:\n{render_evidence_pack(sources)}\n\n"
            f"Candidate answer:\n{answer.answer}\n\n"
            f"Deterministic citation validation passed: {answer.citation_valid}\n"
            "Return the required JSON critique."
        )
        response = self._client.converse(
            modelId=self.model_id,
            system=[{"text": _CRITIC_SYSTEM_PROMPT}],
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": self.max_tokens, "temperature": 0.0},
        )
        payload = _parse_payload(_response_text(response))
        usage = response.get("usage", {})
        return CritiqueResult(
            **payload.model_dump(),
            model_id=self.model_id,
            input_tokens=_optional_int(usage.get("inputTokens")),
            output_tokens=_optional_int(usage.get("outputTokens")),
            total_tokens=_optional_int(usage.get("totalTokens")),
        )


def _parse_payload(text: str) -> CritiquePayload:
    cleaned = text.strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end < start:
        raise CritiqueError("Critic response did not contain a JSON object.")
    try:
        raw = json.loads(cleaned[start : end + 1])
        if isinstance(raw, dict) and isinstance(raw.get("verdict"), str):
            raw["verdict"] = raw["verdict"].strip().lower()
        return CritiquePayload.model_validate(raw)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise CritiqueError("Critic response JSON did not match the expected schema.") from exc


def _response_text(response: dict[str, Any]) -> str:
    try:
        content = response["output"]["message"]["content"]
    except (KeyError, TypeError) as exc:
        raise CritiqueError("Bedrock critic response is missing message content.") from exc
    if not isinstance(content, list):
        raise CritiqueError("Bedrock critic response content is not a list.")
    parts = [item.get("text", "") for item in content if isinstance(item, dict)]
    text = "\n".join(str(part) for part in parts if part).strip()
    if not text:
        raise CritiqueError("Bedrock critic returned empty text.")
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
