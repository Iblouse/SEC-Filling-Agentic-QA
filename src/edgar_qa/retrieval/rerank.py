from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from botocore.exceptions import ClientError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from edgar_qa.retrieval.hybrid import HybridSearchHit
from edgar_qa.retrieval.models import RetrievalChunk

DEFAULT_COHERE_RERANK_MODEL = "cohere.rerank-v3-5:0"


class RerankError(RuntimeError):
    """Raised when Bedrock reranking cannot be completed or validated."""


@dataclass(frozen=True)
class RerankedSearchHit:
    rank: int
    relevance_score: float
    chunk: RetrievalChunk
    hybrid_rank: int
    bm25_rank: int | None
    dense_rank: int | None


class Reranker(Protocol):
    model_id: str

    def rerank(
        self,
        query: str,
        candidates: list[HybridSearchHit],
        top_k: int,
    ) -> list[RerankedSearchHit]: ...


class BedrockReranker:
    """Direct Amazon Bedrock Rerank API adapter for textual SEC chunks."""

    def __init__(
        self,
        client: Any,
        region: str,
        model_id: str = DEFAULT_COHERE_RERANK_MODEL,
    ) -> None:
        self._client = client
        self.region = region
        self.model_id = model_id
        self.model_arn = f"arn:aws:bedrock:{region}::foundation-model/{model_id}"

    @retry(
        retry=retry_if_exception_type((ClientError, RerankError)),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def rerank(
        self,
        query: str,
        candidates: list[HybridSearchHit],
        top_k: int,
    ) -> list[RerankedSearchHit]:
        cleaned = query.strip()
        if not cleaned:
            raise ValueError("Rerank query cannot be empty.")
        if not candidates:
            return []
        if top_k < 1:
            raise ValueError("top_k must be positive.")

        result_count = min(top_k, len(candidates))
        response = self._client.rerank(
            queries=[{"type": "TEXT", "textQuery": {"text": cleaned}}],
            sources=[
                {
                    "type": "INLINE",
                    "inlineDocumentSource": {
                        "type": "TEXT",
                        "textDocument": {"text": _rerank_document(candidate)},
                    },
                }
                for candidate in candidates
            ],
            rerankingConfiguration={
                "type": "BEDROCK_RERANKING_MODEL",
                "bedrockRerankingConfiguration": {
                    "modelConfiguration": {"modelArn": self.model_arn},
                    "numberOfResults": result_count,
                },
            },
        )

        raw_results = response.get("results")
        if not isinstance(raw_results, list):
            raise RerankError("Bedrock rerank response did not contain a results list.")

        reranked: list[RerankedSearchHit] = []
        for rank, result in enumerate(raw_results, start=1):
            if not isinstance(result, dict):
                raise RerankError("Bedrock rerank returned an invalid result.")
            try:
                source_index = int(result["index"])
                relevance_score = float(result["relevanceScore"])
                candidate = candidates[source_index]
            except (IndexError, KeyError, TypeError, ValueError) as exc:
                raise RerankError(
                    "Bedrock rerank returned an invalid source index or score."
                ) from exc
            reranked.append(
                RerankedSearchHit(
                    rank=rank,
                    relevance_score=relevance_score,
                    chunk=candidate.chunk,
                    hybrid_rank=candidate.rank,
                    bm25_rank=candidate.bm25_rank,
                    dense_rank=candidate.dense_rank,
                )
            )
        return reranked


def _rerank_document(candidate: HybridSearchHit) -> str:
    chunk = candidate.chunk
    company = chunk.company_name or f"CIK {chunk.cik}"
    return (
        f"Company: {company}\n"
        f"Form: {chunk.form}\n"
        f"Filed: {chunk.filing_date or 'unknown'}\n"
        f"Section: {chunk.section_label} {chunk.section_title}\n"
        f"Text: {chunk.text}"
    )
