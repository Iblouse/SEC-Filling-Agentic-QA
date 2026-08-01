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

REPOSITORY_URL="$(terraform -chdir="$TF_DIR" output -raw ecr_repository_url)"
REGISTRY="${REPOSITORY_URL%%/*}"

aws ecr get-login-password --region "$AWS_REGION" |
  docker login --username AWS --password-stdin "$REGISTRY"

docker buildx build \
  --platform linux/amd64 \
  -f Dockerfile.api \
  -t "$REPOSITORY_URL:$IMAGE_TAG" \
  --push \
  .

printf 'Pushed %s:%s\n' "$REPOSITORY_URL" "$IMAGE_TAG"
printf 'Deploy with: terraform -chdir=%s apply -var="api_image_tag=%s"\n' \
  "$TF_DIR" "$IMAGE_TAG"
