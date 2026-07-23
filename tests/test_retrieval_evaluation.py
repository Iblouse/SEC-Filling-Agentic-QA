from pathlib import Path

from edgar_qa.retrieval.bm25 import BM25Index
from edgar_qa.retrieval.evaluation import evaluate_bm25
from edgar_qa.retrieval.models import EvaluationQuestion, RetrievalChunk


def chunk(chunk_id: str, text: str) -> RetrievalChunk:
    return RetrievalChunk(
        chunk_id=chunk_id,
        document_id=f"doc-{chunk_id}",
        cik="0000019617",
        form="8-K",
        accession_number=f"accession-{chunk_id}",
        primary_document="filing.htm",
        section_id=f"section-{chunk_id}",
        section_label="item-8.01",
        section_title="Other Events",
        section_occurrence=1,
        chunk_index=0,
        text=text,
        term_count=len(text.split()),
    )


def test_evaluation_calculates_perfect_metrics_for_first_rank() -> None:
    index = BM25Index(
        [
            chunk("relevant", "dividend increase announced by the board"),
            chunk("other", "credit risk and liquidity discussion"),
        ]
    )
    questions = [
        EvaluationQuestion(
            question_id="q001",
            question="What dividend increase was announced?",
            relevant_chunk_ids=["relevant"],
        )
    ]

    report = evaluate_bm25(
        index,
        questions,
        Path("corpus.jsonl"),
        Path("questions.jsonl"),
    )

    assert report.recall_at_5 == 1.0
    assert report.recall_at_10 == 1.0
    assert report.mean_reciprocal_rank == 1.0
    assert report.ndcg_at_10 == 1.0
