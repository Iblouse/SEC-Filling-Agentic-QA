import json
from datetime import UTC, datetime
from typing import Any

from botocore.exceptions import ClientError

from edgar_qa.aws.queue import SqsFilingQueue
from edgar_qa.aws.storage import S3JsonStore, content_addressed_key
from edgar_qa.discovery import FilingDiscoveryService
from edgar_qa.sec.client import SecClient

MOCK_SUBMISSIONS = {
    "cik": "19617",
    "name": "JPMORGAN CHASE & CO",
    "filings": {
        "recent": {
            "accessionNumber": [
                "0000019617-26-000001",
                "0000019617-26-000002",
            ],
            "filingDate": ["2026-02-15", "2026-01-20"],
            "reportDate": ["2025-12-31", "2026-01-20"],
            "form": ["10-K", "8-K"],
            "fileNumber": ["001-05805", "001-05805"],
            "filmNumber": ["261234567", "261234568"],
            "primaryDocument": ["jpm-20251231.htm", "jpm-8k.htm"],
            "isInlineXBRL": [1, 1],
        }
    },
}


class FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}

    def put_object(self, **kwargs: Any) -> dict[str, Any]:
        identity = (kwargs["Bucket"], kwargs["Key"])
        if identity in self.objects and kwargs.get("IfNoneMatch") == "*":
            raise ClientError(
                {
                    "Error": {"Code": "PreconditionFailed", "Message": "exists"},
                    "ResponseMetadata": {"HTTPStatusCode": 412},
                },
                "PutObject",
            )
        self.objects[identity] = kwargs["Body"]
        return {"ETag": "test"}


class FakeSqsClient:
    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []

    def send_message(self, **kwargs: Any) -> dict[str, str]:
        self.messages.append(kwargs)
        return {"MessageId": f"message-{len(self.messages)}"}


class FakeSecClient(SecClient):
    def __init__(self) -> None:
        pass

    def get_company_submissions(self, cik: str | int) -> dict[str, Any]:
        return MOCK_SUBMISSIONS


def test_content_addressed_key_is_deterministic() -> None:
    first = content_addressed_key("manifests/test", {"b": 2, "a": 1})
    second = content_addressed_key("manifests/test", {"a": 1, "b": 2})
    assert first == second
    assert first.startswith("manifests/test/sha256=")


def test_s3_store_does_not_overwrite_immutable_json() -> None:
    client = FakeS3Client()
    store = S3JsonStore(client, "raw-bucket")
    assert store.put_if_absent("manifest.json", {"value": 1}) is True
    assert store.put_if_absent("manifest.json", {"value": 1}) is False


def test_discovery_persists_manifests_and_queues_deterministic_jobs() -> None:
    s3_client = FakeS3Client()
    sqs_client = FakeSqsClient()
    service = FilingDiscoveryService(
        sec_client=FakeSecClient(),
        raw_store=S3JsonStore(s3_client, "raw-bucket"),
        queue=SqsFilingQueue(sqs_client, "https://sqs.test/queue"),
    )

    summary = service.discover(
        cik="19617",
        limit=2,
        discovered_at=datetime(2026, 7, 18, 12, 0, tzinfo=UTC),
    )

    assert summary.filing_count == 2
    assert summary.queued_count == 2
    assert len(s3_client.objects) == 2
    assert len(sqs_client.messages) == 2

    first_message = sqs_client.messages[0]
    payload = json.loads(first_message["MessageBody"])
    assert payload["filing"]["accession_number"] == "0000019617-26-000001"
    assert payload["destination_bucket"] == "raw-bucket"
    assert payload["destination_key"].endswith("/jpm-20251231.htm")
    assert payload["job_id"] == first_message["MessageAttributes"]["job_id"]["StringValue"]
