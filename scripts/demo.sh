#!/usr/bin/env bash
set -euo pipefail

export AWS_PROFILE="${AWS_PROFILE:-sec-qa}"
export AWS_REGION="${AWS_REGION:-us-east-1}"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-$AWS_REGION}"
export AWS_PAGER=""

TF_DIR="${TF_DIR:-infrastructure/portfolio}"
QUESTION_FILE="${QUESTION_FILE:-evaluation/sec_questions.jsonl}"
KEY_FILE="${SEC_QA_API_KEY_FILE:-$HOME/.config/sec-filing-agentic-qa/api-key}"
OUTPUT_FILE="${SEC_QA_DEMO_OUTPUT:-/tmp/sec-qa-demo-response.json}"

for command in aws terraform curl jq; do
  if ! command -v "$command" >/dev/null 2>&1; then
    echo "Required command not found: $command" >&2
    exit 1
  fi
done

usage() {
  cat <<'EOF'
Usage:
  ./scripts/demo.sh
      Display an interactive question-selection menu.

  ./scripts/demo.sh --list
      List available benchmark questions.

  ./scripts/demo.sh --index NUMBER
      Run a benchmark question by its displayed number.

  ./scripts/demo.sh --custom
      Enter a custom question and filters interactively.

Environment variables:
  SEC_QA_BASE_URL
      Optional deployed API URL. When omitted, the script resolves
      the current CloudFront URL from Terraform and AWS.

  SEC_QA_API_KEY
      Optional API key. When omitted, the script reads the key from:
      ~/.config/sec-filing-agentic-qa/api-key

  QUESTION_FILE
      Optional JSONL question file. Default:
      evaluation/sec_questions.jsonl

  SEC_QA_DEMO_OUTPUT
      Output file for the complete JSON response. Default:
      /tmp/sec-qa-demo-response.json
EOF
}

normalize_cik() {
  local value="$1"

  if [[ -z "$value" ]]; then
    printf '%s' ""
    return
  fi

  if [[ "$value" =~ ^[0-9]+$ ]]; then
    printf '%010d' "$((10#$value))"
  else
    printf '%s' "$value"
  fi
}

resolve_base_url() {
  if [[ -n "${SEC_QA_BASE_URL:-}" ]]; then
    BASE_URL="${SEC_QA_BASE_URL%/}"
    return
  fi

  local distribution_id
  local distribution_domain

  distribution_id="$(
    terraform -chdir="$TF_DIR" \
      output -raw api_cloudfront_distribution_id
  )"

  distribution_domain="$(
    aws cloudfront get-distribution \
      --id "$distribution_id" \
      --query 'Distribution.DomainName' \
      --output text
  )"

  BASE_URL="https://${distribution_domain}"
}

load_api_key() {
  if [[ -n "${SEC_QA_API_KEY:-}" ]]; then
    API_KEY="$SEC_QA_API_KEY"
    return
  fi

  if [[ ! -r "$KEY_FILE" ]]; then
    echo "API key file not found or unreadable:" >&2
    echo "  $KEY_FILE" >&2
    echo >&2
    echo "Set SEC_QA_API_KEY or create the key file." >&2
    exit 2
  fi

  API_KEY="$(<"$KEY_FILE")"

  if [[ -z "$API_KEY" ]]; then
    echo "The API key is empty." >&2
    exit 2
  fi
}

create_question_catalog() {
  CATALOG_FILE="$(mktemp)"
  trap 'rm -f "${CATALOG_FILE:-}"' EXIT

  if [[ ! -f "$QUESTION_FILE" ]]; then
    echo "Question file not found: $QUESTION_FILE" >&2
    echo "The custom-question option will still be available." >&2
    printf '[]\n' > "$CATALOG_FILE"
    return
  fi

  jq -s '
    map({
      id: (
        .question_id
        // .id
        // .qid
        // ""
      ),
      question: (
        .question
        // .query
        // .text
        // ""
      ),
      cik: (
        .filters.cik
        // .cik
        // .issuer_cik
        // ""
        | tostring
      ),
      form: (
        .filters.form
        // .form
        // .filing_type
        // ""
      ),
      section_label: (
        .filters.section_label
        // .section_label
        // .section
        // ""
      )
    })
    | map(select(.question != ""))
  ' "$QUESTION_FILE" > "$CATALOG_FILE"
}

