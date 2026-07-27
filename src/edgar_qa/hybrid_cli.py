from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Annotated, Any

import boto3
import typer
from rich.console import Console
from rich.table import Table

from edgar_qa.retrieval.bm25 import BM25Index
from edgar_qa.retrieval.corpus import read_corpus_jsonl
from edgar_qa.retrieval.dense import DenseIndex
from edgar_qa.retrieval.embeddings import DEFAULT_TITAN_EMBED_MODEL, TitanTextEmbedder
from edgar_qa.retrieval.evaluation import load_evaluation_questions, write_evaluation_report
from edgar_qa.retrieval.hybrid import HybridIndex
from edgar_qa.retrieval.hybrid_evaluation import evaluate_hybrid, evaluate_reranked_hybrid
from edgar_qa.retrieval.models import RetrievalEvaluationReport, SearchFilters
from edgar_qa.retrieval.rerank import BedrockReranker
from edgar_qa.retrieval.vector_cache import read_embedding_cache

app = typer.Typer(no_args_is_help=True)
console = Console()

DEFAULT_CORPUS = Path("data/retrieval/sec_chunks.jsonl")
DEFAULT_CACHE = Path("data/retrieval/titan_v2_512_embeddings.jsonl")
DEFAULT_DATASET = Path("evaluation/sec_questions.jsonl")
DEFAULT_HYBRID_REPORT = Path("data/retrieval/hybrid_rrf_evaluation.json")
DEFAULT_RERANK_REPORT = Path("data/retrieval/hybrid_reranked_evaluation.json")


def _region() -> str:
    return os.getenv("AWS_REGION", "us-east-1")


def _bedrock_runtime_client() -> Any:
    return boto3.Session(region_name=_region()).client("bedrock-runtime")


def _bedrock_agent_runtime_client() -> Any:
    return boto3.Session(region_name=_region()).client("bedrock-agent-runtime")


def _embedder(dimensions: int = 512) -> TitanTextEmbedder:
    return TitanTextEmbedder(
        _bedrock_runtime_client(),
        model_id=DEFAULT_TITAN_EMBED_MODEL,
        dimensions=dimensions,
        normalize=True,
    )


def _hybrid_index(
    corpus: Path,
    cache: Path,
    dimensions: int,
    rrf_k: int,
    bm25_weight: float,
    dense_weight: float,
) -> HybridIndex:
    chunks = read_corpus_jsonl(corpus)
    embeddings = read_embedding_cache(cache)
    missing = [chunk.chunk_id for chunk in chunks if chunk.chunk_id not in embeddings]
    if missing:
        raise typer.BadParameter(
            f"Embedding cache is incomplete: {len(missing)} chunk(s) are missing. "
            "Run Day 7 build-embeddings first."
        )
    return HybridIndex(
        BM25Index(chunks),
        DenseIndex(chunks, embeddings, _embedder(dimensions)),
        rrf_k=rrf_k,
        bm25_weight=bm25_weight,
        dense_weight=dense_weight,
    )


def _filters(
    cik: str | None,
    form: str | None,
    accession_number: str | None,
    section_label: str | None,
) -> SearchFilters:
    return SearchFilters(
        cik=cik,
        form=form,
        accession_number=accession_number,
        section_label=section_label,
    )


@app.command("search")
def hybrid_search(
    query: Annotated[str, typer.Option()],
    corpus: Annotated[Path, typer.Option()] = DEFAULT_CORPUS,
    cache: Annotated[Path, typer.Option()] = DEFAULT_CACHE,
    top_k: Annotated[int, typer.Option(min=1, max=50)] = 10,
    candidate_k: Annotated[int, typer.Option(min=1, max=100)] = 20,
    rrf_k: Annotated[int, typer.Option(min=1)] = 60,
    bm25_weight: Annotated[float, typer.Option(min=0.01)] = 1.0,
    dense_weight: Annotated[float, typer.Option(min=0.01)] = 1.0,
    cik: Annotated[str | None, typer.Option()] = None,
    form: Annotated[str | None, typer.Option()] = None,
    accession_number: Annotated[str | None, typer.Option()] = None,
    section_label: Annotated[str | None, typer.Option()] = None,
    dimensions: Annotated[int, typer.Option()] = 512,
) -> None:
    """Fuse BM25 and dense candidates with Reciprocal Rank Fusion."""
    index = _hybrid_index(corpus, cache, dimensions, rrf_k, bm25_weight, dense_weight)
    hits = index.search(
        query,
        top_k=top_k,
        candidate_k=candidate_k,
        filters=_filters(cik, form, accession_number, section_label),
    )

    table = Table(title=f"Hybrid RRF results: {query}")
    table.add_column("Rank", justify="right")
    table.add_column("RRF", justify="right")
    table.add_column("BM25", justify="right")
    table.add_column("Dense", justify="right")
    table.add_column("Form")
    table.add_column("Section")
    table.add_column("Chunk prefix")
    table.add_column("Text")
    for hit in hits:
        table.add_row(
            str(hit.rank),
            f"{hit.rrf_score:.6f}",
            str(hit.bm25_rank or "-"),
            str(hit.dense_rank or "-"),
            hit.chunk.form,
            hit.chunk.section_label,
            hit.chunk.chunk_id[:16],
            hit.chunk.text[:220] + ("..." if len(hit.chunk.text) > 220 else ""),
        )
    console.print(table)


