from edgar_qa.qa.models import EvidenceSource
from edgar_qa.qa.validation import validate_answer_citations


def _source(source_id: str, chunk_id: str) -> EvidenceSource:
    return EvidenceSource(
        source_id=source_id,
        chunk_id=chunk_id,
        document_id="doc-1",
        cik="0000019617",
        form="8-K",
        accession_number="acc-1",
        section_label="Item 7.01",
        section_title="Regulation FD Disclosure",
        rank=1,
        text="The information is furnished and is not deemed filed.",
    )


def test_supported_answer_resolves_citations_to_chunk_ids() -> None:
    citations, chunk_ids, abstained, valid, errors = validate_answer_citations(
        "The information was furnished, not filed [S1].",
        [_source("S1", "chunk-a")],
    )

    assert citations == ["S1"]
    assert chunk_ids == ["chunk-a"]
    assert abstained is False
    assert valid is True
    assert errors == []


def test_unknown_citation_is_rejected() -> None:
    _, _, _, valid, errors = validate_answer_citations(
        "The filing says this [S9].",
        [_source("S1", "chunk-a")],
    )

    assert valid is False
    assert errors


def test_abstention_requires_no_citations() -> None:
    _, _, abstained, valid, errors = validate_answer_citations(
        "INSUFFICIENT_EVIDENCE: The supplied filing excerpt does not establish the date.",
        [_source("S1", "chunk-a")],
    )

    assert abstained is True
    assert valid is True
    assert errors == []
