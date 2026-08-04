from __future__ import annotations

import re
from collections import Counter
from datetime import UTC, datetime
from hashlib import sha256
from html.parser import HTMLParser

from edgar_qa.parsing.models import (
    BlockKind,
    CuratedFilingDocument,
    DocumentBlock,
    FilingIdentity,
    ParsedSection,
    ParsingDiagnostics,
)

PARSER_VERSION = "sec-html-parser-0.1.0"

_BLOCK_TAGS = {"p", "div", "li", "section", "article", "blockquote", "pre"}
_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
_SKIP_TAGS = {"script", "style", "noscript", "svg", "ix:hidden"}

_SPACE_RE = re.compile(r"\s+")
_PART_RE = re.compile(r"^part\s+([ivx]+)\b", re.IGNORECASE)
_ITEM_GENERAL_RE = re.compile(
    r"^(?:part\s+[ivx]+\s*)?item\s+(\d{1,2}[a-z]?)\b[.\-:\s]*(.*)$",
    re.IGNORECASE,
)
_ITEM_8K_RE = re.compile(r"^item\s+(\d{1,2}\.\d{2})\b[.\-:\s]*(.*)$", re.IGNORECASE)


def _clean_text(value: str) -> str:
    return _SPACE_RE.sub(" ", value.replace("\xa0", " ")).strip()


def _stable_id(*parts: str) -> str:
    return sha256(":".join(parts).encode("utf-8")).hexdigest()


class _BlockCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.raw_blocks: list[tuple[BlockKind, str, list[list[str]] | None]] = []
        self.document_title: str | None = None
        self.skipped_element_count = 0

        self._skip_depth = 0
        self._text_parts: list[str] = []
        self._current_kind = BlockKind.PARAGRAPH
        self._in_title = False
        self._title_parts: list[str] = []

        self._in_table = False
        self._table_rows: list[list[str]] = []
        self._current_row: list[str] | None = None
        self._current_cell_parts: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized_tag = tag.lower()
        attrs_map = {name.lower(): (value or "") for name, value in attrs}

        if self._skip_depth > 0:
            self._skip_depth += 1
            return

        style = attrs_map.get("style", "").replace(" ", "").lower()
        hidden = "hidden" in attrs_map or "display:none" in style or "visibility:hidden" in style
        if normalized_tag in _SKIP_TAGS or hidden:
            self._skip_depth = 1
            self.skipped_element_count += 1
            return

        if normalized_tag == "title":
            self._in_title = True
            return

        if normalized_tag == "table":
            self._flush_text()
            self._in_table = True
            self._table_rows = []
            return

        if self._in_table:
            if normalized_tag == "tr":
                self._finish_cell()
                self._finish_row()
                self._current_row = []
            elif normalized_tag in {"td", "th"}:
                self._finish_cell()
                if self._current_row is None:
                    self._current_row = []
                self._current_cell_parts = []
            elif normalized_tag == "br" and self._current_cell_parts is not None:
                self._current_cell_parts.append(" ")
            return

        if normalized_tag in _HEADING_TAGS:
            self._flush_text()
            self._current_kind = BlockKind.HEADING
        elif normalized_tag in _BLOCK_TAGS:
            self._flush_text()
            self._current_kind = BlockKind.PARAGRAPH
        elif normalized_tag == "br":
            self._text_parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.lower()

        if self._skip_depth > 0:
            self._skip_depth -= 1
            return

        if normalized_tag == "title":
            self._in_title = False
            title = _clean_text(" ".join(self._title_parts))
            if title:
                self.document_title = title
            self._title_parts = []
            return

        if self._in_table:
            if normalized_tag in {"td", "th"}:
                self._finish_cell()
            elif normalized_tag == "tr":
                self._finish_cell()
                self._finish_row()
            elif normalized_tag == "table":
                self._finish_cell()
                self._finish_row()
                self._emit_table()
                self._in_table = False
            return

        if normalized_tag in _HEADING_TAGS or normalized_tag in _BLOCK_TAGS:
            self._flush_text()
            self._current_kind = BlockKind.PARAGRAPH

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        if self._in_title:
            self._title_parts.append(data)
            return
        if self._in_table:
            if self._current_cell_parts is not None:
                self._current_cell_parts.append(data)
            return
        self._text_parts.append(data)

    def close(self) -> None:
        super().close()
        self._finish_cell()
        self._finish_row()
        if self._in_table:
            self._emit_table()
            self._in_table = False
        self._flush_text()

    def _flush_text(self) -> None:
        text = _clean_text(" ".join(self._text_parts))
        self._text_parts = []
        if not text:
            return
        if (
            self.raw_blocks
            and self.raw_blocks[-1][0] == self._current_kind
            and self.raw_blocks[-1][1] == text
        ):
            return
        self.raw_blocks.append((self._current_kind, text, None))

    def _finish_cell(self) -> None:
        if self._current_cell_parts is None:
            return
        if self._current_row is None:
            self._current_row = []
        self._current_row.append(_clean_text(" ".join(self._current_cell_parts)))
        self._current_cell_parts = None

    def _finish_row(self) -> None:
        if self._current_row is None:
            return
        if any(cell for cell in self._current_row):
            self._table_rows.append(self._current_row)
        self._current_row = None

    def _emit_table(self) -> None:
        rows = [row for row in self._table_rows if any(cell for cell in row)]
        self._table_rows = []
        if not rows:
            return
        text = "\n".join(" | ".join(cell for cell in row) for row in rows)
        self.raw_blocks.append((BlockKind.TABLE, text, rows))


