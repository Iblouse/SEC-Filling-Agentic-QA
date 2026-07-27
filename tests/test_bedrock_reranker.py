from __future__ import annotations

from typing import Any

from edgar_qa.retrieval.hybrid import HybridSearchHit
from edgar_qa.retrieval.models import RetrievalChunk
from edgar_qa.retrieval.rerank import BedrockReranker


class FakeRerankClient:
    def __init__(self) -> None:
        self.request: dict[str, Any] | None = None

    def rerank(self, **kwargs: Any) -> dict[str, Any]:
        self.request = kwargs
        return {
            "results": [
                {"index": 1, "relevanceScore": 0.98},
                {"index": 0, "relevanceScore": 0.40},
            ]
        }


def _chunk(chunk_id: str, text: str) -> RetrievalChunk:
    return RetrievalChunk(
        chunk_id=chunk_id,
        document_id="doc",
        cik="0000019617",
        company_name="JPMorgan Chase & Co.",
        form="8-K",
        filing_date="2026-05-21",
        accession_number="0000019617-26-000002",
        primary_document="test.htm",
        section_id="section",
        section_label="Item 7.01",
        section_title="Regulation FD Disclosure",
        section_occurrence=1,
        chunk_index=0,
        text=text,
        term_count=len(text.split()),
    )


def test_bedrock_reranker_maps_original_source_indexes() -> None:
    client = FakeRerankClient()
    reranker = BedrockReranker(client, "us-east-1")
    candidates = [
        HybridSearchHit(1, 0.03, _chunk("a", "less relevant"), 1, 2),
        HybridSearchHit(2, 0.02, _chunk("b", "furnished not filed"), 3, 1),
    ]

    hits = reranker.rerank("Was it furnished or filed?", candidates, top_k=2)

    assert [hit.chunk.chunk_id for hit in hits] == ["b", "a"]
    assert hits[0].hybrid_rank == 2
    assert reranker.model_arn.endswith("foundation-model/cohere.rerank-v3-5:0")
    assert client.request is not None
    assert (
        client.request["rerankingConfiguration"]["bedrockRerankingConfiguration"]["numberOfResults"]
        == 2
    )
