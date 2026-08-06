#!/usr/bin/env bash
set -euo pipefail

export AWS_PROFILE="${AWS_PROFILE:-sec-qa}"
export AWS_REGION="${AWS_REGION:-us-east-1}"

TF_DIR="${TF_DIR:-infrastructure/portfolio}"
KEY_FILE="${SEC_QA_API_KEY_FILE:-$HOME/.config/sec-filing-agentic-qa/api-key}"
BASE_URL="$(terraform -chdir="$TF_DIR" output -raw api_public_base_url)"
ORIGIN_URL="$(terraform -chdir="$TF_DIR" output -raw api_base_url)"

if [[ ! -r "$KEY_FILE" ]]; then
  printf 'API key file not found: %s\n' "$KEY_FILE" >&2
  exit 2
fi

API_KEY="$(cat "$KEY_FILE")"
printf 'Testing secure edge URL: %s\n' "$BASE_URL"

curl --fail --silent --show-error \
  --retry 8 \
  --retry-delay 5 \
  "$BASE_URL/healthz" |
jq .

curl --fail --silent --show-error \
  --retry 8 \
  --retry-delay 5 \
  "$BASE_URL/readyz" |
jq .

UNAUTHENTICATED_STATUS="$(
  curl --silent --show-error \
    --output /tmp/day14-unauthenticated.json \
    --write-out '%{http_code}' \
    -X POST \
    "$BASE_URL/v1/answer" \
    -H 'Content-Type: application/json' \
    -d '{"question":"What cybersecurity risks were disclosed?"}'
)"

if [[ "$UNAUTHENTICATED_STATUS" != "401" ]]; then
  cat /tmp/day14-unauthenticated.json >&2
  printf 'Expected unauthenticated status 401, received %s.\n' \
    "$UNAUTHENTICATED_STATUS" >&2
  exit 1
fi

ANSWER_RESPONSE="$(
  curl --fail --silent --show-error \
    -X POST \
    "$BASE_URL/v1/answer" \
    -H 'Content-Type: application/json' \
    -H 'X-API-Key: '"$API_KEY" \
    -H 'X-Request-ID: day14-answer-smoke-001' \
    -d '{
      "question": "What cybersecurity risks did Bank of America disclose in Item 1A?",
      "filters": {
        "cik": "0000070858",
        "form": "10-K",
        "section_label": "item-1a"
      }
    }'
)"

printf '%s\n' "$ANSWER_RESPONSE" | jq .
printf '%s\n' "$ANSWER_RESPONSE" | jq -e '
  .abstained == false
  and (.citations | length) > 0
  and all(.citations[]; .cik == "0000070858")
' >/dev/null

FEEDBACK_RESPONSE="$(
  curl --fail --silent --show-error \
    -X POST \
    "$BASE_URL/v1/feedback" \
    -H 'Content-Type: application/json' \
    -H 'X-API-Key: '"$API_KEY" \
    -H 'X-Request-ID: day14-feedback-smoke-001' \
    -d '{
      "request_id": "day14-answer-smoke-001",
      "helpful": true,
      "reason": "relevant",
      "comment": "Production API protected endpoint smoke test."
    }'
)"

printf '%s\n' "$FEEDBACK_RESPONSE" | jq .
printf '%s\n' "$FEEDBACK_RESPONSE" | jq -e '
  .status == "accepted"
  and .request_id == "day14-answer-smoke-001"
' >/dev/null

if curl \
  --silent \
  --show-error \
  --max-time 8 \
  --output /dev/null \
  "$ORIGIN_URL/healthz"; then
  printf 'Direct ALB origin remains reachable; CloudFront restriction failed.\n' >&2
  exit 1
fi

printf 'Production API security assertions passed: HTTPS edge, API key, citations, feedback, origin blocked.\n'
