#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${AWS_INGESTION_QUEUE_URL:-}" ]]; then
  echo "AWS_INGESTION_QUEUE_URL is not set."
  echo "Run: source scripts/load_terraform_outputs.sh"
  exit 1
fi

python -m edgar_qa.worker_cli drain --maximum "${1:-5}"
