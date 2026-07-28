# Day 11 Checklist

- [ ] Apply patch and install dependencies.
- [ ] `make check` passes.
- [ ] `/healthz` returns 200 without invoking Bedrock.
- [ ] `/readyz` returns 200 when corpus/cache initialization succeeds.
- [ ] `/v1/answer` answers a real SEC question.
- [ ] Response includes `X-Request-ID` and the same ID in JSON.
- [ ] Response includes final answer, critic verdict, revision flag, token count, latency, and cited SEC source metadata.
- [ ] Unsupported question preserves `INSUFFICIENT_EVIDENCE:` behavior.
- [ ] Docker image builds from `Dockerfile.api`.
- [ ] Dockerized `/healthz` and `/readyz` pass.
- [ ] Dockerized `/v1/answer` succeeds with read-only retrieval artifacts and AWS credentials mounted.
- [ ] No `.env`, AWS credentials, local corpus, or embedding cache are copied into the image.
- [ ] Day 11 code, tests, docs, Dockerfile, and dependency updates are committed.
