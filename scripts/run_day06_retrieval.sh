#!/usr/bin/env bash
set -euo pipefail

python -m edgar_qa.retrieval_cli export-corpus \
  --maximum-documents "${1:-100}" \
  --maximum-terms 350 \
  --overlap-terms 50

python -m edgar_qa.retrieval_cli create-evaluation-template \
  --maximum-questions "${2:-10}"

echo "Corpus and evaluation template created."
echo "Review questions in evaluation/sec_questions.jsonl, search each question, and label relevant chunk IDs."
