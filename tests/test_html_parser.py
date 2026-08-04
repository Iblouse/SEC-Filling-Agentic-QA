from __future__ import annotations

from datetime import UTC, datetime

from edgar_qa.parsing.html_parser import SecHtmlDocumentParser
from edgar_qa.parsing.models import BlockKind, FilingIdentity


def filing(form: str = "10-K") -> FilingIdentity:
    return FilingIdentity(
        cik="0000019617",
        accession_number="000001961726000001",
        form=form,
        filing_date="2026-02-15",
        primary_document="jpm-20251231.htm",
        company_name="JPMORGAN CHASE & CO",
    )


def test_parser_extracts_blocks_tables_sections_and_ignores_hidden_content() -> None:
    html = b"""
    <html>
      <head><title>JPMorgan Annual Report</title><style>.x{display:none}</style></head>
      <body>
        <div>Table of Contents</div>
        <h2>Item 1. Business</h2>
        <p>JPMorgan provides financial services.</p>
        <table>
          <tr><th>Year</th><th>Revenue</th></tr>
          <tr><td>2025</td><td>100</td></tr>
        </table>
        <h2>Item 1A. Risk Factors</h2>
        <p>Credit risk may increase losses.</p>
        <div hidden>secret hidden text</div>
        <script>bad()</script>
      </body>
    </html>
    """

    parser = SecHtmlDocumentParser()
    result = parser.parse(
        body=html,
        source_bucket="raw-bucket",
        source_key="filings/test.htm",
        source_sha256="a" * 64,
        filing=filing(),
        parsed_at=datetime(2026, 7, 20, tzinfo=UTC),
    )

    assert result.document_title == "JPMorgan Annual Report"
    assert any(block.kind == BlockKind.TABLE for block in result.blocks)
    assert [section.label for section in result.sections if section.label != "preamble"] == [
        "item-1",
        "item-1a",
    ]
    assert "secret hidden text" not in " ".join(block.text for block in result.blocks)
    assert result.diagnostics.table_count == 1
    assert result.diagnostics.skipped_element_count >= 3


def test_parser_detects_8k_item_numbers() -> None:
    html = b"""
    <html><body>
      <div>Item 1.01 Entry into a Material Definitive Agreement</div>
      <p>The company entered an agreement.</p>
      <div>Item 9.01 Financial Statements and Exhibits</div>
      <p>Exhibit 99.1 is furnished.</p>
    </body></html>
    """
    result = SecHtmlDocumentParser().parse(
        body=html,
        source_bucket="raw",
        source_key="filings/test.htm",
        source_sha256="b" * 64,
        filing=filing("8-K"),
    )

    assert [section.label for section in result.sections] == ["item-1.01", "item-9.01"]


def test_parser_ids_are_deterministic() -> None:
    html = b"<html><body><h2>Item 1. Business</h2><p>Text</p></body></html>"
    parser = SecHtmlDocumentParser()
    first = parser.parse(
        body=html,
        source_bucket="raw",
        source_key="filings/test.htm",
        source_sha256="c" * 64,
        filing=filing(),
    )
    second = parser.parse(
        body=html,
        source_bucket="raw",
        source_key="filings/test.htm",
        source_sha256="c" * 64,
        filing=filing(),
    )

    assert [block.block_id for block in first.blocks] == [block.block_id for block in second.blocks]
    assert [section.section_id for section in first.sections] == [
        section.section_id for section in second.sections
    ]
