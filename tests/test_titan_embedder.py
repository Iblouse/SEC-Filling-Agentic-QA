from __future__ import annotations

import io
import json

from edgar_qa.retrieval.embeddings import TitanTextEmbedder


class FakeBedrockClient:
    def invoke_model(self, **kwargs: object) -> dict[str, io.BytesIO]:
        assert kwargs["modelId"] == "amazon.titan-embed-text-v2:0"
        body = json.loads(str(kwargs["body"]))
        assert body["dimensions"] == 256
        assert body["normalize"] is True
        payload = {
            "embedding": [0.1] * 256,
            "inputTextTokenCount": 5,
        }
        return {"body": io.BytesIO(json.dumps(payload).encode("utf-8"))}


def test_titan_embedder_parses_bedrock_response() -> None:
    embedder = TitanTextEmbedder(FakeBedrockClient(), dimensions=256)
    result = embedder.embed("test input")
    assert len(result.vector) == 256
    assert result.vector[0] == 0.1
    assert result.input_token_count == 5
