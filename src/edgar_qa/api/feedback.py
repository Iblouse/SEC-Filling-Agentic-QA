from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Protocol

import boto3
from botocore.exceptions import ClientError

from edgar_qa.api.models import FeedbackRequest, FeedbackResponse
from edgar_qa.api.settings import APISettings


class FeedbackStoreError(RuntimeError):
    """Raised when durable feedback storage fails."""


class DynamoDBTable(Protocol):
    def put_item(self, *, Item: dict[str, object]) -> dict[str, object]: ...


class FeedbackStore(Protocol):
    def save(
        self,
        feedback_id: str,
        feedback: FeedbackRequest,
    ) -> FeedbackResponse: ...


Clock = Callable[[], datetime]


class DynamoDBFeedbackStore:
    """Persist feedback using request ID as the partition key."""

    def __init__(
        self,
        table: DynamoDBTable,
        *,
        ttl_days: int,
        clock: Clock | None = None,
    ) -> None:
        self.table = table
        self.ttl_days = ttl_days
        self.clock = clock or (lambda: datetime.now(UTC))

    def save(
        self,
        feedback_id: str,
        feedback: FeedbackRequest,
    ) -> FeedbackResponse:
        created_at = self.clock().astimezone(UTC)
        expiration = created_at + timedelta(days=self.ttl_days)
        item: dict[str, object] = {
            "request_id": feedback.request_id,
            "feedback_id": feedback_id,
            "helpful": feedback.helpful,
            "citation_ids": feedback.citation_ids,
            "created_at": created_at.isoformat(),
            "expires_at": int(expiration.timestamp()),
        }
        if feedback.reason is not None:
            item["reason"] = feedback.reason
        if feedback.comment is not None:
            item["comment"] = feedback.comment

        try:
            self.table.put_item(Item=item)
        except ClientError as exc:
            raise FeedbackStoreError("DynamoDB feedback write failed.") from exc

        return FeedbackResponse(
            feedback_id=feedback_id,
            request_id=feedback.request_id,
            expires_at=expiration.isoformat(),
        )


def build_feedback_store(settings: APISettings) -> FeedbackStore | None:
    """Build the feedback store only when a table is configured."""
    if settings.qa_feedback_table_name is None:
        return None
    session = boto3.Session(region_name=settings.aws_region)
    table = session.resource("dynamodb").Table(settings.qa_feedback_table_name)
    return DynamoDBFeedbackStore(
        table,
        ttl_days=settings.qa_feedback_ttl_days,
    )