@app.command("evaluate")
def evaluate(
    corpus: Annotated[Path, typer.Option()] = DEFAULT_CORPUS,
    cache: Annotated[Path, typer.Option()] = DEFAULT_CACHE,
    dataset: Annotated[Path, typer.Option()] = DEFAULT_DATASET,
    output: Annotated[Path, typer.Option()] = DEFAULT_HYBRID_REPORT,
    top_k: Annotated[int, typer.Option(min=10, max=100)] = 10,
    candidate_k: Annotated[int, typer.Option(min=10, max=100)] = 20,
    rrf_k: Annotated[int, typer.Option(min=1)] = 60,
    bm25_weight: Annotated[float, typer.Option(min=0.01)] = 1.0,
    dense_weight: Annotated[float, typer.Option(min=0.01)] = 1.0,
    dimensions: Annotated[int, typer.Option()] = 512,
) -> None:
    """Evaluate RRF hybrid retrieval on the frozen relevance dataset."""
    questions = load_evaluation_questions(dataset)
    index = _hybrid_index(corpus, cache, dimensions, rrf_k, bm25_weight, dense_weight)
    report = evaluate_hybrid(
        index,
        questions,
        corpus,
        dataset,
        top_k=top_k,
        candidate_k=candidate_k,
    )
    write_evaluation_report(report, output)
    _print_metrics(report, output)


@app.command("verify-rerank")
def verify_rerank() -> None:
    """Verify direct Bedrock reranking access with a tiny two-document request."""
    client = _bedrock_agent_runtime_client()
    region = _region()
    reranker = BedrockReranker(client, region)
    response = client.rerank(
        queries=[{"type": "TEXT", "textQuery": {"text": "SEC filing credit risk"}}],
        sources=[
            {
                "type": "INLINE",
                "inlineDocumentSource": {
                    "type": "TEXT",
                    "textDocument": {"text": "The bank discusses credit risk in its SEC filing."},
                },
            },
            {
                "type": "INLINE",
                "inlineDocumentSource": {
                    "type": "TEXT",
                    "textDocument": {"text": "The company opened a new office cafeteria."},
                },
            },
        ],
        rerankingConfiguration={
            "type": "BEDROCK_RERANKING_MODEL",
            "bedrockRerankingConfiguration": {
                "modelConfiguration": {"modelArn": reranker.model_arn},
                "numberOfResults": 2,
            },
        },
    )
    console.print_json(
        json.dumps(
            {
                "region": region,
                "model_id": reranker.model_id,
                "model_arn": reranker.model_arn,
                "results": response.get("results", []),
            }
        )
    )


@app.command("rerank-search")
def rerank_search(
    query: Annotated[str, typer.Option()],
    corpus: Annotated[Path, typer.Option()] = DEFAULT_CORPUS,
    cache: Annotated[Path, typer.Option()] = DEFAULT_CACHE,
    top_k: Annotated[int, typer.Option(min=1, max=50)] = 10,
    candidate_k: Annotated[int, typer.Option(min=1, max=100)] = 20,
    rerank_candidates: Annotated[int, typer.Option(min=1, max=100)] = 20,
    rrf_k: Annotated[int, typer.Option(min=1)] = 60,
    bm25_weight: Annotated[float, typer.Option(min=0.01)] = 1.0,
    dense_weight: Annotated[float, typer.Option(min=0.01)] = 1.0,
    cik: Annotated[str | None, typer.Option()] = None,
    form: Annotated[str | None, typer.Option()] = None,
    accession_number: Annotated[str | None, typer.Option()] = None,
    section_label: Annotated[str | None, typer.Option()] = None,
    dimensions: Annotated[int, typer.Option()] = 512,
) -> None:
    """Rerank the hybrid candidate pool with Cohere Rerank 3.5 on Bedrock."""
    if rerank_candidates < top_k:
        raise typer.BadParameter("rerank-candidates must be greater than or equal to top-k.")
    if candidate_k < rerank_candidates:
        raise typer.BadParameter("candidate-k must be greater than or equal to rerank-candidates.")

    index = _hybrid_index(corpus, cache, dimensions, rrf_k, bm25_weight, dense_weight)
    candidates = index.search(
        query,
        top_k=rerank_candidates,
        candidate_k=candidate_k,
        filters=_filters(cik, form, accession_number, section_label),
    )
    reranker = BedrockReranker(_bedrock_agent_runtime_client(), _region())
    hits = reranker.rerank(query, candidates, top_k=top_k)

    table = Table(title=f"Hybrid + Bedrock rerank results: {query}")
    table.add_column("Rank", justify="right")
    table.add_column("Rerank", justify="right")
    table.add_column("Hybrid", justify="right")
    table.add_column("BM25", justify="right")
    table.add_column("Dense", justify="right")
    table.add_column("Form")
    table.add_column("Section")
    table.add_column("Chunk prefix")
    table.add_column("Text")
    for hit in hits:
        table.add_row(
            str(hit.rank),
            f"{hit.relevance_score:.6f}",
            str(hit.hybrid_rank),
            str(hit.bm25_rank or "-"),
            str(hit.dense_rank or "-"),
            hit.chunk.form,
            hit.chunk.section_label,
            hit.chunk.chunk_id[:16],
            hit.chunk.text[:220] + ("..." if len(hit.chunk.text) > 220 else ""),
        )
    console.print(table)


