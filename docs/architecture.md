# Architecture

## System objective

The system answers questions about public SEC filings while preserving the source document, retrieval evidence, citation metadata, bounded model behavior, and operational trace needed to audit an answer.

## End-to-end flow

1. The EDGAR client retrieves issuer submissions metadata using an identifiable SEC user agent and controlled request rate.
2. Discovery writes immutable manifests to the raw S3 bucket and emits deterministic SQS jobs.
3. The ingestion worker downloads filing HTML, verifies responses, and stores immutable raw objects and receipts.
4. The parser converts HTML into structured blocks, tables, sections, and stable identifiers in curated S3.
5. The retrieval corpus produces stable chunks. Amazon Titan creates 512-dimensional normalized embeddings.
6. BM25 and dense retrieval produce candidates. Weighted reciprocal-rank fusion combines their rankings, and Cohere reranking is available as an evaluated optional stage.
7. Amazon Nova generates an evidence-bounded answer. Citation validation verifies that citation identifiers refer only to supplied evidence.
8. A critic returns `accept` or `revise`. The workflow permits at most one revision before final validation and possible abstention.
9. FastAPI exposes health, answer, and feedback endpoints on ECS Fargate.
10. CloudFront provides the public HTTPS endpoint. The ALB routes to Fargate, and protected API paths require a key injected from Secrets Manager.
11. DynamoDB stores feedback with TTL. CloudWatch receives application logs, embedded metrics, dashboards, and alarms.
12. GitHub Actions uses OIDC to obtain short-lived AWS credentials, pushes immutable images to ECR, deploys ECS, runs smoke tests, records the accepted image tag in SSM, and pauses Fargate by default.

## Retrieval and answer contract

```text
Question + optional SEC metadata filters
  -> BM25 candidates
  -> Titan dense candidates
  -> weighted reciprocal-rank fusion
  -> optional Cohere reranking
  -> top evidence set
  -> Nova answer with source IDs
  -> citation validation
  -> Nova critic
  -> zero or one revision
  -> final validation or abstention
```

The agent cannot mutate infrastructure, prompts, indexes, or production settings. Its action space is deliberately restricted to accepting the answer, requesting one revision, or returning insufficient evidence.

## Production scope

| Issuer | CIK | Status |
|---|---|---|
| JPMorgan Chase | `0000019617` | Supported |
| Bank of America | `0000070858` | Supported |
| Citigroup | `0000831001` | Experimental, excluded from production section-filtered retrieval |

## Storage and identity

- Raw S3 keys preserve downloaded source bytes and ingestion receipts.
- Curated S3 objects preserve structured filing blocks, sections, diagnostics, and source metadata.
- Filing accession numbers and content hashes support idempotency.
- Stable section and chunk IDs connect retrieval results to answer citations.
- Runtime corpus, embedding cache, and manifest checksums must agree before readiness succeeds.

## Serving security

- CloudFront is the public HTTPS endpoint.
- The ALB security group accepts CloudFront origin-facing traffic.
- The task security group accepts only ALB traffic on the application port.
- `/v1/answer` and `/v1/feedback` require `X-API-Key`.
- Secrets Manager injects the key into ECS at startup.
- GitHub deployment uses OIDC rather than permanent AWS keys.

## Cost posture

- ECS desired count defaults to zero.
- Deployment starts one task only for validation unless explicitly left running.
- S3, ECR, DynamoDB, CloudWatch, Secrets Manager, ALB, CloudFront, and public IPv4 resources may still incur charges while retained.
