# Day 5 Design: Curated Filing Documents

## Objective

Transform immutable raw EDGAR HTML into structured JSON suitable for retrieval evaluation and later chunking.

## Curated document contract

Each JSON document records:

- Source bucket, key, and SHA-256
- CIK, form, filing date, accession number, and primary document
- Stable document, block, and section identifiers
- Document title
- Ordered paragraph, heading, and table blocks
- Detected 10-K, 10-Q, or 8-K sections
- Parsing diagnostics and warnings

## Parsing choices

- Use Python's standard HTML parser to avoid introducing a new runtime dependency.
- Preserve visible Inline XBRL values while excluding hidden Inline XBRL blocks.
- Preserve tables as rows and a searchable text representation.
- Do not overwrite an existing curated document.
- Treat duplicate section labels as a diagnostic because filing tables of contents can repeat item names.

## Known limitations for the first parser

- Complex nested tables may lose colspan and rowspan semantics.
- Styling-based headings that do not contain an SEC item label remain paragraphs.
- Section detection may retain table-of-contents occurrences. Retrieval evaluation will determine whether a later deduplication step is necessary.
- Plain-text EDGAR submissions are not yet handled separately.
