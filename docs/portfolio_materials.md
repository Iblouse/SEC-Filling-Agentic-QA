# Portfolio and Interview Materials

## Resume bullets

- Built and deployed a production-oriented SEC filing question-answering platform on AWS that ingests real 10-K, 10-Q, and 8-K filings through SQS and immutable S3 layers, exposes a protected FastAPI service on ECS Fargate, and captures feedback and operational metrics in DynamoDB and CloudWatch.
- Benchmarked BM25, Amazon Titan dense retrieval, weighted reciprocal-rank fusion, and Cohere reranking on an 18-question labeled corpus; hybrid retrieval achieved 0.585 Recall@10 and 0.608 nDCG@10, while dense retrieval achieved the highest MRR at 0.667.
- Implemented evidence-bounded Amazon Nova answer generation with citation validation, controlled abstention, and a maximum one-revision critique workflow; automated secure deployments with Terraform, GitHub Actions OIDC, immutable ECR images, protected smoke tests, and automatic Fargate scale-down.

## LinkedIn project description

Built an end-to-end SEC Filing Agentic QA platform using real EDGAR filings and AWS. The system ingests 10-K, 10-Q, and 8-K filings into immutable S3 layers, parses stable sections and chunks, benchmarks BM25 and Amazon Titan dense retrieval, combines rankings through weighted reciprocal-rank fusion, and generates citation-backed answers with Amazon Nova.

I added a bounded critique workflow with a maximum of one revision, FastAPI deployment on ECS Fargate, CloudFront HTTPS, Secrets Manager API-key protection, DynamoDB feedback with TTL, CloudWatch metrics and alarms, Terraform infrastructure, and GitHub Actions deployment through OIDC.

The evaluation was important: hybrid retrieval achieved the strongest Recall@10 and nDCG@10 on the active two-issuer benchmark, while dense retrieval achieved the best MRR. Cohere reranking and the critique stage did not improve every aggregate metric, so I documented the tradeoffs and limitations rather than presenting them as automatic gains.

## Sixty-second explanation

> I built a production-oriented question-answering system over real SEC filings. It starts with controlled EDGAR ingestion, deterministic SQS jobs, and immutable raw and curated S3 storage. I parse filings into stable sections and chunks, then benchmark BM25, Titan dense retrieval, weighted reciprocal-rank fusion, and Cohere reranking. The answer layer uses Amazon Nova with a fixed evidence set, citation validation, and a bounded critic that can request at most one revision. I deployed the API on ECS Fargate behind CloudFront, protected it with a Secrets Manager API key, stored feedback in DynamoDB, added CloudWatch metrics and alarms, and automated deployments through GitHub OIDC. The strongest result was hybrid Recall@10 of 0.585, and I also documented where reranking and critique did not improve the benchmark.

## Five-minute technical walkthrough

1. **Problem:** SEC filings are public but long, inconsistent, and difficult to search with reliable citations.
2. **Data pipeline:** EDGAR discovery produces stable jobs; workers store source HTML and receipts; parsing creates stable blocks, sections, and diagnostics.
3. **Retrieval:** BM25 and Titan dense retrieval are evaluated independently; weighted RRF combines them; reranking is optional and benchmarked.
4. **Grounding:** Nova receives only selected evidence. Source IDs are validated against that evidence before an answer is accepted.
5. **Bounded agent:** The critic can accept or request one revision. There is no unbounded autonomous loop.
6. **Serving:** FastAPI runs on Fargate behind CloudFront and an ALB. Protected paths require an API key from Secrets Manager.
7. **Feedback and operations:** DynamoDB stores user feedback with TTL; CloudWatch captures logs, latency, answer, abstention, revision, and feedback signals.
8. **Delivery:** Terraform defines infrastructure; GitHub Actions uses OIDC, immutable images, manual production approval, smoke tests, SSM release state, and scale-down.
9. **Evaluation:** Hybrid retrieval improved recall, dense improved MRR, and the project records regressions from reranking and critique.
10. **Limitations:** Production scope is two issuers, Citigroup section parsing remains experimental, and the final QA benchmark should be rerun across all 18 active questions.
