#!/usr/bin/env bash
set -euo pipefail

export AWS_PROFILE="${AWS_PROFILE:-sec-qa}"
export AWS_REGION="${AWS_REGION:-us-east-1}"

TF_DIR="${TF_DIR:-infrastructure/portfolio}"
KEY_FILE="${SEC_QA_API_KEY_FILE:-$HOME/.config/sec-filing-agentic-qa/api-key}"

SECRET_ARN="$(terraform -chdir="$TF_DIR" output -raw api_key_secret_arn)"
API_KEY="$(openssl rand -hex 32)"

aws secretsmanager put-secret-value \
  --secret-id "$SECRET_ARN" \
  --secret-string "$API_KEY" \
  >/dev/null

mkdir -p "$(dirname "$KEY_FILE")"
umask 077
printf '%s' "$API_KEY" > "$KEY_FILE"
chmod 600 "$KEY_FILE"

printf 'Stored a new API key in AWS Secrets Manager.\n'
printf 'Local key file: %s\n' "$KEY_FILE"
printf 'The key value was not printed.\n'
