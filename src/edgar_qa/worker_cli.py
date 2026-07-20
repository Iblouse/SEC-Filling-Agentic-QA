from __future__ import annotations

import os
from typing import Annotated

import boto3
import typer
from rich.console import Console

from edgar_qa.config import get_settings
from edgar_qa.ingestion.downloader import SecFilingDownloader
from edgar_qa.ingestion.storage import S3RawFilingStore
from edgar_qa.ingestion.worker import FilingIngestionWorker

app = typer.Typer(no_args_is_help=True)
console = Console()


def _required_environment(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise typer.BadParameter(
            f"{name} is required. Run `source scripts/load_terraform_outputs.sh`."
        )
    return value


def _build_worker(visibility_timeout: int) -> tuple[FilingIngestionWorker, SecFilingDownloader]:
    settings = get_settings()
    queue_url = _required_environment("AWS_INGESTION_QUEUE_URL")
    region = os.getenv("AWS_REGION", "us-east-1")
    session = boto3.Session(region_name=region)
    downloader = SecFilingDownloader(
        user_agent=settings.sec_user_agent,
        requests_per_second=settings.sec_requests_per_second,
        timeout_seconds=settings.sec_timeout_seconds,
    )
    worker = FilingIngestionWorker(
        sqs_client=session.client("sqs"),
        queue_url=queue_url,
        store=S3RawFilingStore(session.client("s3")),
        downloader=downloader,
        visibility_timeout_seconds=visibility_timeout,
    )
    return worker, downloader


@app.command("run-once")
def run_once(
    wait_seconds: Annotated[int, typer.Option(min=0, max=20)] = 5,
    visibility_timeout: Annotated[int, typer.Option(min=30, max=900)] = 120,
) -> None:
    """Receive and process at most one filing job."""
    worker, downloader = _build_worker(visibility_timeout)
    try:
        result = worker.run_once(wait_time_seconds=wait_seconds)
    finally:
        downloader.close()

    if result is None:
        console.print("No ingestion message was available.")
        return
    console.print_json(result.model_dump_json(indent=2))


@app.command()
def drain(
    maximum: Annotated[int, typer.Option(min=1, max=500)] = 10,
    wait_seconds: Annotated[int, typer.Option(min=0, max=20)] = 2,
    visibility_timeout: Annotated[int, typer.Option(min=30, max=900)] = 120,
) -> None:
    """Process messages until the queue is empty or the limit is reached."""
    worker, downloader = _build_worker(visibility_timeout)
    processed = 0
    try:
        while processed < maximum:
            result = worker.run_once(wait_time_seconds=wait_seconds)
            if result is None:
                break
            processed += 1
            console.print(f"[{processed}] {result.status}: s3://{result.bucket}/{result.key}")
    finally:
        downloader.close()
    console.print(f"Processed {processed} message(s).")


if __name__ == "__main__":
    app()
