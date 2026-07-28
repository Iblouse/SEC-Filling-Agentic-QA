# Day 11 Design: FastAPI Service Boundary

## Objective

Expose the Day 10 bounded QA workflow through a stable HTTP API before deploying it to AWS.
The API must reuse the retrieval index across requests, preserve deterministic citation and
critique safeguards, return source provenance, and emit operational request metadata.

## Endpoints

- `GET /healthz`: process liveness only. It must not call Bedrock.
- `GET /readyz`: reports whether the corpus, embedding cache, retrieval index, reranker, and
  QA service initialized successfully.
- `POST /v1/answer`: accepts a question plus optional SEC metadata filters and returns the
  final bounded-agent answer plus cited source metadata.

## API boundary

Public clients do not control RRF weights, candidate depth, model IDs, or maximum revisions.
Those values are server-side environment configuration. This prevents a UI client from
silently changing the evaluated retrieval/agent behavior.

## Runtime reuse

The hybrid index is built once during FastAPI lifespan startup and stored in `app.state`.
Each request reuses the same in-memory BM25/dense index and model adapters. Bedrock calls
remain request-scoped.

## Failure handling

- Invalid API input: FastAPI validation (`422`).
- Invalid retrieval configuration/question: `400`.
- Bedrock or reranking dependency failure after retries: `502`.
- Service initialization failure: `/readyz` returns `503` and `/v1/answer` remains unavailable.
- `/healthz` remains a cheap liveness probe.

## Observability

Every request receives an `X-Request-ID`. Valid caller-provided IDs are preserved; otherwise
one is generated. The service writes request ID, method, path, status, and latency to stdout,
which can be routed to CloudWatch when the container is deployed on ECS.

## Container strategy

Day 11 creates `Dockerfile.api`. The corpus and embedding cache are mounted read-only for the
local container test. Day 12 will replace this local-artifact assumption with AWS deployment
packaging and ECS/Fargate infrastructure.
