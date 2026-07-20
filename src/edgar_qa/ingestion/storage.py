from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from botocore.exceptions import ClientError

from edgar_qa.ingestion.downloader import DownloadedFiling
from edgar_qa.ingestion.models import IngestionJob


@dataclass(frozen=True)
class StoredObject:
    created: bool
    receipt_key: str


class S3RawFilingStore:
    """Stores immutable filing bodies and ingestion receipts."""

    def __init__(self, s3_client: Any) -> None:
        self._s3 = s3_client

    def exists(self, bucket: str, key: str) -> bool:
        try:
            self._s3.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError as exc:
            status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            code = exc.response.get("Error", {}).get("Code")
            if status == 404 or code in {"404", "NoSuchKey", "NotFound"}:
                return False
            raise

    def put_filing_if_absent(
        self,
        job: IngestionJob,
        downloaded: DownloadedFiling,
    ) -> StoredObject:
        metadata = {
            "content-sha256": downloaded.content_sha256,
            "job-id": job.job_id,
            "cik": job.filing.cik,
            "accession-number": job.filing.accession_number,
            "form": job.filing.form,
        }
        try:
            self._s3.put_object(
                Bucket=job.destination_bucket,
                Key=job.destination_key,
                Body=downloaded.body,
                ContentType=downloaded.content_type,
                Metadata=metadata,
                IfNoneMatch="*",
            )
            created = True
        except ClientError as exc:
            status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            code = exc.response.get("Error", {}).get("Code")
            if status == 412 or code in {"PreconditionFailed", "ConditionalRequestConflict"}:
                created = False
            else:
                raise

        receipt_key = f"{job.destination_key}.receipt.json"
        receipt = {
            "schema_version": "1.0",
            "job": job.model_dump(mode="json"),
            "download": {
                "content_sha256": downloaded.content_sha256,
                "bytes": len(downloaded.body),
                "fetched_at": downloaded.fetched_at.isoformat(),
                "content_type": downloaded.content_type,
                "final_url": downloaded.final_url,
                "etag": downloaded.etag,
                "last_modified": downloaded.last_modified,
            },
            "storage": {
                "bucket": job.destination_bucket,
                "key": job.destination_key,
                "created": created,
            },
        }
        try:
            self._s3.put_object(
                Bucket=job.destination_bucket,
                Key=receipt_key,
                Body=json.dumps(receipt, indent=2, sort_keys=True).encode("utf-8"),
                ContentType="application/json",
                Metadata={
                    "content-sha256": downloaded.content_sha256,
                    "job-id": job.job_id,
                },
                IfNoneMatch="*",
            )
        except ClientError as exc:
            status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            code = exc.response.get("Error", {}).get("Code")
            if status != 412 and code not in {
                "PreconditionFailed",
                "ConditionalRequestConflict",
            }:
                raise

        return StoredObject(created=created, receipt_key=receipt_key)
