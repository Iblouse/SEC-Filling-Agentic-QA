from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Annotated

import boto3
import typer
from rich.console import Console
from rich.table import Table

from edgar_qa.retrieval.bm25 import BM25Index
from edgar_qa.retrieval.corpus import (
    S3CuratedCorpusReader,
    build_corpus,
    create_question_template,
    read_corpus_jsonl,
    update_question_labels,
    write_corpus_jsonl,
)
from edgar_qa.retrieval.evaluation import (
    evaluate_bm25,
    load_evaluation_questions,
    write_evaluation_report,
)
from edgar_qa.retrieval.models import SearchFilters

app = typer.Typer(no_args_is_help=True)
console = Console()


def _required_environment(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise typer.BadParameter(f"{name} is required. Run `source scripts/load_day05_outputs.sh`.")
    return value


@app.command("export-corpus")
def export_corpus(
    output: Annotated[Path, typer.Option()] = Path("data/retrieval/sec_chunks.jsonl"),
    manifest: Annotated[Path, typer.Option()] = Path("data/retrieval/corpus_manifest.json"),
    maximum_documents: Annotated[int, typer.Option(min=1, max=10000)] = 100,
    maximum_terms: Annotated[int, typer.Option(min=50, max=2000)] = 350,
    overlap_terms: Annotated[int, typer.Option(min=0, max=500)] = 50,
) -> None:
    """Create a local, section-aware retrieval corpus from curated S3 documents."""
    curated_bucket = _required_environment("AWS_CURATED_BUCKET")
    region = os.getenv("AWS_REGION", "us-east-1")
    s3_client = boto3.Session(region_name=region).client("s3")
    reader = S3CuratedCorpusReader(s3_client, curated_bucket)
    documents = list(reader.iter_documents(maximum=maximum_documents))
    chunks = build_corpus(documents, maximum_terms, overlap_terms)
    metadata = write_corpus_jsonl(chunks, output)
    metadata.update(
        {
            "curated_bucket": curated_bucket,
            "maximum_terms": maximum_terms,
            "overlap_terms": overlap_terms,
        }
    )
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    console.print_json(json.dumps(metadata))


@app.command()
def search(
    query: Annotated[str, typer.Option()],
    corpus: Annotated[Path, typer.Option()] = Path("data/retrieval/sec_chunks.jsonl"),
    top_k: Annotated[int, typer.Option(min=1, max=50)] = 5,
    cik: Annotated[str | None, typer.Option()] = None,
    form: Annotated[str | None, typer.Option()] = None,
    accession_number: Annotated[str | None, typer.Option()] = None,
    section_label: Annotated[str | None, typer.Option()] = None,
) -> None:
    """Search the BM25 baseline and display inspectable evidence."""
    chunks = read_corpus_jsonl(corpus)
    index = BM25Index(chunks)
    hits = index.search(
        query,
        top_k=top_k,
        filters=SearchFilters(
            cik=cik,
            form=form,
            accession_number=accession_number,
            section_label=section_label,
        ),
    )

    table = Table(title=f"BM25 results: {query}")
    table.add_column("Rank", justify="right")
    table.add_column("Score", justify="right")
    table.add_column("Form")
    table.add_column("Filed")
    table.add_column("Section")
    table.add_column("Chunk ID")
    table.add_column("Text")
    for hit in hits:
        table.add_row(
            str(hit.rank),
            f"{hit.score:.4f}",
            hit.chunk.form,
            hit.chunk.filing_date or "",
            hit.chunk.section_label,
            hit.chunk.chunk_id,
            hit.chunk.text[:240] + ("..." if len(hit.chunk.text) > 240 else ""),
        )
    console.print(table)


@app.command("create-evaluation-template")
def create_evaluation_template(
    corpus: Annotated[Path, typer.Option()] = Path("data/retrieval/sec_chunks.jsonl"),
    output: Annotated[Path, typer.Option()] = Path("evaluation/sec_questions.jsonl"),
    maximum_questions: Annotated[int, typer.Option(min=1, max=100)] = 10,
) -> None:
    """Create unlabeled questions based on the filings available in the corpus."""
    chunks = read_corpus_jsonl(corpus)
    count = create_question_template(chunks, output, maximum_questions)
    console.print(f"Created {count} question(s) in [bold]{output}[/bold].")


@app.command("label-question")
def label_question(
    question_id: Annotated[str, typer.Option()],
    chunk_id: Annotated[list[str], typer.Option(help="Repeat for multiple relevant chunks.")],
    dataset: Annotated[Path, typer.Option()] = Path("evaluation/sec_questions.jsonl"),
) -> None:
    """Save manually reviewed relevant chunk IDs for one question."""
    updated = update_question_labels(dataset, question_id, chunk_id)
    console.print_json(updated.model_dump_json(indent=2))


@app.command()
def evaluate(
    corpus: Annotated[Path, typer.Option()] = Path("data/retrieval/sec_chunks.jsonl"),
    dataset: Annotated[Path, typer.Option()] = Path("evaluation/sec_questions.jsonl"),
    output: Annotated[Path, typer.Option()] = Path("data/retrieval/bm25_evaluation.json"),
    top_k: Annotated[int, typer.Option(min=10, max=100)] = 10,
) -> None:
    """Calculate Recall@k, MRR, and nDCG for the labeled BM25 baseline."""
    chunks = read_corpus_jsonl(corpus)
    questions = load_evaluation_questions(dataset)
    index = BM25Index(chunks)
    report = evaluate_bm25(index, questions, corpus, dataset, top_k=top_k)
    write_evaluation_report(report, output)
    console.print_json(
        json.dumps(
            {
                "question_count": report.question_count,
                "recall_at_5": report.recall_at_5,
                "recall_at_10": report.recall_at_10,
                "mean_reciprocal_rank": report.mean_reciprocal_rank,
                "ndcg_at_10": report.ndcg_at_10,
                "report": str(output),
            }
        )
    )


if __name__ == "__main__":
    app()
