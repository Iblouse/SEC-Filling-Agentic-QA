#!/usr/bin/env bash

TERRAFORM_DIR="${1:-infrastructure/portfolio}"

AWS_RAW_BUCKET="$(terraform -chdir="$TERRAFORM_DIR" output -raw raw_bucket_name)" || return 1 2>/dev/null || exit 1
AWS_INGESTION_QUEUE_URL="$(terraform -chdir="$TERRAFORM_DIR" output -raw ingestion_queue_url)" || return 1 2>/dev/null || exit 1
AWS_REGION="${AWS_REGION:-us-east-1}"

export AWS_RAW_BUCKET
export AWS_INGESTION_QUEUE_URL
export AWS_REGION

cat <<EOF
Loaded AWS discovery configuration:
  AWS_REGION=$AWS_REGION
  AWS_RAW_BUCKET=$AWS_RAW_BUCKET
  AWS_INGESTION_QUEUE_URL=$AWS_INGESTION_QUEUE_URL
EOF
