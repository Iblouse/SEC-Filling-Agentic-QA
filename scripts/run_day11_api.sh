#!/usr/bin/env bash
set -euo pipefail

export AWS_PROFILE="${AWS_PROFILE:-sec-qa}"
export AWS_REGION="${AWS_REGION:-us-east-1}"
export QA_CORPUS_PATH="${QA_CORPUS_PATH:-data/retrieval/sec_chunks.jsonl}"
export QA_EMBEDDING_CACHE_PATH="${QA_EMBEDDING_CACHE_PATH:-data/retrieval/titan_v2_512_embeddings.jsonl}"

exec uvicorn edgar_qa.api.app:app \
  --host 0.0.0.0 \
  --port "${PORT:-8080}"