list_questions() {
  local count

  count="$(jq 'length' "$CATALOG_FILE")"

  if [[ "$count" -eq 0 ]]; then
    echo "No benchmark questions were detected."
    return
  fi

  jq -r '
    to_entries[]
    | "\(.key + 1)) "
      + (
          if .value.id == ""
          then ""
          else "[" + .value.id + "] "
          end
        )
      + .value.question
  ' "$CATALOG_FILE"
}

select_issuer() {
  echo
  echo "Select an issuer filter:"
  echo "  1) Bank of America"
  echo "  2) JPMorgan Chase"
  echo "  3) No issuer filter"
  echo "  4) Enter a different CIK"
  echo

  read -r -p "Issuer selection [1]: " issuer_choice
  issuer_choice="${issuer_choice:-1}"

  case "$issuer_choice" in
    1)
      CIK="0000070858"
      ;;
    2)
      CIK="0000019617"
      ;;
    3)
      CIK=""
      ;;
    4)
      read -r -p "Enter the issuer CIK: " CIK
      CIK="$(normalize_cik "$CIK")"
      ;;
    *)
      echo "Invalid issuer selection." >&2
      exit 2
      ;;
  esac
}

select_custom_question() {
  echo
  read -r -p "Enter the question: " QUESTION

  if [[ -z "$QUESTION" ]]; then
    echo "A question is required." >&2
    exit 2
  fi

  select_issuer

  read -r -p "Filing form [10-K]: " FORM
  FORM="${FORM:-10-K}"

  read -r -p \
    "Section label, for example item-1a [leave blank for no section filter]: " \
    SECTION_LABEL
}

select_catalog_question() {
  local selection="$1"
  local count
  local selected_json

  count="$(jq 'length' "$CATALOG_FILE")"

  if ! [[ "$selection" =~ ^[0-9]+$ ]]; then
    echo "The selection must be a number." >&2
    exit 2
  fi

  if (( selection < 1 || selection > count )); then
    echo "Selection must be between 1 and $count." >&2
    exit 2
  fi

  selected_json="$(
    jq -c ".[$((selection - 1))]" "$CATALOG_FILE"
  )"

  QUESTION="$(
    jq -r '.question' <<<"$selected_json"
  )"

  CIK="$(
    jq -r '.cik' <<<"$selected_json"
  )"

  FORM="$(
    jq -r '.form' <<<"$selected_json"
  )"

  SECTION_LABEL="$(
    jq -r '.section_label' <<<"$selected_json"
  )"

  CIK="$(normalize_cik "$CIK")"

  if [[ -z "$FORM" ]]; then
    FORM="10-K"
  fi
}

select_question_interactively() {
  local count
  local selection

  count="$(jq 'length' "$CATALOG_FILE")"

  echo
  echo "Available demonstration questions"
  echo "================================="
  echo

  list_questions

  echo
  echo "  0) Enter a custom question"
  echo

  if [[ "$count" -gt 0 ]]; then
    read -r -p "Select a question [1]: " selection
    selection="${selection:-1}"
  else
    selection="0"
  fi

  if [[ "$selection" == "0" ]]; then
    select_custom_question
  else
    select_catalog_question "$selection"
  fi
}

