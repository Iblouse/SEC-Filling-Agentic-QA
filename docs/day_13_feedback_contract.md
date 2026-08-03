# Day 13 Feedback API Contract

## Request

`POST /v1/feedback`

```json
{
  "request_id": "day13-answer-smoke-001",
  "helpful": false,
  "reason": "citation_issue",
  "comment": "The second citation did not support the claim.",
  "citation_ids": ["S2"]
}
```

Accepted reasons:

- `relevant`
- `incomplete`
- `incorrect`
- `citation_issue`
- `other`

## Response

```json
{
  "status": "accepted",
  "feedback_id": "day13-feedback-smoke-001",
  "request_id": "day13-answer-smoke-001",
  "expires_at": "2026-10-31T16:00:00+00:00"
}
```

The `X-Request-ID` supplied to the feedback request becomes `feedback_id`. Reusing that ID overwrites the same DynamoDB item instead of creating an additional record.
