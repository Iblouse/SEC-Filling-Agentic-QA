#!/usr/bin/env bash
set -euo pipefail

TERRAFORM_DIR="${1:-infrastructure/portfolio}"

command -v aws >/dev/null || { echo "AWS CLI is required." >&2; exit 1; }
command -v terraform >/dev/null || { echo "Terraform is required." >&2; exit 1; }

pushd "$TERRAFORM_DIR" >/dev/null

RAW_BUCKET=$(terraform output -raw raw_bucket_name)
CURATED_BUCKET=$(terraform output -raw curated_bucket_name)
QUEUE_URL=$(terraform output -raw ingestion_queue_url)
ECR_URL=$(terraform output -raw ecr_repository_url)
ECR_REPOSITORY=${ECR_URL#*/}

printf 'Checking raw bucket: %s\n' "$RAW_BUCKET"
aws s3api get-public-access-block --bucket "$RAW_BUCKET" >/dev/null
aws s3api get-bucket-versioning --bucket "$RAW_BUCKET" | grep -q 'Enabled'
aws s3api get-bucket-encryption --bucket "$RAW_BUCKET" >/dev/null

printf 'Checking curated bucket: %s\n' "$CURATED_BUCKET"
aws s3api get-public-access-block --bucket "$CURATED_BUCKET" >/dev/null
aws s3api get-bucket-versioning --bucket "$CURATED_BUCKET" | grep -q 'Enabled'
aws s3api get-bucket-encryption --bucket "$CURATED_BUCKET" >/dev/null

printf 'Checking ingestion queue.\n'
aws sqs get-queue-attributes \
  --queue-url "$QUEUE_URL" \
  --attribute-names RedrivePolicy SqsManagedSseEnabled >/dev/null

printf 'Checking ECR repository: %s\n' "$ECR_REPOSITORY"
aws ecr describe-repositories --repository-names "$ECR_REPOSITORY" >/dev/null

printf '{"status":"verified"}\n' > /tmp/sec-qa-foundation-smoke.json
aws s3 cp /tmp/sec-qa-foundation-smoke.json "s3://$RAW_BUCKET/smoke/foundation.json" >/dev/null
aws s3 cp "s3://$RAW_BUCKET/smoke/foundation.json" - | grep -q 'verified'

printf 'AWS foundation verification passed.\n'
popd >/dev/null