build_payload() {
  FILTERS="$(
    jq -n \
      --arg cik "$CIK" \
      --arg form "$FORM" \
      --arg section_label "$SECTION_LABEL" \
      '{
        cik: $cik,
        form: $form,
        section_label: $section_label
      }
      | with_entries(
          select(
            .value != ""
            and .value != null
          )
        )'
  )"

  PAYLOAD="$(
    jq -n \
      --arg question "$QUESTION" \
      --argjson filters "$FILTERS" \
      '{
        question: $question,
        filters: $filters
      }'
  )"
}

check_endpoint() {
  local health_json=""
  local ready_json=""
  local answer="y"
  local attempt

  echo
  echo "Checking deployed API..."
  echo

  if health_json="$(
    curl \
      --fail \
      --silent \
      --show-error \
      "$BASE_URL/healthz" \
      2>/dev/null
  )"; then
    echo "$health_json" | jq .
  else
    echo "The API is not currently healthy."
    echo "The ECS service may be paused at zero running tasks."
    echo

    if [[ ! -x "./scripts/resume_api.sh" ]]; then
      echo "Required script not found or not executable:" >&2
      echo "  ./scripts/resume_api.sh" >&2
      exit 3
    fi

    if [[ -t 0 ]]; then
      read -r -p "Start the API now? [Y/n]: " answer
      answer="${answer:-y}"
    fi

    case "$answer" in
      y|Y|yes|YES)
        echo
        echo "Starting the API..."
        echo

        ./scripts/resume_api.sh
        ;;
      *)
        echo "The demonstration cannot continue while the API is paused." >&2
        exit 3
        ;;
    esac

    health_json=""

    for attempt in $(seq 1 36); do
      if health_json="$(
        curl \
          --fail \
          --silent \
          "$BASE_URL/healthz" \
          2>/dev/null
      )"; then
        break
      fi

      sleep 5
    done

    if [[ -z "$health_json" ]]; then
      echo "The API did not become healthy." >&2

      if [[ -x "./scripts/status_api.sh" ]]; then
        echo
        ./scripts/status_api.sh || true
      fi

      exit 3
    fi

    echo "$health_json" | jq .
  fi

  ready_json="$(
    curl \
      --fail \
      --silent \
      --show-error \
      --retry 6 \
      --retry-delay 3 \
      "$BASE_URL/readyz"
  )"

  echo "$ready_json" | jq .
}

run_question() {
  local request_id

  request_id="interview-demo-$(date +%Y%m%d%H%M%S)"

  echo
  echo "Selected question"
  echo "================="
  echo "$QUESTION"
  echo

  echo "Filters"
  echo "======="
  jq . <<<"$FILTERS"
  echo

  echo "Submitting request..."
  echo

  curl \
    --fail \
    --silent \
    --show-error \
    --retry 2 \
    --retry-delay 2 \
    -X POST \
    "$BASE_URL/v1/answer" \
    -H 'Content-Type: application/json' \
    -H "X-API-Key: $API_KEY" \
    -H "X-Request-ID: $request_id" \
    --data "$PAYLOAD" |
  tee "$OUTPUT_FILE" |
  jq .

  echo
  echo "Complete response saved to:"
  echo "  $OUTPUT_FILE"
}

main() {
  local mode="interactive"
  local selected_index=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --list)
        mode="list"
        shift
        ;;
      --index)
        if [[ $# -lt 2 ]]; then
          echo "--index requires a number." >&2
          exit 2
        fi

        mode="index"
        selected_index="$2"
        shift 2
        ;;
      --custom)
        mode="custom"
        shift
        ;;
      --help|-h)
        usage
        exit 0
        ;;
      *)
        echo "Unknown option: $1" >&2
        usage >&2
        exit 2
        ;;
    esac
  done

  create_question_catalog

  case "$mode" in
    list)
      list_questions
      exit 0
      ;;
    index)
      select_catalog_question "$selected_index"
      ;;
    custom)
      select_custom_question
      ;;
    interactive)
      select_question_interactively
      ;;
  esac

  resolve_base_url
  load_api_key
  build_payload
  check_endpoint
  run_question
}

main "$@"
