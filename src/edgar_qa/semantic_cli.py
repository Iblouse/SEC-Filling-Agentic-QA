from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Annotated, Any

import boto3
import typer
from pydantic import BaseModel
from rich.console import Console
from rich.table import Table

from edgar_qa.retrieval.corpus import read_corpus_jsonl
from edgar_qa.retrieval.dense import DenseIndex
from edgar_qa.retrieval.dense_evaluation import evaluate_dense
from edgar_qa.retrieval.embeddings import DEFAULT_TITAN_EMBED_MODEL, TitanTextEmbedder
from edgar_qa.retrieval.evaluation import load_evaluation_questions, write_evaluation_report
from edgar_qa.retrieval.models import RetrievalEvaluationReport, SearchFilters
from edgar_qa.retrieval.vector_cache import build_embedding_cache, read_embedding_cache

app = typer.Typer(no_args_is_help=True)
console = Console()

DEFAULT_CORPUS = Path("data/retrieval/sec_chunks.jsonl")
DEFAULT_CACHE = Path("data/retrieval/titan_v2_512_embeddings.jsonl")
DEFAULT_MANIFEST = Path("data/retrieval/titan_v2_512_embeddings_manifest.json")
DEFAULT_DATASET = Path("evaluation/sec_questions.jsonl")
DEFAULT_REPORT = Path("data/retrieval/dense_evaluation.json")


def _bedrock_client() -> Any:
    region = os.getenv("AWS_REGION", "us-east-1")
    return boto3.Session(region_name=region).client("bedrock-runtime")


def _embedder(dimensions: int = 512) -> TitanTextEmbedder:
    return TitanTextEmbedder(
        _bedrock_client(),
        model_id=DEFAULT_TITAN_EMBED_MODEL,
        dimensions=dimensions,
        normalize=True,
    )


@app.command("verify-bedrock")
def verify_bedrock(
    dimensions: Annotated[int, typer.Option()] = 512,
) -> None:
    """Verify Bedrock embedding access with one small request."""
    embedder = _embedder(dimensions)
    result = embedder.embed("SEC filing semantic search verification request")
    console.print_json(
        json.dumps(
            {
                "model_id": embedder.model_id,
                "dimensions": len(result.vector),
                "normalized": embedder.normalize,
                "input_token_count": result.input_token_count,
            }
        )
    )


@app.command("build-embeddings")
def build_embeddings(
    corpus: Annotated[Path, typer.Option()] = DEFAULT_CORPUS,
    cache: Annotated[Path, typer.Option()] = DEFAULT_CACHE,
    manifest: Annotated[Path, typer.Option()] = DEFAULT_MANIFEST,
    dimensions: Annotated[int, typer.Option()] = 512,
    maximum_new: Annotated[int | None, typer.Option(min=1)] = None,
    rebuild: Annotated[bool, typer.Option()] = False,
) -> None:
    """Create or resume the local Titan embedding cache for SEC chunks."""
    chunks = read_corpus_jsonl(corpus)
    metadata = build_embedding_cache(
        chunks=chunks,
        embedder=_embedder(dimensions),
        corpus_path=corpus,
        cache_path=cache,
        manifest_path=manifest,
        maximum_new=maximum_new,
        rebuild=rebuild,
    )
    console.print_json(json.dumps(metadata))


