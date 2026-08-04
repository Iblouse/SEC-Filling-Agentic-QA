#!/usr/bin/env bash
set -euo pipefail

export AWS_PROFILE="${AWS_PROFILE:-sec-qa}"
export AWS_REGION="${AWS_REGION:-us-east-1}"
export AWS_DEFAULT_REGION="$AWS_REGION"
export AWS_PAGER=""
export GH_PAGER=cat
export GIT_PAGER=cat

TF_DIR="${TF_DIR:-infrastructure/portfolio}"

failures=0

check() {
  local description="$1"
  shift
  printf '\n[%s]\n' "$description"
  if "$@"; then
    printf 'PASS\n'
  else
    printf 'FAIL\n' >&2
    failures=$((failures + 1))
  fi
}

not_tracked() {
  ! git ls-files sec-venv .venv | grep -q .
}

no_sensitive_tracked() {
  ! git ls-files | grep -Eq '(^|/)(\.env|terraform\.tfstate|terraform\.tfvars|api-key|credentials)$'
}

latest_workflow_success() {
  local workflow="$1"
  local conclusion
  conclusion="$(
    gh run list \
      --workflow "$workflow" \
      --limit 1 \
      --json conclusion \
      --jq '.[0].conclusion // "missing"'
  )"
  printf '%s: %s\n' "$workflow" "$conclusion"
  [[ "$conclusion" == "success" ]]
}

service_active_and_paused() {
  local cluster service status desired running
  cluster="$(terraform -chdir="$TF_DIR" output -raw api_cluster_name)"
  service="$(terraform -chdir="$TF_DIR" output -raw api_service_name)"
  read -r status desired running < <(
    aws ecs describe-services \
      --cluster "$cluster" \
      --services "$service" \
      --query 'services[0].[status,desiredCount,runningCount]' \
      --output text
  )
  printf 'status=%s desired=%s running=%s\n' "$status" "$desired" "$running"
  [[ "$status" == "ACTIVE" && "$desired" == "0" && "$running" == "0" ]]
}

check "Virtual environment is not tracked" not_tracked
check "No obvious secret or state files are tracked" no_sensitive_tracked
check "Python quality gate" make check
check "Terraform formatting" terraform -chdir="$TF_DIR" fmt -check -recursive
check "Terraform validation" terraform -chdir="$TF_DIR" validate
check "Latest CI workflow succeeded" latest_workflow_success ci.yml
check "Latest deployment workflow succeeded" latest_workflow_success deploy.yml
check "ECS service is active and paused" service_active_and_paused

printf '\nRelease-gate failures: %s\n' "$failures"
[[ "$failures" -eq 0 ]]
