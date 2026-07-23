from datetime import UTC, datetime

from edgar_qa.parsing.models import (
    BlockKind,
    CuratedFilingDocument,
    DocumentBlock,
    FilingIdentity,
    ParsedSection,
    ParsingDiagnostics,
)
from edgar_qa.retrieval.chunking import SectionAwareChunker


def document_fixture() -> CuratedFilingDocument:
    filing = FilingIdentity(
        cik="0000019617",
        accession_number="0000019617-26-000001",
        form="10-K",
        filing_date="2026-02-15",
        primary_document="jpm.htm",
        company_name="JPMorgan Chase & Co.",
    )
    blocks = [
        DocumentBlock(block_id="b1", order=0, kind=BlockKind.HEADING, text="Item 1A Risk Factors"),
        DocumentBlock(
            block_id="b2",
            order=1,
            kind=BlockKind.PARAGRAPH,
            text="Commercial real estate credit risk increased during the year.",
        ),
        DocumentBlock(
            block_id="b3",
            order=2,
            kind=BlockKind.HEADING,
            text="Item 3 Legal Proceedings",
        ),
        DocumentBlock(
            block_id="b4",
            order=3,
            kind=BlockKind.PARAGRAPH,
            text="The company described several pending legal proceedings.",
        ),
    ]
    sections = [
        ParsedSection(
            section_id="s1",
            label="item-1a",
            title="Item 1A Risk Factors",
            occurrence=1,
            start_block=0,
            end_block=1,
            block_ids=["b1", "b2"],
        ),
        ParsedSection(
            section_id="s2",
            label="item-3",
            title="Item 3 Legal Proceedings",
            occurrence=1,
            start_block=2,
            end_block=3,
            block_ids=["b3", "b4"],
        ),
    ]
    return CuratedFilingDocument(
        parser_version="test",
        parsed_at=datetime(2026, 7, 20, tzinfo=UTC),
        source_bucket="curated",
        source_key="documents/test.json",
        source_sha256="a" * 64,
        filing=filing,
        blocks=blocks,
        sections=sections,
        diagnostics=ParsingDiagnostics(
            input_bytes=1000,
            total_characters=200,
            block_count=4,
            paragraph_count=2,
            heading_count=2,
            table_count=0,
            section_count=2,
            skipped_element_count=0,
        ),
    )


def test_chunker_preserves_section_boundaries_and_stable_ids() -> None:
    chunker = SectionAwareChunker(maximum_terms=50, overlap_terms=10)
    first = chunker.chunk_document(document_fixture())
    second = chunker.chunk_document(document_fixture())

    assert len(first) == 2
    assert [chunk.section_label for chunk in first] == ["item-1a", "item-3"]
    assert [chunk.chunk_id for chunk in first] == [chunk.chunk_id for chunk in second]
    assert all(chunk.term_count > 0 for chunk in first)
