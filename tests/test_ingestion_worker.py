import json
from datetime import UTC, datetime
from typing import Any

from edgar_qa.ingestion.downloader import DownloadedFiling
from edgar_qa.ingestion.models import IngestionStatus
from edgar_qa.ingestion.worker import FilingIngestionWorker


class FakeStore:
    def __init__(self, exists: bool = False) -> None:
        self.object_exists = exists
        self.put_calls = 0

    def exists(self, bucket: str, key: str) -> bool:
        return self.object_exists

    def put_filing_if_absent(self, job: Any, downloaded: Any) -> Any:
        self.put_calls += 1
        return type("Stored", (), {
            "created": True,
            "receipt_key": f"{job.destination_key}.receipt.json",
        })()


class FakeDownloader:
    def __init__(self) -> None:
        self.calls = 0

    def download(self, source_url: str) -> DownloadedFiling:
        self.calls += 1
        body = b"<html>" + b"x" * 300 + b"</html>"
        return DownloadedFiling(
            body=body,
            content_sha256="a" * 64,
            fetched_at=datetime(2026, 7, 18, tzinfo=UTC),
            content_type="text/html",
            final_url=source_url,
            etag=None,
            last_modified=None,
        )


class FakeSqs:
    def __init__(self, body: str | None) -> None:
        self.body = body
        self.deleted = False

    def receive_message(self, **_: Any) -> dict[str, Any]:
        if self.body is None:
            return {}
        return {"Messages": [{
            "Body": self.body,
            "ReceiptHandle": "receipt-1",
            "Attributes": {"ApproximateReceiveCount": "1"},
        }]}

    def delete_message(self, **kwargs: Any) -> None:
        assert kwargs["ReceiptHandle"] == "receipt-1"
        self.deleted = True


def job_body() -> str:
    return json.dumps({
        "schema_version": "1.0",
        "job_id": "job-123",
        "discovered_at": "2026-07-18T12:00:00Z",
        "filing": {
            "cik": "0000019617",
            "company_name": "JPMORGAN CHASE & CO",
            "accession_number": "0000019617-26-000001",
            "form": "10-K",
            "source_url": (
                "https://www.sec.gov/Archives/edgar/data/19617/"
                "000001961726000001/jpm-20251231.htm"
            ),
        },
        "destination_bucket": "raw-bucket",
        "destination_key": (
            "filings/cik=0000019617/form=10-K/"
            "accession=0000019617-26-000001/jpm-20251231.html"
        ),
    })


def test_worker_stores_then_deletes_message() -> None:
    sqs = FakeSqs(job_body())
    store = FakeStore()
    downloader = FakeDownloader()
    worker = FilingIngestionWorker(
        sqs, "queue-url", store, downloader  # type: ignore[arg-type]
    )
    result = worker.run_once(wait_time_seconds=0)
    assert result is not None and result.status == IngestionStatus.STORED
    assert downloader.calls == 1 and store.put_calls == 1 and sqs.deleted


def test_worker_skips_existing_object() -> None:
    sqs = FakeSqs(job_body())
    store = FakeStore(exists=True)
    downloader = FakeDownloader()
    worker = FilingIngestionWorker(
        sqs, "queue-url", store, downloader  # type: ignore[arg-type]
    )
    result = worker.run_once(wait_time_seconds=0)
    assert result is not None and result.status == IngestionStatus.ALREADY_EXISTS
    assert downloader.calls == 0 and store.put_calls == 0 and sqs.deleted


def test_failure_does_not_delete_message() -> None:
    class FailingDownloader:
        def download(self, source_url: str) -> DownloadedFiling:
            raise RuntimeError(source_url)

    sqs = FakeSqs(job_body())
    worker = FilingIngestionWorker(
        sqs, "queue-url", FakeStore(), FailingDownloader()  # type: ignore[arg-type]
    )
    try:
        worker.run_once(wait_time_seconds=0)
    except RuntimeError:
        pass
    else:
        raise AssertionError("Expected a failure.")
    assert not sqs.deleted


def test_empty_queue_returns_none() -> None:
    sqs = FakeSqs(None)
    worker = FilingIngestionWorker(
        sqs, "queue-url", FakeStore(), FakeDownloader()  # type: ignore[arg-type]
    )
    assert worker.run_once(wait_time_seconds=0) is None
