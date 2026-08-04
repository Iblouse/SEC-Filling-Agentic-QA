from __future__ import annotations

from io import BytesIO
from typing import Any

from botocore.exceptions import ClientError

from edgar_qa.parsing.models import ParsingStatus
from edgar_qa.parsing.pipeline import S3CuratedDocumentPipeline


class FakePaginator:
    def __init__(self, keys: list[str]) -> None:
        self._keys = keys

    def paginate(self, **_: Any) -> list[dict[str, Any]]:
        return [{"Contents": [{"Key": key} for key in self._keys]}]


class FakeS3:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}
        self.metadata: dict[tuple[str, str], dict[str, str]] = {}

    def head_object(self, Bucket: str, Key: str) -> dict[str, Any]:  # noqa: N803
        if (Bucket, Key) not in self.objects:
            raise ClientError(
                {
                    "Error": {"Code": "404", "Message": "Not Found"},
                    "ResponseMetadata": {"HTTPStatusCode": 404},
                },
                "HeadObject",
            )
        return {"Metadata": self.metadata.get((Bucket, Key), {})}

    def get_object(self, Bucket: str, Key: str) -> dict[str, Any]:  # noqa: N803
        return {
            "Body": BytesIO(self.objects[(Bucket, Key)]),
            "Metadata": self.metadata.get((Bucket, Key), {}),
        }

    def put_object(self, **kwargs: Any) -> dict[str, Any]:
        location = (kwargs["Bucket"], kwargs["Key"])
        if location in self.objects and kwargs.get("IfNoneMatch") == "*":
            raise ClientError(
                {
                    "Error": {"Code": "PreconditionFailed", "Message": "exists"},
                    "ResponseMetadata": {"HTTPStatusCode": 412},
                },
                "PutObject",
            )
        body = kwargs["Body"]
        self.objects[location] = body if isinstance(body, bytes) else body.read()
        self.metadata[location] = kwargs.get("Metadata", {})
        return {}

    def get_paginator(self, name: str) -> FakePaginator:
        assert name == "list_objects_v2"
        keys = [key for bucket, key in self.objects if bucket == "raw-bucket"]
        return FakePaginator(keys)


def raw_key() -> str:
    return (
        "filings/cik=0000019617/form=10-k/filing_date=2026-02-15/"
        "accession=000001961726000001/jpm-20251231.htm"
    )


def test_pipeline_writes_curated_json_and_is_idempotent() -> None:
    s3 = FakeS3()
    key = raw_key()
    body = b"<html><body><h2>Item 1. Business</h2><p>Banking text.</p></body></html>"
    s3.objects[("raw-bucket", key)] = body
    s3.metadata[("raw-bucket", key)] = {
        "content-sha256": "d" * 64,
        "form": "10-K",
        "cik": "0000019617",
        "accession-number": "000001961726000001",
    }
    pipeline = S3CuratedDocumentPipeline(s3, "raw-bucket", "curated-bucket")

    first = pipeline.parse_key(key)
    second = pipeline.parse_key(key)

    assert first.status == ParsingStatus.STORED
    assert first.block_count == 2
    assert first.section_count == 1
    assert second.status == ParsingStatus.ALREADY_EXISTS
    assert ("curated-bucket", first.curated_key) in s3.objects


def test_batch_skips_receipts() -> None:
    s3 = FakeS3()
    key = raw_key()
    s3.objects[("raw-bucket", key)] = b"<html><body><p>Text</p></body></html>"
    s3.objects[("raw-bucket", f"{key}.receipt.json")] = b"{}"
    pipeline = S3CuratedDocumentPipeline(s3, "raw-bucket", "curated-bucket")

    results = pipeline.parse_batch(maximum=5)

    assert len(results) == 1
    assert results[0].raw_key == key
