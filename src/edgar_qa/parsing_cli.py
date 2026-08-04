from __future__ import annotations

import os
from typing import Annotated

import boto3
import typer
from rich.console import Console

from edgar_qa.parsing.pipeline import S3CuratedDocumentPipeline

app = typer.Typer(no_args_is_help=True)
console = Console()


def _required_environment(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise typer.BadParameter(f"{name} is required. Run `source scripts/load_day05_outputs.sh`.")
    return value


def _pipeline() -> S3CuratedDocumentPipeline:
    raw_bucket = _required_environment("AWS_RAW_BUCKET")
    curated_bucket = _required_environment("AWS_CURATED_BUCKET")
    region = os.getenv("AWS_REGION", "us-east-1")
    s3_client = boto3.Session(region_name=region).client("s3")
    return S3CuratedDocumentPipeline(
        s3_client=s3_client,
        raw_bucket=raw_bucket,
        curated_bucket=curated_bucket,
    )


@app.command("parse-key")
def parse_key(
    raw_key: Annotated[str, typer.Option(help="Exact raw S3 filing object key.")],
) -> None:
    """Parse one raw filing into a curated JSON document."""
    result = _pipeline().parse_key(raw_key)
    console.print_json(result.model_dump_json(indent=2))


@app.command("parse-batch")
def parse_batch(
    maximum: Annotated[int, typer.Option(min=1, max=500)] = 5,
    prefix: Annotated[str, typer.Option()] = "filings/",
) -> None:
    """Parse raw filing objects sequentially until the requested limit is reached."""
    results = _pipeline().parse_batch(prefix=prefix, maximum=maximum)
    for index, result in enumerate(results, start=1):
        console.print(
            f"[{index}] {result.status}: s3://{result.curated_bucket}/{result.curated_key} "
            f"blocks={result.block_count} sections={result.section_count} "
            f"warnings={result.warning_count}"
        )
    console.print(f"Parsed {len(results)} raw filing object(s).")


if __name__ == "__main__":
    app()
