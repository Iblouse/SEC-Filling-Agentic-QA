#!/usr/bin/env bash
set -euo pipefail

export AWS_PROFILE="${AWS_PROFILE:-sec-qa}"
export AWS_REGION="${AWS_REGION:-us-east-1}"

python -m edgar_qa.agentic_cli verify-critic
python -m edgar_qa.agentic_cli evaluate \
  --dataset evaluation/sec_questions.jsonl \
  --maximum-questions 3 \
  --candidate-k 20 \
  --rerank-candidates 10 \
  --evidence-k 5
