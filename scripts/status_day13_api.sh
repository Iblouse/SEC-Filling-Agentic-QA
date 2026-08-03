#!/usr/bin/env bash
set -euo pipefail

export AWS_PROFILE="${AWS_PROFILE:-sec-qa}"
export AWS_REGION="${AWS_REGION:-us-east-1}"

CLUSTER="$(terraform -chdir=infrastructure/portfolio output -raw api_cluster_name)"
SERVICE="$(terraform -chdir=infrastructure/portfolio output -raw api_service_name)"
TABLE="$(terraform -chdir=infrastructure/portfolio output -raw api_feedback_table_name)"
TARGET_GROUP="$(terraform -chdir=infrastructure/portfolio output -raw api_target_group_arn)"
PROJECT_NAME="$(terraform -chdir=infrastructure/portfolio output -raw project_name)"

printf 'ECS service\n'
aws ecs describe-services \
  --cluster "$CLUSTER" \
  --services "$SERVICE" \
  --query 'services[0].{status:status,desired:desiredCount,running:runningCount,pending:pendingCount,taskDefinition:taskDefinition}'

printf '\nALB target health\n'
aws elbv2 describe-target-health \
  --target-group-arn "$TARGET_GROUP" \
  --query 'TargetHealthDescriptions[*].{target:Target.Id,state:TargetHealth.State,reason:TargetHealth.Reason}'

printf '\nFeedback table\n'
aws dynamodb describe-table \
  --table-name "$TABLE" \
  --query 'Table.{name:TableName,status:TableStatus,billingMode:BillingModeSummary.BillingMode,itemCount:ItemCount}'

printf '\nCloudWatch alarms\n'
aws cloudwatch describe-alarms \
  --alarm-name-prefix "${PROJECT_NAME}-api-" \
  --query 'MetricAlarms[*].{name:AlarmName,state:StateValue,metric:MetricName}'
