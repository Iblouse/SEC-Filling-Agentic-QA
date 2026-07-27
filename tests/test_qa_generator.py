from edgar_qa.qa.generator import BedrockAnswerGenerator
from edgar_qa.qa.models import EvidenceSource


class FakeBedrockRuntime:
    def converse(self, **kwargs: object) -> dict[str, object]:
        assert kwargs["modelId"] == "test-model"
        return {
            "output": {
                "message": {
                    "content": [{"text": "The disclosure was furnished rather than filed [S1]."}]
                }
            },
            "usage": {"inputTokens": 100, "outputTokens": 12, "totalTokens": 112},
            "stopReason": "end_turn",
        }


def _source() -> EvidenceSource:
    return EvidenceSource(
        source_id="S1",
        chunk_id="chunk-a",
        document_id="doc-1",
        cik="0000019617",
        form="8-K",
        filing_date="2026-05-21",
        accession_number="acc-1",
        section_label="Item 7.01",
        section_title="Regulation FD Disclosure",
        rank=1,
        text="The information in this item is furnished and shall not be deemed filed.",
    )


def test_generator_returns_provenance_and_usage() -> None:
    generator = BedrockAnswerGenerator(FakeBedrockRuntime(), model_id="test-model")

    answer = generator.answer("Was the information filed or furnished?", [_source()])

    assert answer.citation_valid is True
    assert answer.citations == ["S1"]
    assert answer.cited_chunk_ids == ["chunk-a"]
    assert answer.total_tokens == 112
