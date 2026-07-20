from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from edgar_qa.ingestion.downloader import SecFilingDownloader
from edgar_qa.ingestion.models import IngestionJob, IngestionResult, IngestionStatus
from edgar_qa.ingestion.storage import S3RawFilingStore


class InvalidIngestionMessageError(RuntimeError):
    """Raised when an SQS body is not a valid ingestion job."""


class FilingIngestionWorker:
    def __init__(
        self,
        sqs_client: Any,
        queue_url: str,
        store: S3RawFilingStore,
        downloader: SecFilingDownloader,
        visibility_timeout_seconds: int = 120,
    ) -> None:
        if visibility_timeout_seconds < 1:
            raise ValueError("visibility_timeout_seconds must be positive.")
        self._sqs = sqs_client
        self._queue_url = queue_url
        self._store = store
        self._downloader = downloader
        self._visibility_timeout_seconds = visibility_timeout_seconds

    def run_once(self, wait_time_seconds: int = 5) -> IngestionResult | None:
        response = self._sqs.receive_message(
            QueueUrl=self._queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=wait_time_seconds,
            VisibilityTimeout=self._visibility_timeout_seconds,
            AttributeNames=["ApproximateReceiveCount"],
            MessageAttributeNames=["All"],
        )
        messages = response.get("Messages", [])
        if not messages:
            return None

        # message = messages[0]
        # result = self.process_message_body(message["Body"])

        # self._sqs.delete_message(
        #     QueueUrl=self._queue_url,
        #     ReceiptHandle=message["ReceiptHandle"],
        # )
        
        message = messages[0]
        try:
            # Process and delete valid messages
            result = self.process_message_body(message["Body"])
            self._sqs.delete_message(
                QueueUrl=self._queue_url,
                ReceiptHandle=message["ReceiptHandle"],
            )
            return result
        except InvalidIngestionMessageError as exc:
            # Catch the mismatch, log it, and clear it from the queue
            print(f"Dropping malformed discovery message from queue: {exc}")
            self._sqs.delete_message(
                QueueUrl=self._queue_url,
                ReceiptHandle=message["ReceiptHandle"],
            )
            return None

            return result

    def process_message_body(self, body: str) -> IngestionResult:
        try:
            job = IngestionJob.model_validate(json.loads(body))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise InvalidIngestionMessageError(
                "SQS message is not a valid ingestion job."
            ) from exc

        if self._store.exists(job.destination_bucket, job.destination_key):
            return IngestionResult(
                status=IngestionStatus.ALREADY_EXISTS,
                job_id=job.job_id,
                bucket=job.destination_bucket,
                key=job.destination_key,
                receipt_key=f"{job.destination_key}.receipt.json",
            )

        downloaded = self._downloader.download(str(job.filing.source_url))
        stored = self._store.put_filing_if_absent(job, downloaded)
        status = IngestionStatus.STORED if stored.created else IngestionStatus.ALREADY_EXISTS

        return IngestionResult(
            status=status,
            job_id=job.job_id,
            bucket=job.destination_bucket,
            key=job.destination_key,
            content_sha256=downloaded.content_sha256,
            bytes_stored=len(downloaded.body),
            fetched_at=downloaded.fetched_at,
            receipt_key=stored.receipt_key,
            response_metadata={
                "content_type": downloaded.content_type,
                "final_url": downloaded.final_url,
                "etag": downloaded.etag,
                "last_modified": downloaded.last_modified,
            },
        )
