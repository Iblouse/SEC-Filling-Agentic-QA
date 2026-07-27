from edgar_qa.qa.evidence import build_evidence_sources, render_evidence_pack
from edgar_qa.retrieval.hybrid import HybridSearchHit
from edgar_qa.retrieval.models import RetrievalChunk
from edgar_qa.retrieval.rerank import RerankedSearchHit


def _chunk(chunk_id: str) -> RetrievalChunk:
    return RetrievalChunk(
        chunk_id=chunk_id,
        document_id="doc-1",
        cik="0000019617",
        company_name="JPMorgan Chase & Co.",
        form="10-K",
        filing_date="2026-02-20",
        accession_number="0000019617-26-000001",
        primary_document="sample.htm",
        section_id="section-1",
        section_label="Item 1A",
        section_title="Risk Factors",
        section_occurrence=1,
        chunk_index=0,
        text="Credit risk could increase during adverse economic conditions.",
        term_count=9,
    )


def test_build_evidence_sources_assigns_stable_labels() -> None:
    chunk = _chunk("chunk-a")
    hybrid = HybridSearchHit(
        rank=2,
        rrf_score=0.03,
        chunk=chunk,
        bm25_rank=4,
        dense_rank=2,
    )
    hit = RerankedSearchHit(
        rank=1,
        relevance_score=0.98,
        chunk=chunk,
        hybrid_rank=hybrid.rank,
        bm25_rank=hybrid.bm25_rank,
        dense_rank=hybrid.dense_rank,
    )

    sources = build_evidence_sources([hit], maximum_sources=1)

    assert sources[0].source_id == "S1"
    assert sources[0].chunk_id == "chunk-a"
    assert "[S1]" in render_evidence_pack(sources)
    assert "Risk Factors" in render_evidence_pack(sources)
