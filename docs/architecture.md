# Architecture Decision Record 001

## Decision

Use AWS for the SEC filing application.

## Production target

```text
SEC EDGAR
  -> EventBridge filing discovery
  -> SQS ingestion queue
  -> ECS ingestion workers
  -> S3 immutable raw zone
  -> parsing and section extraction
  -> S3 curated zone
  -> OpenSearch hybrid index
  -> Bedrock answer and critic models
  -> Step Functions bounded critique workflow
  -> FastAPI and analyst interface on ECS
  -> DynamoDB feedback
  -> CloudWatch operations and quality metrics
```

## Agentic critique contract

The system may execute no more than two refinement rounds.

Permitted outcomes:

- accept
- retrieve_more
- regenerate_with_existing_evidence
- abstain
- request_human_review

No agent may alter infrastructure, indexes, prompts, or production settings directly.
