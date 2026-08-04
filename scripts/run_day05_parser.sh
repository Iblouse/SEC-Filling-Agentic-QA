#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${AWS_RAW_BUCKET:-}" || -z "${AWS_CURATED_BUCKET:-}" ]]; then
  echo "AWS_RAW_BUCKET and AWS_CURATED_BUCKET are required."
  echo "Run: source scripts/load_day05_outputs.sh"
  exit 1
fi

python -m edgar_qa.parsing_cli parse-batch --maximum "${1:-5}"
