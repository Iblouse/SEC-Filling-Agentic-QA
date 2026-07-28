
chunk_id() {
  local prefix="$1"
  local matches

  matches=$(
    jq -r \
      --arg prefix "$prefix" \
      'select(.chunk_id | startswith($prefix)) | .chunk_id' \
      data/retrieval/sec_chunks.jsonl
  )

  local count
  count=$(printf '%s\n' "$matches" | grep -c .)

  if [[ "$count" -eq 0 ]]; then
    echo "ERROR: No chunk matches prefix: $prefix" >&2
    return 1
  fi

  if [[ "$count" -gt 1 ]]; then
    echo "ERROR: Prefix matches multiple chunks: $prefix" >&2
    printf '%s\n' "$matches" >&2
    return 1
  fi

  printf '%s\n' "$matches"
}

label_question() {
  local question_id="$1"
  shift

  local corpus="data/retrieval/sec_chunks.jsonl"
  local resolved_ids=()

  for value in "$@"; do
    local matches
    matches=$(
      jq -r \
        --arg prefix "$value" \
        'select(.chunk_id | startswith($prefix)) | .chunk_id' \
        "$corpus"
    )

    local count
    count=$(printf '%s\n' "$matches" | grep -c .)

    if [[ "$count" -eq 0 ]]; then
      echo "ERROR: No chunk matches: $value" >&2
      return 1
    fi

    if [[ "$count" -gt 1 ]]; then
      echo "ERROR: Prefix is ambiguous: $value" >&2
      printf '%s\n' "$matches" >&2
      return 1
    fi

    resolved_ids+=("$matches")
  done

  # Remove duplicates after resolving prefixes to complete IDs.
  local unique_ids=("${(@f)$(printf '%s\n' "${resolved_ids[@]}" | sort -u)}")

  echo "Selected: ${#resolved_ids[@]} chunks"
  echo "Unique:   ${#unique_ids[@]} chunks"

  local args=()
  for chunk in "${unique_ids[@]}"; do
    args+=(--chunk-id "$chunk")
  done

  python -m edgar_qa.retrieval_cli label-question \
    --question-id "$question_id" \
    "${args[@]}"
}