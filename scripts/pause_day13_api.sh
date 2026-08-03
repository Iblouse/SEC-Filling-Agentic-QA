#!/usr/bin/env bash
set -euo pipefail

export AWS_PROFILE="${AWS_PROFILE:-sec-qa}"
export AWS_REGION="${AWS_REGION:-us-east-1}"

CLUSTER="$(terraform -chdir=infrastructure/portfolio output -raw api_cluster_name)"
SERVICE="$(terraform -chdir=infrastructure/portfolio output -raw api_service_name)"

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

printf '\nFargate tasks are stopped. The ALB remains provisioned and can still incur charges.\n'
