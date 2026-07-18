from __future__ import annotations

from typing import Any

from edgar_qa.aws.storage import canonical_json_bytes
from edgar_qa.sec.models import FilingIngestionJob


class SqsFilingQueue:
    """Publishes deterministic filing jobs to a standard SQS queue."""

    def __init__(self, client: Any, queue_url: str) -> None:
        self._client = client
        self.queue_url = queue_url

    def send(self, job: FilingIngestionJob) -> str:
        body = canonical_json_bytes(job.model_dump(mode="json")).decode("utf-8")
        response = self._client.send_message(
            QueueUrl=self.queue_url,
            MessageBody=body,
            MessageAttributes={
                "job_id": {"DataType": "String", "StringValue": job.job_id},
                "cik": {"DataType": "String", "StringValue": job.filing.cik},
                "form": {"DataType": "String", "StringValue": job.filing.form},
            },
        )
        return str(response["MessageId"])