@app.command("search")
def semantic_search(
    query: Annotated[str, typer.Option()],
    corpus: Annotated[Path, typer.Option()] = DEFAULT_CORPUS,
    cache: Annotated[Path, typer.Option()] = DEFAULT_CACHE,
    top_k: Annotated[int, typer.Option(min=1, max=50)] = 5,
    cik: Annotated[str | None, typer.Option()] = None,
    form: Annotated[str | None, typer.Option()] = None,
    accession_number: Annotated[str | None, typer.Option()] = None,
    section_label: Annotated[str | None, typer.Option()] = None,
    dimensions: Annotated[int, typer.Option()] = 512,
) -> None:
    """Run dense semantic retrieval with inspectable SEC metadata."""
    chunks = read_corpus_jsonl(corpus)
    embeddings = read_embedding_cache(cache)
    index = DenseIndex(chunks, embeddings, _embedder(dimensions))
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

    table = Table(title=f"Semantic results: {query}")
    table.add_column("Rank", justify="right")
    table.add_column("Cosine", justify="right")
    table.add_column("Form")
    table.add_column("Filed")
    table.add_column("Section")
    table.add_column("Chunk prefix")
    table.add_column("Text")
    for hit in hits:
        table.add_row(
            str(hit.rank),
            f"{hit.score:.4f}",
            hit.chunk.form,
            hit.chunk.filing_date or "",
            hit.chunk.section_label,
            hit.chunk.chunk_id[:16],
            hit.chunk.text[:260] + ("..." if len(hit.chunk.text) > 260 else ""),
        )
    console.print(table)


@app.command("evaluate")
def evaluate(
    corpus: Annotated[Path, typer.Option()] = DEFAULT_CORPUS,
    cache: Annotated[Path, typer.Option()] = DEFAULT_CACHE,
    dataset: Annotated[Path, typer.Option()] = DEFAULT_DATASET,
    output: Annotated[Path, typer.Option()] = DEFAULT_REPORT,
    top_k: Annotated[int, typer.Option(min=10, max=100)] = 10,
    dimensions: Annotated[int, typer.Option()] = 512,
) -> None:
    """Evaluate dense retrieval on the same labeled questions as BM25."""
    chunks = read_corpus_jsonl(corpus)
    embeddings = read_embedding_cache(cache)
    missing = [chunk.chunk_id for chunk in chunks if chunk.chunk_id not in embeddings]
    if missing:
        raise typer.BadParameter(
            f"Embedding cache is incomplete: {len(missing)} chunk(s) are missing. "
            "Run build-embeddings before evaluation."
        )
    questions = load_evaluation_questions(dataset)
    index = DenseIndex(chunks, embeddings, _embedder(dimensions))
    report = evaluate_dense(index, questions, corpus, dataset, top_k=top_k)
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


class Comparison(BaseModel):
    bm25: dict[str, float]
    dense: dict[str, float]
    delta_dense_minus_bm25: dict[str, float]


@app.command("compare")
def compare(
    bm25_report: Annotated[Path, typer.Option()] = Path("data/retrieval/bm25_evaluation.json"),
    dense_report: Annotated[Path, typer.Option()] = DEFAULT_REPORT,
    output: Annotated[Path, typer.Option()] = Path("data/retrieval/retrieval_comparison.json"),
) -> None:
    """Compare BM25 and dense retrieval aggregate metrics."""
    bm25 = RetrievalEvaluationReport.model_validate_json(bm25_report.read_text(encoding="utf-8"))
    dense = RetrievalEvaluationReport.model_validate_json(dense_report.read_text(encoding="utf-8"))
    if bm25.question_count != dense.question_count:
        raise typer.BadParameter("Reports were produced from different question counts.")

    metrics = {
        "recall_at_5": (bm25.recall_at_5, dense.recall_at_5),
        "recall_at_10": (bm25.recall_at_10, dense.recall_at_10),
        "mean_reciprocal_rank": (
            bm25.mean_reciprocal_rank,
            dense.mean_reciprocal_rank,
        ),
        "ndcg_at_10": (bm25.ndcg_at_10, dense.ndcg_at_10),
    }
    result = Comparison(
        bm25={name: values[0] for name, values in metrics.items()},
        dense={name: values[1] for name, values in metrics.items()},
        delta_dense_minus_bm25={name: values[1] - values[0] for name, values in metrics.items()},
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    console.print_json(result.model_dump_json(indent=2))


if __name__ == "__main__":
    app()
