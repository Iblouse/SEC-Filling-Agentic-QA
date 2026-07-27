from edgar_qa.qa.critic import BedrockAnswerCritic
from edgar_qa.qa.models import EvidenceSource, GroundedAnswer


class FakeCriticRuntime:
    def converse(self, **kwargs: object) -> dict[str, object]:
        assert kwargs["modelId"] == "critic-model"
        return {
            "output": {
                "message": {
                    "content": [
                        {
                            "text": (
                                '{"verdict":"accept","summary":"Supported",'
                                '"issues":[],"should_abstain":false}'
                            )
                        }
                    ]
                }
            },
            "usage": {"inputTokens": 80, "outputTokens": 20, "totalTokens": 100},
        }


def _source() -> EvidenceSource:
    return EvidenceSource(
        source_id="S1",
        chunk_id="chunk-a",
        document_id="doc-a",
        cik="0000019617",
        form="8-K",
        accession_number="acc-a",
        section_label="Item 7.01",
        section_title="Regulation FD Disclosure",
        rank=1,
        text="The information is furnished and shall not be deemed filed.",
    )


def test_critic_returns_structured_decision() -> None:
    answer = GroundedAnswer(
        question="Filed or furnished?",
        answer="The information was furnished [S1].",
        citations=["S1"],
        cited_chunk_ids=["chunk-a"],
        citation_valid=True,
        model_id="answer-model",
    )
    critic = BedrockAnswerCritic(FakeCriticRuntime(), model_id="critic-model")

    result = critic.review(answer.question, [_source()], answer)

    assert result.verdict == "accept"
    assert result.issues == []
    assert result.total_tokens == 100
