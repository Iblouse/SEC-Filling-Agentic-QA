from __future__ import annotations

from datetime import UTC, datetime

from edgar_qa.api.feedback import DynamoDBFeedbackStore
from edgar_qa.api.models import FeedbackRequest


class FakeTable:
    def __init__(self) -> None:
        self.items: list[dict[str, object]] = []

    def put_item(self, *, Item: dict[str, object]) -> dict[str, object]:
        self.items.append(Item)
        return {}


def test_feedback_store_writes_ttl_and_metadata() -> None:
    table = FakeTable()
    store = DynamoDBFeedbackStore(
        table,
        ttl_days=30,
        clock=lambda: datetime(2026, 8, 2, 12, 0, tzinfo=UTC),
    )

    response = store.save(
        "feedback-001",
        FeedbackRequest(
            request_id="answer-001",
            helpful=False,
            reason="incomplete",
            comment="  Missing one material risk.  ",
            citation_ids=["S1", "S2"],
        ),
    )

    item = table.items[0]
    assert item["request_id"] == "answer-001"
    assert item["feedback_id"] == "feedback-001"
    assert item["comment"] == "Missing one material risk."
    assert item["expires_at"] == 1788264000
    assert response.status == "accepted"
