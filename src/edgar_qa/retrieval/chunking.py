from __future__ import annotations

from hashlib import sha256

from edgar_qa.parsing.models import CuratedFilingDocument, DocumentBlock, ParsedSection
from edgar_qa.retrieval.models import RetrievalChunk
from edgar_qa.retrieval.tokenization import tokenize


def _stable_id(*parts: str) -> str:
    return sha256(":".join(parts).encode("utf-8")).hexdigest()


class SectionAwareChunker:
    """Build retrieval chunks without crossing SEC section boundaries."""

    def __init__(self, maximum_terms: int = 350, overlap_terms: int = 50) -> None:
        if maximum_terms < 50:
            raise ValueError("maximum_terms must be at least 50.")
        if overlap_terms < 0 or overlap_terms >= maximum_terms:
            raise ValueError("overlap_terms must be non-negative and below maximum_terms.")
        self.maximum_terms = maximum_terms
        self.overlap_terms = overlap_terms

    def chunk_document(self, document: CuratedFilingDocument) -> list[RetrievalChunk]:
        blocks_by_order = {block.order: block for block in document.blocks}
        chunks: list[RetrievalChunk] = []

        for section in document.sections:
            section_blocks = [
                blocks_by_order[order]
                for order in range(section.start_block, section.end_block + 1)
                if order in blocks_by_order
            ]
            chunks.extend(self._chunk_section(document, section, section_blocks))

        return chunks

    def _chunk_section(
        self,
        document: CuratedFilingDocument,
        section: ParsedSection,
        blocks: list[DocumentBlock],
    ) -> list[RetrievalChunk]:
        if not blocks:
            return []

        windows: list[tuple[list[str], list[str]]] = []
        current_terms: list[str] = []
        current_block_ids: list[str] = []

        for block in blocks:
            block_terms = tokenize(block.text)
            if not block_terms:
                continue

            if len(block_terms) > self.maximum_terms:
                if current_terms:
                    windows.append((current_terms, current_block_ids))
                    current_terms = []
                    current_block_ids = []
                windows.extend(self._split_large_block(block))
                continue

            if current_terms and len(current_terms) + len(block_terms) > self.maximum_terms:
                windows.append((current_terms, current_block_ids))
                overlap = current_terms[-self.overlap_terms :] if self.overlap_terms else []
                current_terms = list(overlap)
                current_block_ids = []

            current_terms.extend(block_terms)
            current_block_ids.append(block.block_id)

        if current_terms:
            windows.append((current_terms, current_block_ids))

        return [
            self._make_chunk(document, section, index, terms, block_ids)
            for index, (terms, block_ids) in enumerate(windows)
            if terms
        ]

    def _split_large_block(self, block: DocumentBlock) -> list[tuple[list[str], list[str]]]:
        terms = tokenize(block.text)
        step = self.maximum_terms - self.overlap_terms
        result: list[tuple[list[str], list[str]]] = []
        for start in range(0, len(terms), step):
            window = terms[start : start + self.maximum_terms]
            if not window:
                break
            result.append((window, [block.block_id]))
            if start + self.maximum_terms >= len(terms):
                break
        return result

    @staticmethod
    def _make_chunk(
        document: CuratedFilingDocument,
        section: ParsedSection,
        chunk_index: int,
        terms: list[str],
        block_ids: list[str],
    ) -> RetrievalChunk:
        text = " ".join(terms)
        chunk_id = _stable_id(
            document.filing.document_id,
            section.section_id,
            str(chunk_index),
            sha256(text.encode("utf-8")).hexdigest(),
        )
        return RetrievalChunk(
            chunk_id=chunk_id,
            document_id=document.filing.document_id,
            cik=document.filing.cik,
            company_name=document.filing.company_name,
            form=document.filing.form,
            filing_date=document.filing.filing_date,
            accession_number=document.filing.accession_number,
            primary_document=document.filing.primary_document,
            section_id=section.section_id,
            section_label=section.label,
            section_title=section.title,
            section_occurrence=section.occurrence,
            chunk_index=chunk_index,
            block_ids=block_ids,
            text=text,
            term_count=len(terms),
        )
