# Day 13 Design: Feedback, Metrics, Alarms, and Cost Controls

## Objective

Day 13 makes the deployed SEC QA API observable and creates a durable feedback loop without adding always-on application compute.

## Feedback flow

1. A client calls `POST /v1/answer` and receives a stable `request_id`.
2. The client calls `POST /v1/feedback` with that answer request ID.
3. The API stores the feedback in DynamoDB using:
   - partition key: `request_id`
   - sort key: `feedback_id`
4. DynamoDB TTL removes expired feedback after the configured retention window.

The table uses on-demand billing because portfolio traffic is low and unpredictable.

## Feedback fields

- `request_id`: answer request being evaluated
- `feedback_id`: feedback HTTP request ID, also used as an idempotency key
- `helpful`: binary usefulness signal
- `reason`: controlled failure or success category
- `comment`: optional human explanation
- `citation_ids`: source IDs selected by the user
- `created_at`: UTC timestamp
- `expires_at`: DynamoDB TTL epoch timestamp

## Metrics flow

The API writes one-line JSON events that follow CloudWatch Embedded Metric Format. The ECS `awslogs` driver sends these events to the existing application log group, where CloudWatch extracts metrics.

Dimensions are intentionally low-cardinality:

- `Service`
- `Environment`

Request IDs, paths, and feedback IDs remain log properties rather than metric dimensions.

## Metrics

- `RequestCount`
- `RequestLatency`
- `ClientErrorCount`
- `ServerErrorCount`
- `AnswerCount`
- `AnswerLatency`
- `AbstentionCount`
- `RevisionCount`
- `CitationFailureCount`
- `ModelCallCount`
- `TokenCount`
- `FeedbackCount`
- `NegativeFeedbackCount`

## Alarms

- Any server error within five minutes
- Maximum request latency above 15 seconds
- Five or more abstentions within fifteen minutes
- Unhealthy ALB targets for two consecutive one-minute periods

Alarm notification actions are optional. Set `api_alarm_sns_topic_arn` to an existing SNS topic ARN to enable notifications.

## Cost controls

`pause_day13_api.sh` sets the ECS desired count to zero. This stops Fargate tasks but does not delete the Application Load Balancer. The ALB remains a separately billable resource until removed through Terraform.

`resume_day13_api.sh` starts one task, waits for service stability, and runs the Day 13 smoke test.

The DynamoDB table uses on-demand capacity and TTL. Container Insights remains disabled by default.
