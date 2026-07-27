#!/usr/bin/env bash
set -euo pipefail

export AWS_PROFILE="${AWS_PROFILE:-sec-qa}"
export AWS_REGION="${AWS_REGION:-us-east-1}"

python -m edgar_qa.hybrid_cli evaluate \
  --dataset evaluation/sec_questions.jsonl \
  --top-k 10 \
  --candidate-k 20

python -m edgar_qa.hybrid_cli compare

cat <<'EOF'
RRF evaluation complete.
Next, run:
  python -m edgar_qa.hybrid_cli verify-rerank
Then, if Bedrock rerank access succeeds:
  python -m edgar_qa.hybrid_cli evaluate-reranked --dataset evaluation/sec_questions.jsonl --top-k 10 --candidate-k 20 --rerank-candidates 20
  python -m edgar_qa.hybrid_cli compare
EOF
