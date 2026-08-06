#!/usr/bin/env bash
set -euo pipefail

export AWS_PROFILE="${AWS_PROFILE:-sec-qa}"
export AWS_REGION="${AWS_REGION:-us-east-1}"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-$AWS_REGION}"
export AWS_PAGER=""

TF_DIR="${TF_DIR:-infrastructure/portfolio}"

for command in terraform aws; do
  if ! command -v "$command" >/dev/null 2>&1; then
    echo "Required command not found: $command" >&2
    exit 1
  fi
done

CLUSTER="$(
  terraform -chdir="$TF_DIR" \
    output -raw api_cluster_name
)"

SERVICE="$(
  terraform -chdir="$TF_DIR" \
    output -raw api_service_name
)"

echo "ECS cluster: $CLUSTER"
echo "ECS service: $SERVICE"
echo

aws ecs describe-services \
  --cluster "$CLUSTER" \
  --services "$SERVICE" \
  --query 'services[0].{
    status:status,
    desired:desiredCount,
    running:runningCount,
    pending:pendingCount,
    taskDefinition:taskDefinition,
    deploymentStatus:deployments[0].rolloutState
  }' \
  --output json
