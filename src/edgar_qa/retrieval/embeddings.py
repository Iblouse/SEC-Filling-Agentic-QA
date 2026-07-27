from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

from botocore.exceptions import ClientError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

DEFAULT_TITAN_EMBED_MODEL = "amazon.titan-embed-text-v2:0"
SUPPORTED_DIMENSIONS = {256, 512, 1024}


class EmbeddingError(RuntimeError):
    """Raised when an embedding request cannot be completed or validated."""


@dataclass(frozen=True)
class EmbeddingResult:
    vector: list[float]
    input_token_count: int


class TextEmbedder(Protocol):
    model_id: str
    dimensions: int
    normalize: bool

    def embed(self, text: str) -> EmbeddingResult: ...


class TitanTextEmbedder:
    """Amazon Titan Text Embeddings V2 adapter for Bedrock Runtime."""

    def __init__(
        self,
        bedrock_runtime_client: Any,
        model_id: str = DEFAULT_TITAN_EMBED_MODEL,
        dimensions: int = 512,
        normalize: bool = True,
    ) -> None:
        if dimensions not in SUPPORTED_DIMENSIONS:
            raise ValueError("Titan V2 dimensions must be one of 256, 512, or 1024.")
        self._client = bedrock_runtime_client
        self.model_id = model_id
        self.dimensions = dimensions
        self.normalize = normalize

    @retry(
        retry=retry_if_exception_type((ClientError, EmbeddingError)),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=16),
        reraise=True,
    )
    def embed(self, text: str) -> EmbeddingResult:
        cleaned = text.strip()
        if not cleaned:
            raise ValueError("Embedding input cannot be empty.")
        if len(cleaned) > 50000:
            raise ValueError("Embedding input exceeds the Titan V2 50,000-character limit.")

        response = self._client.invoke_model(
            modelId=self.model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(
                {
                    "inputText": cleaned,
                    "dimensions": self.dimensions,
                    "normalize": self.normalize,
                }
            ),
        )
        payload = json.loads(response["body"].read())
        vector = payload.get("embedding")
        if not isinstance(vector, list) or len(vector) != self.dimensions:
            raise EmbeddingError(
                f"Expected {self.dimensions} embedding dimensions from {self.model_id}."
            )
        try:
            float_vector = [float(value) for value in vector]
            token_count = int(payload.get("inputTextTokenCount", 0))
        except (TypeError, ValueError) as exc:
            raise EmbeddingError("Bedrock returned an invalid embedding payload.") from exc
        return EmbeddingResult(vector=float_vector, input_token_count=token_count)
