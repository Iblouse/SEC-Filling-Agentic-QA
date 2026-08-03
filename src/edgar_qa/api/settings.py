from __future__ import annotations

from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from edgar_qa.qa.critic import DEFAULT_CRITIC_MODEL
from edgar_qa.qa.generator import DEFAULT_ANSWER_MODEL
from edgar_qa.qa.reviser import DEFAULT_REVISION_MODEL


class APISettings(BaseSettings):
    """Runtime configuration for the FastAPI service."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    aws_region: str = "us-east-1"
    qa_corpus_path: Path = Path("data/retrieval/sec_chunks.jsonl")
    qa_embedding_cache_path: Path = Path("data/retrieval/titan_v2_512_embeddings.jsonl")
    qa_artifact_bucket: str | None = None
    qa_artifact_manifest_key: str = "runtime/api/manifest.json"
    qa_artifact_directory: Path = Path("/tmp/edgar-qa")
    qa_candidate_k: int = Field(default=20, ge=5, le=100)
    qa_rerank_candidates: int = Field(default=10, ge=5, le=50)
    qa_evidence_k: int = Field(default=5, ge=1, le=10)
    qa_rrf_k: int = Field(default=60, ge=1)
    qa_bm25_weight: float = Field(default=1.0, gt=0)
    qa_dense_weight: float = Field(default=1.0, gt=0)
    qa_embedding_dimensions: int = Field(default=512, ge=1)
    qa_generator_model_id: str = DEFAULT_ANSWER_MODEL
    qa_critic_model_id: str = DEFAULT_CRITIC_MODEL
    qa_revision_model_id: str = DEFAULT_REVISION_MODEL

    qa_feedback_table_name: str | None = None
    qa_feedback_ttl_days: int = Field(default=90, ge=1, le=365)
    qa_metrics_namespace: str = "SECQA"
    qa_service_name: str = "sec-filing-agentic-qa"
    qa_environment: str = "portfolio"

    @model_validator(mode="after")
    def validate_retrieval_depths(self) -> APISettings:
        if self.qa_candidate_k < self.qa_rerank_candidates:
            raise ValueError("QA_CANDIDATE_K must be >= QA_RERANK_CANDIDATES.")
        if self.qa_rerank_candidates < self.qa_evidence_k:
            raise ValueError("QA_RERANK_CANDIDATES must be >= QA_EVIDENCE_K.")
        return self
