#!/usr/bin/env bash
set -euo pipefail

export AWS_PROFILE="${AWS_PROFILE:-sec-qa}"
export AWS_REGION="${AWS_REGION:-us-east-1}"
export AWS_DEFAULT_REGION="$AWS_REGION"
export AWS_PAGER=""

TF_DIR="${TF_DIR:-infrastructure/portfolio}"
CLUSTER="$(terraform -chdir="$TF_DIR" output -raw api_cluster_name)"
SERVICE="$(terraform -chdir="$TF_DIR" output -raw api_service_name)"

pause_service() {
  printf '\nReturning ECS service to zero tasks...\n'
  aws ecs update-service \
    --cluster "$CLUSTER" \
    --service "$SERVICE" \
    --desired-count 0 \
    >/dev/null 2>&1 || true

  aws ecs wait services-stable \
    --cluster "$CLUSTER" \
    --services "$SERVICE" \
    >/dev/null 2>&1 || true
}
trap pause_service EXIT INT TERM

STATUS="$(
  aws ecs describe-services \
    --cluster "$CLUSTER" \
    --services "$SERVICE" \
    --query 'services[0].status' \
    --output text
)"

if [[ "$STATUS" != "ACTIVE" ]]; then
  printf 'ECS service %s/%s is not ACTIVE.\n' "$CLUSTER" "$SERVICE" >&2
  printf 'Run the Day 15 Terraform drift-recovery steps before the demo.\n' >&2
  exit 2
fi

aws ecs update-service \
  --cluster "$CLUSTER" \
  --service "$SERVICE" \
  --desired-count 1 \
  >/dev/null

aws ecs wait services-stable \
  --cluster "$CLUSTER" \
  --services "$SERVICE"

./scripts/smoke_test_api.sh

printf '\nDemo smoke test passed. The cleanup trap will pause ECS.\n'
