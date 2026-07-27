from __future__ import annotations

from collections.abc import Sequence

from edgar_qa.qa.models import EvidenceSource
from edgar_qa.retrieval.rerank import RerankedSearchHit


def build_evidence_sources(
    hits: Sequence[RerankedSearchHit],
    maximum_sources: int = 5,
    maximum_chars_per_source: int = 5000,
) -> list[EvidenceSource]:
    """Convert ranked retrieval hits into stable source labels S1, S2, ... ."""
    if maximum_sources < 1:
        raise ValueError("maximum_sources must be positive.")
    if maximum_chars_per_source < 200:
        raise ValueError("maximum_chars_per_source must be at least 200.")

    sources: list[EvidenceSource] = []
    for index, hit in enumerate(hits[:maximum_sources], start=1):
        chunk = hit.chunk
        sources.append(
            EvidenceSource(
                source_id=f"S{index}",
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                cik=chunk.cik,
                company_name=chunk.company_name,
                form=chunk.form,
                filing_date=chunk.filing_date,
                accession_number=chunk.accession_number,
                section_label=chunk.section_label,
                section_title=chunk.section_title,
                rank=hit.rank,
                retrieval_score=hit.relevance_score,
                text=chunk.text[:maximum_chars_per_source].strip(),
            )
        )
    return sources


def render_evidence_pack(sources: Sequence[EvidenceSource]) -> str:
    """Render evidence as an explicit source-labeled prompt block."""
    blocks: list[str] = []
    for source in sources:
        company = source.company_name or f"CIK {source.cik}"
        blocks.append(
            "\n".join(
                [
                    f"[{source.source_id}]",
                    f"Company: {company}",
                    f"CIK: {source.cik}",
                    f"Form: {source.form}",
                    f"Filed: {source.filing_date or 'unknown'}",
                    f"Accession: {source.accession_number}",
                    f"Section: {source.section_label} {source.section_title}".strip(),
                    "Text:",
                    source.text,
                ]
            )
        )
    return "\n\n".join(blocks)
