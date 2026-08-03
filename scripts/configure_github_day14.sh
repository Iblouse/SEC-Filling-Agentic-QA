#!/usr/bin/env bash
set -euo pipefail

export AWS_PROFILE="${AWS_PROFILE:-sec-qa}"
export AWS_REGION="${AWS_REGION:-us-east-1}"

TF_DIR="${TF_DIR:-infrastructure/portfolio}"
ENVIRONMENT="${GITHUB_DEPLOY_ENVIRONMENT:-production}"
KEY_FILE="${SEC_QA_API_KEY_FILE:-$HOME/.config/sec-filing-agentic-qa/api-key}"

command -v gh >/dev/null || {
  echo "GitHub CLI is required. Install it and run: gh auth login" >&2
  exit 2
}

[[ -r "$KEY_FILE" ]] || {
  printf 'API key file not found: %s\n' "$KEY_FILE" >&2
  exit 2
}

REPOSITORY="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
PROJECT_NAME="$(terraform -chdir="$TF_DIR" output -raw project_name)"
DEPLOY_ROLE="$(terraform -chdir="$TF_DIR" output -raw github_deploy_role_arn)"
ECR_URL="$(terraform -chdir="$TF_DIR" output -raw ecr_repository_url)"
CLUSTER="$(terraform -chdir="$TF_DIR" output -raw api_cluster_name)"
SERVICE="$(terraform -chdir="$TF_DIR" output -raw api_service_name)"
BASE_URL="$(terraform -chdir="$TF_DIR" output -raw api_public_base_url)"
IMAGE_TAG_PARAMETER="$(
  terraform -chdir="$TF_DIR" output -raw api_image_tag_parameter_name
)"

gh api \
  --method PUT \
  "repos/$REPOSITORY/environments/$ENVIRONMENT" \
  >/dev/null

gh variable set AWS_REGION --env "$ENVIRONMENT" --body "$AWS_REGION"
gh variable set AWS_DEPLOY_ROLE_ARN --env "$ENVIRONMENT" --body "$DEPLOY_ROLE"
gh variable set ECR_REPOSITORY_URL --env "$ENVIRONMENT" --body "$ECR_URL"
gh variable set ECS_CLUSTER --env "$ENVIRONMENT" --body "$CLUSTER"
gh variable set ECS_SERVICE --env "$ENVIRONMENT" --body "$SERVICE"
gh variable set ECS_TASK_DEFINITION_FAMILY \
  --env "$ENVIRONMENT" \
  --body "${PROJECT_NAME}-api"
gh variable set ECS_CONTAINER_NAME --env "$ENVIRONMENT" --body "api"
gh variable set API_BASE_URL --env "$ENVIRONMENT" --body "$BASE_URL"
gh variable set IMAGE_TAG_PARAMETER \
  --env "$ENVIRONMENT" \
  --body "$IMAGE_TAG_PARAMETER"
gh secret set SEC_QA_API_KEY --env "$ENVIRONMENT" < "$KEY_FILE"

printf 'Configured GitHub Environment %s for %s.\n' \
  "$ENVIRONMENT" "$REPOSITORY"
printf 'Add a required reviewer in GitHub Settings > Environments > %s.\n' \
  "$ENVIRONMENT"
