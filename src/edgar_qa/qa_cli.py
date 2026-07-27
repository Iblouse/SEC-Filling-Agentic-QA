from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Annotated, Any

import boto3
import typer
from rich.console import Console
from rich.table import Table

from edgar_qa.qa.evaluation import build_qa_report, evaluate_answer
from edgar_qa.qa.evidence import build_evidence_sources
from edgar_qa.qa.generator import DEFAULT_ANSWER_MODEL, BedrockAnswerGenerator
from edgar_qa.qa.models import GroundedAnswer
from edgar_qa.retrieval.bm25 import BM25Index
from edgar_qa.retrieval.corpus import read_corpus_jsonl
from edgar_qa.retrieval.dense import DenseIndex
from edgar_qa.retrieval.embeddings import DEFAULT_TITAN_EMBED_MODEL, TitanTextEmbedder
from edgar_qa.retrieval.evaluation import load_evaluation_questions
from edgar_qa.retrieval.hybrid import HybridIndex
from edgar_qa.retrieval.models import SearchFilters
from edgar_qa.retrieval.rerank import BedrockReranker
from edgar_qa.retrieval.vector_cache import read_embedding_cache

app = typer.Typer(no_args_is_help=True)
console = Console()

DEFAULT_CORPUS = Path("data/retrieval/sec_chunks.jsonl")
DEFAULT_CACHE = Path("data/retrieval/titan_v2_512_embeddings.jsonl")
DEFAULT_DATASET = Path("evaluation/sec_questions.jsonl")
DEFAULT_QA_REPORT = Path("data/qa/day09_qa_evaluation.json")


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


def _answer_question(
    question: str,
    filters: SearchFilters,
    index: HybridIndex,
    reranker: BedrockReranker,
    generator: BedrockAnswerGenerator,
    candidate_k: int,
    rerank_candidates: int,
    evidence_k: int,
) -> GroundedAnswer:
    candidates = index.search(
        question,
        top_k=rerank_candidates,
        candidate_k=candidate_k,
        filters=filters,
    )
    reranked = reranker.rerank(question, candidates, top_k=rerank_candidates)
    sources = build_evidence_sources(reranked, maximum_sources=evidence_k)
    return generator.answer(question, sources)


@app.command("verify-model")
def verify_model(
    model_id: Annotated[str, typer.Option()] = DEFAULT_ANSWER_MODEL,
) -> None:
    """Verify that the configured Bedrock answer model can be invoked."""
    client = _bedrock_runtime_client()
    response = client.converse(
        modelId=model_id,
        messages=[
            {
                "role": "user",
                "content": [{"text": "Reply with exactly: BEDROCK_QA_OK"}],
            }
        ],
        inferenceConfig={"maxTokens": 32, "temperature": 0.0},
    )
    content = response.get("output", {}).get("message", {}).get("content", [])
    text = "\n".join(
        str(item.get("text", "")) for item in content if isinstance(item, dict)
    ).strip()
    console.print_json(
        json.dumps(
            {
                "region": _region(),
                "model_id": model_id,
                "response": text,
                "usage": response.get("usage", {}),
            }
        )
    )


@app.command("ask")
def ask(
    question: Annotated[str, typer.Option()],
    corpus: Annotated[Path, typer.Option()] = DEFAULT_CORPUS,
    cache: Annotated[Path, typer.Option()] = DEFAULT_CACHE,
    model_id: Annotated[str, typer.Option()] = DEFAULT_ANSWER_MODEL,
    candidate_k: Annotated[int, typer.Option(min=5, max=100)] = 20,
    rerank_candidates: Annotated[int, typer.Option(min=5, max=50)] = 10,
    evidence_k: Annotated[int, typer.Option(min=1, max=10)] = 5,
    rrf_k: Annotated[int, typer.Option(min=1)] = 60,
    bm25_weight: Annotated[float, typer.Option(min=0.01)] = 1.0,
    dense_weight: Annotated[float, typer.Option(min=0.01)] = 1.0,
    cik: Annotated[str | None, typer.Option()] = None,
    form: Annotated[str | None, typer.Option()] = None,
    accession_number: Annotated[str | None, typer.Option()] = None,
    section_label: Annotated[str | None, typer.Option()] = None,
    dimensions: Annotated[int, typer.Option()] = 512,
) -> None:
    """Answer one SEC question from hybrid + reranked filing evidence."""
    if candidate_k < rerank_candidates:
        raise typer.BadParameter("candidate-k must be >= rerank-candidates.")
    if rerank_candidates < evidence_k:
        raise typer.BadParameter("rerank-candidates must be >= evidence-k.")

    index = _hybrid_index(corpus, cache, dimensions, rrf_k, bm25_weight, dense_weight)
    reranker = BedrockReranker(_bedrock_agent_runtime_client(), _region())
    generator = BedrockAnswerGenerator(_bedrock_runtime_client(), model_id=model_id)
    answer = _answer_question(
        question,
        _filters(cik, form, accession_number, section_label),
        index,
        reranker,
        generator,
        candidate_k,
        rerank_candidates,
        evidence_k,
    )
    console.print(f"\n[bold]Answer[/bold]\n{answer.answer}\n")
    console.print_json(answer.model_dump_json(indent=2))


