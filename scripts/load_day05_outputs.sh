#!/usr/bin/env bash

TERRAFORM_DIR="${1:-infrastructure/portfolio}"

# shellcheck source=/dev/null
source scripts/load_terraform_outputs.sh "$TERRAFORM_DIR" || return 1 2>/dev/null || exit 1

AWS_CURATED_BUCKET="$(terraform -chdir="$TERRAFORM_DIR" output -raw curated_bucket_name)" \
  || return 1 2>/dev/null || exit 1
export AWS_CURATED_BUCKET

cat <<EOF
Loaded Day 5 parsing configuration:
  AWS_CURATED_BUCKET=$AWS_CURATED_BUCKET
EOF
