from edgar_qa.retrieval.bm25 import BM25Index
from edgar_qa.retrieval.models import RetrievalChunk, SearchFilters


def chunk(chunk_id: str, text: str, form: str = "10-K") -> RetrievalChunk:
    return RetrievalChunk(
        chunk_id=chunk_id,
        document_id=f"doc-{chunk_id}",
        cik="0000019617",
        company_name="JPMorgan Chase & Co.",
        form=form,
        filing_date="2026-02-15",
        accession_number=f"accession-{chunk_id}",
        primary_document="filing.htm",
        section_id=f"section-{chunk_id}",
        section_label="item-1a",
        section_title="Risk Factors",
        section_occurrence=1,
        chunk_index=0,
        block_ids=[f"block-{chunk_id}"],
        text=text,
        term_count=len(text.split()),
    )


def test_bm25_ranks_lexically_relevant_chunk_first() -> None:
    index = BM25Index(
        [
            chunk("credit", "commercial real estate credit risk and loan losses"),
            chunk("legal", "pending litigation and legal proceedings"),
        ]
    )

    hits = index.search("commercial real estate credit risk", top_k=2)

    assert [hit.chunk.chunk_id for hit in hits] == ["credit"]
    assert hits[0].score > 0


def test_bm25_applies_metadata_filters() -> None:
    index = BM25Index(
        [
            chunk("annual", "liquidity risk", form="10-K"),
            chunk("quarterly", "liquidity risk", form="10-Q"),
        ]
    )

    hits = index.search(
        "liquidity risk",
        top_k=5,
        filters=SearchFilters(form="10-Q"),
    )

    assert [hit.chunk.chunk_id for hit in hits] == ["quarterly"]