class SecHtmlDocumentParser:
    """Converts one immutable EDGAR HTML filing into a structured document."""

    def parse(
        self,
        body: bytes,
        source_bucket: str,
        source_key: str,
        source_sha256: str,
        filing: FilingIdentity,
        parsed_at: datetime | None = None,
    ) -> CuratedFilingDocument:
        text = body.decode("utf-8", errors="replace")
        collector = _BlockCollector()
        collector.feed(text)
        collector.close()

        blocks = self._build_blocks(collector.raw_blocks, filing)
        sections = self._detect_sections(blocks, filing)
        diagnostics = self._diagnostics(body, blocks, sections, collector)

        return CuratedFilingDocument(
            parser_version=PARSER_VERSION,
            parsed_at=parsed_at or datetime.now(UTC),
            source_bucket=source_bucket,
            source_key=source_key,
            source_sha256=source_sha256,
            filing=filing,
            document_title=collector.document_title,
            blocks=blocks,
            sections=sections,
            diagnostics=diagnostics,
        )

    @staticmethod
    def _build_blocks(
        raw_blocks: list[tuple[BlockKind, str, list[list[str]] | None]],
        filing: FilingIdentity,
    ) -> list[DocumentBlock]:
        result: list[DocumentBlock] = []
        for order, (kind, text, rows) in enumerate(raw_blocks):
            result.append(
                DocumentBlock(
                    block_id=_stable_id(filing.document_id, kind.value, str(order)),
                    order=order,
                    kind=kind,
                    text=text,
                    table_rows=rows,
                )
            )
        return result

    def _detect_sections(
        self,
        blocks: list[DocumentBlock],
        filing: FilingIdentity,
    ) -> list[ParsedSection]:
        starts: list[tuple[int, str, str]] = []
        current_part: str | None = None

        for block in blocks:
            if block.kind == BlockKind.TABLE or len(block.text) > 220:
                continue
            text = block.text.strip()
            part_match = _PART_RE.match(text)
            if part_match and len(text) <= 80:
                current_part = part_match.group(1).lower()
                continue

            candidate = self._section_candidate(text, filing.form, current_part)
            if candidate is not None:
                label, title = candidate
                starts.append((block.order, label, title))

        if not starts:
            if not blocks:
                return []
            return [
                ParsedSection(
                    section_id=_stable_id(filing.document_id, "document", "1"),
                    label="document",
                    title="Complete filing",
                    occurrence=1,
                    start_block=0,
                    end_block=len(blocks) - 1,
                    block_ids=[block.block_id for block in blocks],
                )
            ]

        sections: list[ParsedSection] = []
        occurrences: Counter[str] = Counter()

        if starts[0][0] > 0:
            sections.append(
                ParsedSection(
                    section_id=_stable_id(filing.document_id, "preamble", "1"),
                    label="preamble",
                    title="Preamble",
                    occurrence=1,
                    start_block=0,
                    end_block=starts[0][0] - 1,
                    block_ids=[block.block_id for block in blocks[: starts[0][0]]],
                )
            )

        for index, (start, label, title) in enumerate(starts):
            end = starts[index + 1][0] - 1 if index + 1 < len(starts) else len(blocks) - 1
            occurrences[label] += 1
            occurrence = occurrences[label]
            sections.append(
                ParsedSection(
                    section_id=_stable_id(filing.document_id, label, str(occurrence)),
                    label=label,
                    title=title,
                    occurrence=occurrence,
                    start_block=start,
                    end_block=end,
                    block_ids=[block.block_id for block in blocks[start : end + 1]],
                )
            )
        return sections

    @staticmethod
    def _section_candidate(
        text: str,
        form: str,
        current_part: str | None,
    ) -> tuple[str, str] | None:
        normalized_form = form.upper()
        match = _ITEM_8K_RE.match(text) if normalized_form.startswith("8-K") else None
        if match is not None:
            number = match.group(1).lower()
            return f"item-{number}", text

        match = _ITEM_GENERAL_RE.match(text)
        if match is None:
            return None
        number = match.group(1).lower()
        if normalized_form.startswith("10-Q") and current_part:
            return f"part-{current_part}-item-{number}", text
        return f"item-{number}", text

    @staticmethod
    def _diagnostics(
        body: bytes,
        blocks: list[DocumentBlock],
        sections: list[ParsedSection],
        collector: _BlockCollector,
    ) -> ParsingDiagnostics:
        label_counts = Counter(section.label for section in sections)
        duplicates = sorted(label for label, count in label_counts.items() if count > 1)
        warnings: list[str] = []
        if not blocks:
            warnings.append("no_text_blocks")
        if not sections:
            warnings.append("no_sections_detected")
        if duplicates:
            warnings.append("duplicate_section_labels_detected")
        if any("�" in block.text for block in blocks):
            warnings.append("replacement_characters_detected")

        return ParsingDiagnostics(
            input_bytes=len(body),
            total_characters=sum(len(block.text) for block in blocks),
            block_count=len(blocks),
            paragraph_count=sum(block.kind == BlockKind.PARAGRAPH for block in blocks),
            heading_count=sum(block.kind == BlockKind.HEADING for block in blocks),
            table_count=sum(block.kind == BlockKind.TABLE for block in blocks),
            section_count=len(sections),
            skipped_element_count=collector.skipped_element_count,
            duplicate_section_labels=duplicates,
            warnings=warnings,
        )
