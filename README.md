# SEC Filing Agentic QA

A production-oriented retrieval and grounded question-answering system for public SEC filings. It ingests real 10-K, 10-Q, and 8-K filings, preserves immutable source artifacts, benchmarks multiple retrieval strategies, generates answers with source-level citations, applies a bounded critique workflow, records user feedback, and deploys a protected API on AWS.

**Production-supported issuers:** JPMorgan Chase and Bank of America  
**Cloud:** AWS  
**Language:** Python 3.11+  
**Release posture:** portfolio release with the serving environment paused by default for cost control

## What this project demonstrates

- Real EDGAR ingestion rather than synthetic documents
- Immutable raw and curated S3 storage
- Idempotent SQS-based ingestion jobs
- Filing parsing with stable block, section, and chunk identifiers
- BM25, Titan dense retrieval, weighted reciprocal-rank fusion, and Cohere reranking
- Grounded generation with Amazon Nova and structured citation validation
- A bounded generate, critique, optional single-revision workflow
- FastAPI on ECS Fargate behind an ALB and CloudFront HTTPS
- API-key protection with AWS Secrets Manager
- Durable feedback in DynamoDB with TTL
- CloudWatch logs, embedded metrics, dashboard, and alarms
- Terraform infrastructure and GitHub Actions deployment through OIDC
- Explicit pause controls so Fargate does not run continuously

## Architecture

![SEC Filing Agentic QA production architecture](ArchitectureDiagram.png)

The end-to-end flow is documented in [docs/architecture.md](docs/architecture.md).

## Evaluation highlights

The committed benchmark contains **18 labeled questions** covering two issuers and three filing types:

| Scope | Count |
|---|---:|
| JPMorgan Chase | 13 |
| Bank of America | 5 |
| 10-K | 5 |
| 10-Q | 6 |
| 8-K | 7 |

Retrieval metrics recalculated for the active 18-question benchmark:

| Retrieval system | Recall@5 | Recall@10 | MRR | nDCG@10 |
|---|---:|---:|---:|---:|
| BM25 | 0.456 | 0.515 | 0.583 | 0.521 |
| Titan dense | 0.492 | 0.571 | **0.667** | 0.608 |
| Weighted hybrid RRF | **0.511** | **0.585** | 0.639 | **0.608** |
| Hybrid plus Cohere rerank | 0.489 | 0.567 | 0.611 | 0.570 |

Weighted hybrid retrieval produced the strongest recall and nDCG, while dense retrieval produced the best first-relevant-result ranking. Cohere reranking did not improve this small benchmark, so the project retains evaluation evidence rather than claiming that every additional model improved results.

The grounded QA evaluation on q001 through q015 produced a **93.3% citation-validity rate**, a **60.0% gold-evidence hit rate**, and a **33.3% abstention rate**. The bounded critique workflow revised 20.0% of answers but did not improve aggregate evidence metrics. It is therefore presented as a controlled safety and review mechanism, not as an automatic quality gain.

See [docs/evaluation_summary.md](docs/evaluation_summary.md) and the machine-readable summaries under [evaluation/results](evaluation/results).

## Supported API

### Health

```http
GET /healthz
GET /readyz
```

### Grounded answer

```http
POST /v1/answer
X-API-Key: <key>
Content-Type: application/json
```

```json
{
  "question": "What cybersecurity risks did Bank of America disclose in Item 1A?",
  "filters": {
    "cik": "0000070858",
    "form": "10-K",
    "section_label": "item-1a"
  }
}
```

The response includes the answer, abstention and revision flags, citation-validation status, model-call count, latency, and filing citations with excerpts.

### Feedback

```http
POST /v1/feedback
X-API-Key: <key>
Content-Type: application/json
```

```json
{
  "request_id": "demo-answer-001",
  "helpful": true,
  "reason": "relevant",
  "comment": "The answer cited the correct risk-factor section."
}
```

The feedback record is stored in DynamoDB with automatic TTL expiration.

## Local setup

```bash
python3.12 -m venv sec-venv
source sec-venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
cp .env.example .env
```

Set an identifiable SEC user agent in `.env`:

```text
SEC_USER_AGENT="Your Name your.email@example.com"
```

Run the quality gate:

```bash
make check
```

Retrieve recent JPMorgan filing metadata:

```bash
edgar-qa submissions \
  --cik 0000019617 \
  --output data/raw/jpmorgan-submissions.json
```

## System components

- Controlled SEC EDGAR discovery and ingestion
- Deterministic SQS jobs and idempotent workers
- Immutable raw and curated S3 storage
- Filing-aware parsing with stable source and chunk identifiers
- BM25 lexical retrieval
- Amazon Titan dense retrieval
- Weighted reciprocal-rank fusion
- Evidence-bounded answer generation with Amazon Nova
- Citation validation and explicit abstention
- Bounded critique with at most one revision
- Protected FastAPI service on ECS Fargate
- CloudFront and Application Load Balancer delivery
- DynamoDB feedback with TTL
- CloudWatch logs, metrics, dashboards, and alarms
- Terraform infrastructure and GitHub Actions OIDC deployment
- Immutable ECR releases and scale-to-zero cost controls
## Deployment and cost controls

Terraform keeps the ECS service at a desired count of zero by default. The deployment workflow starts one task, runs protected smoke tests, and returns the service to zero unless explicitly instructed to leave it running.

```bash
./scripts/resume_api.sh
./scripts/pause_api.sh
```

The public serving layer can still incur ALB, public IPv4, CloudFront request, storage, log, metric, alarm, and Secrets Manager charges. Review [docs/security_and_cost_controls.md](docs/security_and_cost_controls.md) before leaving the environment deployed.

## Security design

- `/v1/answer` and `/v1/feedback` require `X-API-Key`
- The API key is stored in Secrets Manager and injected through the ECS task definition
- GitHub Actions assumes an AWS role through repository-and-environment-scoped OIDC
- The ALB accepts origin traffic from the CloudFront managed prefix list
- Direct public access to the Fargate task is blocked by security-group rules
- Raw credentials, Terraform state, local data, and virtual environments are excluded from Git

## Known limitations

- The current production corpus is intentionally limited to JPMorgan Chase and Bank of America.
- The active retrieval benchmark has 18 questions. The latest QA and bounded-agent evaluations cover q001 through q015 and should be rerun before making claims about all 18 questions.
- The serving stack must be recreated if Terraform state and AWS resources drift after a partial apply or manual deletion.
- CloudFront provides public HTTPS, while the current CloudFront-to-ALB origin connection uses HTTP inside an origin-restricted path. End-to-end TLS requires a custom domain and ACM certificate.

See [docs/known_limitations.md](docs/known_limitations.md).

## Portfolio materials

- [Architecture](docs/architecture.md)
- [Evaluation summary](docs/evaluation_summary.md)
- [Three-minute demo](docs/demo_script.md)
- [Security and cost controls](docs/security_and_cost_controls.md)
- [Resume, LinkedIn, and interview material](docs/portfolio_materials.md)
- [Release checklist](docs/release_checklist.md)

## License and data

SEC filings are public source documents retrieved from SEC EDGAR. This repository does not commit downloaded filings, generated corpora, embeddings, Terraform state, credentials, or API keys.
