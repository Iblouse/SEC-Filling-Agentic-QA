#!/usr/bin/env bash
set -euo pipefail

TF_DIR="${TF_DIR:-infrastructure/portfolio}"
BASE_URL="$(terraform -chdir="$TF_DIR" output -raw api_base_url)"

printf 'Testing %s\n' "$BASE_URL"
curl --fail --silent --show-error "$BASE_URL/healthz" | jq .
curl --fail --silent --show-error "$BASE_URL/readyz" | jq .

curl --fail --silent --show-error \
  -X POST \
  "$BASE_URL/v1/answer" \
  -H 'Content-Type: application/json' \
  -H 'X-Request-ID: day12-smoke-001' \
  -d '{
    "question": "What cybersecurity risks did Bank of America disclose in Item 1A?",
    "filters": {
      "cik": "0000070858",
      "form": "10-K",
      "section_label": "item-1a"
    }
  }' | jq .
