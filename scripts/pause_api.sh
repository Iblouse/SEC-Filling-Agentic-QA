#!/usr/bin/env bash
set -euo pipefail

export AWS_PROFILE="${AWS_PROFILE:-sec-qa}"
export AWS_REGION="${AWS_REGION:-us-east-1}"

TF_DIR="${TF_DIR:-infrastructure/portfolio}"
CLUSTER="$(terraform -chdir="$TF_DIR" output -raw api_cluster_name)"
SERVICE="$(terraform -chdir="$TF_DIR" output -raw api_service_name)"

printf 'Scaling %s/%s to zero tasks...\n' "$CLUSTER" "$SERVICE"
aws ecs update-service \
  --cluster "$CLUSTER" \
  --service "$SERVICE" \
  --desired-count 0 \
  >/dev/null

aws ecs wait services-stable \
  --cluster "$CLUSTER" \
  --services "$SERVICE"

aws ecs describe-services \
  --cluster "$CLUSTER" \
  --services "$SERVICE" \
  --query 'services[0].{desired:desiredCount,running:runningCount,pending:pendingCount}'
