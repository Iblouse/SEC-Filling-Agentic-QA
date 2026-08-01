#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <immutable-image-tag>" >&2
  exit 2
fi

IMAGE_TAG="$1"
AWS_PROFILE="${AWS_PROFILE:-sec-qa}"
AWS_REGION="${AWS_REGION:-us-east-1}"
TF_DIR="${TF_DIR:-infrastructure/portfolio}"

export AWS_PROFILE AWS_REGION

terraform -chdir="$TF_DIR" init
terraform -chdir="$TF_DIR" fmt -check
terraform -chdir="$TF_DIR" validate
terraform -chdir="$TF_DIR" plan \
  -var="api_image_tag=$IMAGE_TAG" \
  -out=day12.tfplan
terraform -chdir="$TF_DIR" apply day12.tfplan