@app.command("evaluate")
def evaluate(
    corpus: Annotated[Path, typer.Option()] = DEFAULT_CORPUS,
    cache: Annotated[Path, typer.Option()] = DEFAULT_CACHE,
    dataset: Annotated[Path, typer.Option()] = DEFAULT_DATASET,
    output: Annotated[Path, typer.Option()] = DEFAULT_QA_REPORT,
    model_id: Annotated[str, typer.Option()] = DEFAULT_ANSWER_MODEL,
    candidate_k: Annotated[int, typer.Option(min=5, max=100)] = 20,
    rerank_candidates: Annotated[int, typer.Option(min=5, max=50)] = 10,
    evidence_k: Annotated[int, typer.Option(min=1, max=10)] = 5,
    maximum_questions: Annotated[int | None, typer.Option(min=1)] = None,
    rrf_k: Annotated[int, typer.Option(min=1)] = 60,
    bm25_weight: Annotated[float, typer.Option(min=0.01)] = 1.0,
    dense_weight: Annotated[float, typer.Option(min=0.01)] = 1.0,
    dimensions: Annotated[int, typer.Option()] = 512,
) -> None:
    """Generate and evaluate single-pass answers on the frozen relevance dataset."""
    if candidate_k < rerank_candidates:
        raise typer.BadParameter("candidate-k must be >= rerank-candidates.")
    if rerank_candidates < evidence_k:
        raise typer.BadParameter("rerank-candidates must be >= evidence-k.")

    questions = load_evaluation_questions(dataset)
    if maximum_questions is not None:
        questions = questions[:maximum_questions]
    index = _hybrid_index(corpus, cache, dimensions, rrf_k, bm25_weight, dense_weight)
    reranker = BedrockReranker(_bedrock_agent_runtime_client(), _region())
    generator = BedrockAnswerGenerator(_bedrock_runtime_client(), model_id=model_id)

    results = []
    for question in questions:
        answer = _answer_question(
            question.question,
            question.filters,
            index,
            reranker,
            generator,
            candidate_k,
            rerank_candidates,
            evidence_k,
        )
        results.append(evaluate_answer(question, answer))

    report = build_qa_report(
        results,
        model_id=model_id,
        configuration={
            "retrieval": "weighted_rrf_then_bedrock_rerank",
            "candidate_k": candidate_k,
            "rerank_candidates": rerank_candidates,
            "evidence_k": evidence_k,
            "rrf_k": rrf_k,
            "bm25_weight": bm25_weight,
            "dense_weight": dense_weight,
            "dimensions": dimensions,
        },
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    console.print_json(
        json.dumps(
            {
                "question_count": report.question_count,
                "answered_count": report.answered_count,
                "abstention_rate": report.abstention_rate,
                "citation_validity_rate": report.citation_validity_rate,
                "gold_evidence_hit_rate": report.gold_evidence_hit_rate,
                "mean_cited_gold_precision": report.mean_cited_gold_precision,
                "mean_cited_gold_recall": report.mean_cited_gold_recall,
                "report": str(output),
            }
        )
    )


@app.command("review")
def review(
    report_path: Annotated[Path, typer.Option()] = DEFAULT_QA_REPORT,
) -> None:
    """Display compact answer/citation review rows from a Day 9 report."""
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    table = Table(title="Day 9 grounded QA review")
    table.add_column("ID")
    table.add_column("Abstain")
    table.add_column("Citations valid")
    table.add_column("Gold cited")
    table.add_column("Answer")
    for item in payload.get("queries", []):
        table.add_row(
            str(item.get("question_id", "")),
            "yes" if item.get("abstained") else "no",
            "yes" if item.get("citation_valid") else "no",
            "yes" if item.get("cites_at_least_one_gold_chunk") else "no",
            str(item.get("answer", ""))[:180],
        )
    console.print(table)


if __name__ == "__main__":
    app()
