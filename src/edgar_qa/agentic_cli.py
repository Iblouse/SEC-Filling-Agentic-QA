from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Annotated, Any

import boto3
import typer
from rich.console import Console
from rich.table import Table

from edgar_qa.qa.agent import BoundedCritiqueAgent
from edgar_qa.qa.agentic_evaluation import (
    build_agentic_report,
    evaluate_agentic_answer,
)
from edgar_qa.qa.critic import DEFAULT_CRITIC_MODEL, BedrockAnswerCritic
from edgar_qa.qa.generator import DEFAULT_ANSWER_MODEL, BedrockAnswerGenerator
from edgar_qa.qa.models import EvidenceSource, GroundedAnswer
from edgar_qa.qa.pipeline import build_hybrid_index, retrieve_evidence
from edgar_qa.qa.reviser import DEFAULT_REVISION_MODEL, BedrockAnswerReviser
from edgar_qa.retrieval.evaluation import load_evaluation_questions
from edgar_qa.retrieval.models import SearchFilters
from edgar_qa.retrieval.rerank import BedrockReranker

app = typer.Typer(no_args_is_help=True)
console = Console()

DEFAULT_CORPUS = Path("data/retrieval/sec_chunks.jsonl")
DEFAULT_CACHE = Path("data/retrieval/titan_v2_512_embeddings.jsonl")
DEFAULT_DATASET = Path("evaluation/sec_questions.jsonl")
DEFAULT_DAY9_REPORT = Path("data/qa/day09_qa_evaluation.json")
DEFAULT_DAY10_REPORT = Path("data/qa/day10_agentic_qa_evaluation.json")
DEFAULT_COMPARISON = Path("data/qa/day10_vs_day09_comparison.json")


def _region() -> str:
    return os.getenv("AWS_REGION", "us-east-1")


def _bedrock_runtime_client() -> Any:
    return boto3.Session(region_name=_region()).client("bedrock-runtime")


def _bedrock_agent_runtime_client() -> Any:
    return boto3.Session(region_name=_region()).client("bedrock-agent-runtime")


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


def _agent(
    runtime_client: Any,
    generator_model_id: str,
    critic_model_id: str,
    revision_model_id: str,
) -> BoundedCritiqueAgent:
    return BoundedCritiqueAgent(
        BedrockAnswerGenerator(runtime_client, model_id=generator_model_id),
        BedrockAnswerCritic(runtime_client, model_id=critic_model_id),
        BedrockAnswerReviser(runtime_client, model_id=revision_model_id),
    )


@app.command("verify-critic")
def verify_critic(
    critic_model_id: Annotated[str, typer.Option()] = DEFAULT_CRITIC_MODEL,
) -> None:
    """Verify the Day 10 critic can return a structured decision."""
    source = EvidenceSource(
        source_id="S1",
        chunk_id="verification-chunk",
        document_id="verification-document",
        cik="0000000000",
        form="10-K",
        accession_number="verification-accession",
        section_label="Item 1A",
        section_title="Risk Factors",
        rank=1,
        text="The filing states that market conditions may adversely affect results.",
    )
    answer = GroundedAnswer(
        question="What risk is described?",
        answer="Market conditions may adversely affect results. [S1]",
        citations=["S1"],
        cited_chunk_ids=["verification-chunk"],
        citation_valid=True,
        model_id="verification",
    )
    critic = BedrockAnswerCritic(
        _bedrock_runtime_client(),
        model_id=critic_model_id,
    )
    result = critic.review(answer.question, [source], answer)
    console.print_json(result.model_dump_json(indent=2))