@app.command("evaluate-reranked")
def evaluate_reranked(
    corpus: Annotated[Path, typer.Option()] = DEFAULT_CORPUS,
    cache: Annotated[Path, typer.Option()] = DEFAULT_CACHE,
    dataset: Annotated[Path, typer.Option()] = DEFAULT_DATASET,
    output: Annotated[Path, typer.Option()] = DEFAULT_RERANK_REPORT,
    top_k: Annotated[int, typer.Option(min=10, max=100)] = 10,
    candidate_k: Annotated[int, typer.Option(min=10, max=100)] = 20,
    rerank_candidates: Annotated[int, typer.Option(min=10, max=100)] = 20,
    rrf_k: Annotated[int, typer.Option(min=1)] = 60,
    bm25_weight: Annotated[float, typer.Option(min=0.01)] = 1.0,
    dense_weight: Annotated[float, typer.Option(min=0.01)] = 1.0,
    dimensions: Annotated[int, typer.Option()] = 512,
) -> None:
    """Evaluate hybrid retrieval after Bedrock reranking."""
    questions = load_evaluation_questions(dataset)
    index = _hybrid_index(corpus, cache, dimensions, rrf_k, bm25_weight, dense_weight)
    reranker = BedrockReranker(_bedrock_agent_runtime_client(), _region())
    report = evaluate_reranked_hybrid(
        index,
        reranker,
        questions,
        corpus,
        dataset,
        top_k=top_k,
        candidate_k=candidate_k,
        rerank_candidates=rerank_candidates,
    )
    write_evaluation_report(report, output)
    _print_metrics(report, output)


@app.command("compare")
def compare(
    bm25_report: Annotated[Path, typer.Option()] = Path("data/retrieval/bm25_evaluation.json"),
    dense_report: Annotated[Path, typer.Option()] = Path("data/retrieval/dense_evaluation.json"),
    hybrid_report: Annotated[Path, typer.Option()] = DEFAULT_HYBRID_REPORT,
    reranked_report: Annotated[Path | None, typer.Option()] = DEFAULT_RERANK_REPORT,
    output: Annotated[Path, typer.Option()] = Path(
        "data/retrieval/day08_retrieval_comparison.json"
    ),
) -> None:
    """Compare baseline, fused, and optionally reranked retrieval metrics."""
    report_paths: dict[str, Path] = {
        "bm25": bm25_report,
        "dense": dense_report,
        "hybrid_rrf": hybrid_report,
    }
    if reranked_report is not None and reranked_report.exists():
        report_paths["hybrid_reranked"] = reranked_report

    reports = {
        name: RetrievalEvaluationReport.model_validate_json(path.read_text(encoding="utf-8"))
        for name, path in report_paths.items()
    }
    question_counts = {report.question_count for report in reports.values()}
    question_paths = {report.question_path for report in reports.values()}
    if len(question_counts) != 1 or len(question_paths) != 1:
        raise typer.BadParameter("All reports must use the same frozen evaluation dataset.")

    metrics = {
        name: {
            "recall_at_5": report.recall_at_5,
            "recall_at_10": report.recall_at_10,
            "mean_reciprocal_rank": report.mean_reciprocal_rank,
            "ndcg_at_10": report.ndcg_at_10,
        }
        for name, report in reports.items()
    }
    payload = {
        "question_count": next(iter(question_counts)),
        "question_path": next(iter(question_paths)),
        "systems": metrics,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    console.print_json(json.dumps(payload))


def _print_metrics(report: RetrievalEvaluationReport, output: Path) -> None:
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
