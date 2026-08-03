#!/usr/bin/env bash
set -euo pipefail

BASE_URL="$(terraform -chdir=infrastructure/portfolio output -raw api_base_url)"

printf 'Testing %s\n' "$BASE_URL"
curl --fail --silent --show-error "$BASE_URL/healthz" | jq .
curl --fail --silent --show-error "$BASE_URL/readyz" | jq .

ANSWER_RESPONSE="$(
  curl --fail --silent --show-error \
    -X POST \
    "$BASE_URL/v1/answer" \
    -H 'Content-Type: application/json' \
    -H 'X-Request-ID: day13-answer-smoke-001' \
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

ANSWER_REQUEST_ID="$(printf '%s\n' "$ANSWER_RESPONSE" | jq -r '.request_id')"
CITATION_IDS="$(printf '%s\n' "$ANSWER_RESPONSE" | jq -c '[.citations[].source_id]')"

FEEDBACK_PAYLOAD="$(
  jq -n \
    --arg request_id "$ANSWER_REQUEST_ID" \
    --argjson citation_ids "$CITATION_IDS" \
    '{
      request_id: $request_id,
      helpful: true,
      reason: "relevant",
      comment: "Day 13 deployment smoke test.",
      citation_ids: $citation_ids
    }'
)"

FEEDBACK_RESPONSE="$(
  curl --fail --silent --show-error \
    -X POST \
    "$BASE_URL/v1/feedback" \
    -H 'Content-Type: application/json' \
    -H 'X-Request-ID: day13-feedback-smoke-001' \
    --data-binary "$FEEDBACK_PAYLOAD"
)"

printf '%s\n' "$FEEDBACK_RESPONSE" | jq .
printf '%s\n' "$FEEDBACK_RESPONSE" | jq -e '
  .status == "accepted"
  and .feedback_id == "day13-feedback-smoke-001"
  and .request_id == "day13-answer-smoke-001"
' >/dev/null

printf 'Day 13 smoke assertions passed: answer citations=%s, feedback=%s\n' \
  "$(printf '%s\n' "$ANSWER_RESPONSE" | jq '.citations | length')" \
  "$(printf '%s\n' "$FEEDBACK_RESPONSE" | jq -r '.status')"
