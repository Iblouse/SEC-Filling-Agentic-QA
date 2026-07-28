from __future__ import annotations

import time
from collections.abc import Sequence
from typing import Protocol

import boto3
from botocore.exceptions import ClientError

from edgar_qa.api.models import AnswerRequest, AnswerResponse, CitationSource
from edgar_qa.api.settings import APISettings
from edgar_qa.qa.agent import BoundedCritiqueAgent
from edgar_qa.qa.agentic_models import AgenticAnswer, CritiqueResult
from edgar_qa.qa.critic import BedrockAnswerCritic, CritiqueError
from edgar_qa.qa.generator import AnswerGenerationError, BedrockAnswerGenerator
from edgar_qa.qa.models import EvidenceSource, GroundedAnswer
from edgar_qa.qa.pipeline import build_hybrid_index, retrieve_evidence
from edgar_qa.qa.reviser import BedrockAnswerReviser, RevisionError
from edgar_qa.retrieval.embeddings import EmbeddingError
from edgar_qa.retrieval.hybrid import HybridIndex
from edgar_qa.retrieval.models import SearchFilters
from edgar_qa.retrieval.rerank import BedrockReranker, RerankError


class ServiceDependencyError(RuntimeError):
    """Raised when an upstream AWS model or reranking dependency fails."""


class AnswerService(Protocol):
    def answer(self, request_id: str, request: AnswerRequest) -> AnswerResponse: ...


class QAService:
    """Long-lived API service that reuses the retrieval index across requests."""

    def __init__(
        self,
        settings: APISettings,
        agent: BoundedCritiqueAgent,
        reranker: BedrockReranker,
        index: HybridIndex,
    ) -> None:
        self.settings = settings
        self.agent = agent
        self.reranker = reranker
        self.index = index

    @classmethod
    def build(cls, settings: APISettings | None = None) -> QAService:
        resolved = settings or APISettings()
        if not resolved.qa_corpus_path.exists():
            raise ValueError(f"Corpus does not exist: {resolved.qa_corpus_path}")
        if not resolved.qa_embedding_cache_path.exists():
            raise ValueError(f"Embedding cache does not exist: {resolved.qa_embedding_cache_path}")

        session = boto3.Session(region_name=resolved.aws_region)
        runtime_client = session.client("bedrock-runtime")
        agent_runtime_client = session.client("bedrock-agent-runtime")
        index = build_hybrid_index(
            resolved.qa_corpus_path,
            resolved.qa_embedding_cache_path,
            runtime_client,
            dimensions=resolved.qa_embedding_dimensions,
            rrf_k=resolved.qa_rrf_k,
            bm25_weight=resolved.qa_bm25_weight,
            dense_weight=resolved.qa_dense_weight,
        )
        reranker = BedrockReranker(agent_runtime_client, resolved.aws_region)
        agent = BoundedCritiqueAgent(
            BedrockAnswerGenerator(
                runtime_client,
                model_id=resolved.qa_generator_model_id,
            ),
            BedrockAnswerCritic(
                runtime_client,
                model_id=resolved.qa_critic_model_id,
            ),
            BedrockAnswerReviser(
                runtime_client,
                model_id=resolved.qa_revision_model_id,
            ),
        )
        return cls(resolved, agent, reranker, index)

    def answer(self, request_id: str, request: AnswerRequest) -> AnswerResponse:
        started = time.perf_counter()
        filters = SearchFilters(
            cik=request.filters.cik,
            form=request.filters.form,
            accession_number=request.filters.accession_number,
            section_label=request.filters.section_label,
        )
        try:
            sources = retrieve_evidence(
                request.question,
                filters,
                self.index,
                self.reranker,
                candidate_k=self.settings.qa_candidate_k,
                rerank_candidates=self.settings.qa_rerank_candidates,
                evidence_k=self.settings.qa_evidence_k,
            )
            result = self.agent.answer(request.question, sources)
        except (
            ClientError,
            AnswerGenerationError,
            CritiqueError,
            RevisionError,
            EmbeddingError,
            RerankError,
        ) as exc:
            raise ServiceDependencyError("An AWS QA dependency failed.") from exc

        latency_ms = (time.perf_counter() - started) * 1000
        return _build_response(request_id, result, sources, latency_ms)


def _build_response(
    request_id: str,
    result: AgenticAnswer,
    sources: Sequence[EvidenceSource],
    latency_ms: float,
) -> AnswerResponse:
    final = result.final_answer
    source_by_id = {source.source_id: source for source in sources}
    cited_sources = [
        _citation_source(source_by_id[source_id])
        for source_id in final.citations
        if source_id in source_by_id
    ]
    return AnswerResponse(
        request_id=request_id,
        question=result.question,
        answer=final.answer,
        abstained=final.abstained,
        revised=result.revised,
        unresolved_after_revision=result.unresolved_after_revision,
        citation_valid=final.citation_valid,
        critic_verdict=result.final_critique.verdict,
        citations=cited_sources,
        model_calls=_model_calls(result),
        total_tokens=_total_tokens(result),
        latency_ms=round(latency_ms, 2),
    )


def _citation_source(source: EvidenceSource) -> CitationSource:
    return CitationSource(
        source_id=source.source_id,
        chunk_id=source.chunk_id,
        cik=source.cik,
        company_name=source.company_name,
        form=source.form,
        filing_date=source.filing_date,
        accession_number=source.accession_number,
        section_label=source.section_label,
        section_title=source.section_title,
        excerpt=_excerpt(source.text),
    )


def _excerpt(text: str, maximum: int = 500) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= maximum:
        return cleaned
    return f"{cleaned[: maximum - 1].rstrip()}…"


def _model_calls(result: AgenticAnswer) -> int:
    return 4 if result.revised else 2


def _total_tokens(result: AgenticAnswer) -> int | None:
    calls: list[GroundedAnswer | CritiqueResult] = [
        result.initial_answer,
        result.initial_critique,
    ]
    if result.revised:
        calls.extend([result.final_answer, result.final_critique])
    values = [call.total_tokens for call in calls if call.total_tokens is not None]
    return sum(values) if values else None
