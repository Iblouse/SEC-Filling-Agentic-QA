#!/usr/bin/env bash
set -euo pipefail

export AWS_PROFILE="${AWS_PROFILE:-sec-qa}"
export AWS_REGION="${AWS_REGION:-us-east-1}"

TF_DIR="${TF_DIR:-infrastructure/portfolio}"

DISTRIBUTION_ID="$(
  terraform -chdir="$TF_DIR" output -raw api_cloudfront_distribution_id
)"
SECRET_ARN="$(terraform -chdir="$TF_DIR" output -raw api_key_secret_arn)"
TASK_DEFINITION="$(
  terraform -chdir="$TF_DIR" output -raw api_task_definition_arn
)"

printf 'CloudFront distribution\n'
aws cloudfront get-distribution \
  --id "$DISTRIBUTION_ID" \
  --query 'Distribution.{status:Status,domain:DomainName,enabled:DistributionConfig.Enabled}'

printf '\nAPI-key secret\n'
aws secretsmanager describe-secret \
  --secret-id "$SECRET_ARN" \
  --query '{name:Name,arn:ARN,lastChanged:LastChangedDate}'

printf '\nECS secret injection\n'
aws ecs describe-task-definition \
  --task-definition "$TASK_DEFINITION" \
  --query 'taskDefinition.containerDefinitions[0].secrets'

printf '\nGitHub deployment role\n'
terraform -chdir="$TF_DIR" output -raw github_deploy_role_arn
printf '\n'
