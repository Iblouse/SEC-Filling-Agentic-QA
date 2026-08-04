# Three-Minute Demo Script

## Preparation

1. Confirm the ECS service exists and is paused.
2. Confirm the local API-key file is readable.
3. Run `./scripts/day15_demo.sh`. The script starts one task, runs the protected smoke tests, and pauses the service on exit.
4. Open the GitHub Actions page, CloudWatch dashboard, and DynamoDB table in separate browser tabs.

## Minute 0:00 to 0:35, problem and architecture

> SEC filings contain valuable risk, capital, liquidity, governance, and event disclosures, but they are long, structurally inconsistent, and difficult to search reliably. I built a production-oriented system that ingests real SEC filings, benchmarks retrieval, generates evidence-bounded answers, validates citations, records feedback, and deploys securely on AWS.

Show `docs/architecture.svg` and point to:

- EDGAR ingestion through SQS and immutable S3 storage
- BM25 plus Titan dense retrieval and weighted RRF
- Nova answer generation and bounded critique
- FastAPI on Fargate behind CloudFront
- DynamoDB feedback, CloudWatch observability, and GitHub OIDC deployment

## Minute 0:35 to 1:35, successful grounded answer

Ask:

```text
What cybersecurity risks did Bank of America disclose in Item 1A?
```

Use filters:

```json
{
  "cik": "0000070858",
  "form": "10-K",
  "section_label": "item-1a"
}
```

Show that the response contains:

- `abstained: false`
- one or more citations
- Bank of America CIK on every citation
- filing accession and section metadata
- excerpts that can be inspected directly
- model-call count and latency

## Minute 1:35 to 2:10, bounded behavior

Explain:

> The model does not have an open-ended agent loop. It receives a bounded evidence set, generates an answer, undergoes citation validation and critique, and may revise at most once. If the evidence remains insufficient, it returns an abstention or unresolved state rather than continuing indefinitely.

Use an unsupported issuer or deliberately mismatched filing filter to demonstrate insufficient evidence when the service is configured for the test.

## Minute 2:10 to 2:35, feedback and observability

Submit feedback linked to the answer request ID. Show:

- HTTP 201 accepted response
- DynamoDB item with helpful flag, reason, timestamp, and TTL
- CloudWatch request, answer, and feedback metrics

## Minute 2:35 to 3:00, evaluation and deployment

Show `docs/evaluation_summary.md`:

> Weighted hybrid retrieval achieved the best Recall@10 and nDCG@10 on the active two-issuer benchmark. Dense retrieval achieved the best MRR. The Cohere reranking stage and the critique loop did not improve every aggregate metric, and I documented those regressions rather than hiding them.

Finish with the GitHub Actions workflow and explain that it uses OIDC, immutable ECR image tags, protected smoke tests, and automatic scale-down to zero.