@app.command("ask")
def ask(
    question: Annotated[str, typer.Option()],
    corpus: Annotated[Path, typer.Option()] = DEFAULT_CORPUS,
    cache: Annotated[Path, typer.Option()] = DEFAULT_CACHE,
    generator_model_id: Annotated[str, typer.Option()] = DEFAULT_ANSWER_MODEL,
    critic_model_id: Annotated[str, typer.Option()] = DEFAULT_CRITIC_MODEL,
    revision_model_id: Annotated[str, typer.Option()] = DEFAULT_REVISION_MODEL,
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
    """Answer one question with a bounded critic and at most one revision."""
    runtime_client = _bedrock_runtime_client()
    index = build_hybrid_index(
        corpus,
        cache,
        runtime_client,
        dimensions=dimensions,
        rrf_k=rrf_k,
        bm25_weight=bm25_weight,
        dense_weight=dense_weight,
    )
    reranker = BedrockReranker(_bedrock_agent_runtime_client(), _region())
    sources = retrieve_evidence(
        question,
        _filters(cik, form, accession_number, section_label),
        index,
        reranker,
        candidate_k=candidate_k,
        rerank_candidates=rerank_candidates,
        evidence_k=evidence_k,
    )
    result = _agent(
        runtime_client,
        generator_model_id,
        critic_model_id,
        revision_model_id,
    ).answer(question, sources)
    console.print(f"\n[bold]Initial answer[/bold]\n{result.initial_answer.answer}\n")
    console.print(
        f"[bold]Initial critic[/bold]: {result.initial_critique.verdict} - "
        f"{result.initial_critique.summary}\n"
    )
    if result.revised:
        console.print(f"[bold]Revised answer[/bold]\n{result.final_answer.answer}\n")
        console.print(
            f"[bold]Final critic[/bold]: {result.final_critique.verdict} - "
            f"{result.final_critique.summary}\n"
        )
    else:
        console.print("[bold]Revision[/bold]: not required\n")
    console.print_json(result.model_dump_json(indent=2))


@app.command("evaluate")
def evaluate(
    corpus: Annotated[Path, typer.Option()] = DEFAULT_CORPUS,
    cache: Annotated[Path, typer.Option()] = DEFAULT_CACHE,
    dataset: Annotated[Path, typer.Option()] = DEFAULT_DATASET,
    output: Annotated[Path, typer.Option()] = DEFAULT_DAY10_REPORT,
    generator_model_id: Annotated[str, typer.Option()] = DEFAULT_ANSWER_MODEL,
    critic_model_id: Annotated[str, typer.Option()] = DEFAULT_CRITIC_MODEL,
    revision_model_id: Annotated[str, typer.Option()] = DEFAULT_REVISION_MODEL,
    candidate_k: Annotated[int, typer.Option(min=5, max=100)] = 20,
    rerank_candidates: Annotated[int, typer.Option(min=5, max=50)] = 10,
    evidence_k: Annotated[int, typer.Option(min=1, max=10)] = 5,
    maximum_questions: Annotated[int | None, typer.Option(min=1)] = None,
    rrf_k: Annotated[int, typer.Option(min=1)] = 60,
    bm25_weight: Annotated[float, typer.Option(min=0.01)] = 1.0,
    dense_weight: Annotated[float, typer.Option(min=0.01)] = 1.0,
    dimensions: Annotated[int, typer.Option()] = 512,
) -> None:
    """Evaluate the bounded critique workflow on the frozen benchmark."""
    questions = load_evaluation_questions(dataset)
    if maximum_questions is not None:
        questions = questions[:maximum_questions]

    runtime_client = _bedrock_runtime_client()
    index = build_hybrid_index(
        corpus,
        cache,
        runtime_client,
        dimensions=dimensions,
        rrf_k=rrf_k,
        bm25_weight=bm25_weight,
        dense_weight=dense_weight,
    )
    reranker = BedrockReranker(_bedrock_agent_runtime_client(), _region())
    agent = _agent(
        runtime_client,
        generator_model_id,
        critic_model_id,
        revision_model_id,
    )

    results = []
    for question in questions:
        sources = retrieve_evidence(
            question.question,
            question.filters,
            index,
            reranker,
            candidate_k=candidate_k,
            rerank_candidates=rerank_candidates,
            evidence_k=evidence_k,
        )
        result = agent.answer(question.question, sources)
        results.append(evaluate_agentic_answer(question, result))

    report = build_agentic_report(
        results,
        generator_model_id=generator_model_id,
        critic_model_id=critic_model_id,
        revision_model_id=revision_model_id,
        configuration={
            "workflow": "generate_critique_optional_single_revision_final_critique",
            "max_revisions": 1,
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
                "revised_count": report.revised_count,
                "revision_rate": report.revision_rate,
                "final_critic_accept_rate": report.final_critic_accept_rate,
                "final_citation_validity_rate": report.final_citation_validity_rate,
                "final_gold_evidence_hit_rate": report.final_gold_evidence_hit_rate,
                "final_mean_cited_gold_precision": (report.final_mean_cited_gold_precision),
                "final_mean_cited_gold_recall": report.final_mean_cited_gold_recall,
                "mean_model_calls": report.mean_model_calls,
                "mean_model_tokens": report.mean_model_tokens,
                "report": str(output),
            }
        )
    )


@app.command("compare-day09")
def compare_day09(
    day09_report: Annotated[Path, typer.Option()] = DEFAULT_DAY9_REPORT,
    day10_report: Annotated[Path, typer.Option()] = DEFAULT_DAY10_REPORT,
    output: Annotated[Path, typer.Option()] = DEFAULT_COMPARISON,
) -> None:
    """Compare the Day 9 single-pass report with the Day 10 final answers."""
    day09 = json.loads(day09_report.read_text(encoding="utf-8"))
    day10 = json.loads(day10_report.read_text(encoding="utf-8"))
    payload = {
        "question_count_day09": day09.get("question_count"),
        "question_count_day10": day10.get("question_count"),
        "day09": {
            "citation_validity_rate": day09.get("citation_validity_rate"),
            "gold_evidence_hit_rate": day09.get("gold_evidence_hit_rate"),
            "mean_cited_gold_precision": day09.get("mean_cited_gold_precision"),
            "mean_cited_gold_recall": day09.get("mean_cited_gold_recall"),
        },
        "day10_final": {
            "citation_validity_rate": day10.get("final_citation_validity_rate"),
            "gold_evidence_hit_rate": day10.get("final_gold_evidence_hit_rate"),
            "mean_cited_gold_precision": day10.get("final_mean_cited_gold_precision"),
            "mean_cited_gold_recall": day10.get("final_mean_cited_gold_recall"),
            "revision_rate": day10.get("revision_rate"),
            "final_critic_accept_rate": day10.get("final_critic_accept_rate"),
            "mean_model_calls": day10.get("mean_model_calls"),
            "mean_model_tokens": day10.get("mean_model_tokens"),
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    console.print_json(json.dumps(payload))


@app.command("review")
def review(
    report_path: Annotated[Path, typer.Option()] = DEFAULT_DAY10_REPORT,
) -> None:
    """Display compact initial-versus-final review rows."""
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    table = Table(title="Day 10 bounded critique review")
    table.add_column("ID")
    table.add_column("Revised")
    table.add_column("Initial critic")
    table.add_column("Final critic")
    table.add_column("Final citation")
    table.add_column("Final gold")
    table.add_column("Final answer")
    for item in payload.get("queries", []):
        table.add_row(
            str(item.get("question_id", "")),
            "yes" if item.get("revised") else "no",
            str(item.get("initial_critic_verdict", "")),
            str(item.get("final_critic_verdict", "")),
            "yes" if item.get("final_citation_valid") else "no",
            "yes" if item.get("final_gold_hit") else "no",
            str(item.get("final_answer", ""))[:160],
        )
    console.print(table)


if __name__ == "__main__":
    app()
