#!/usr/bin/env bash
set -euo pipefail

AWS_PROFILE="${AWS_PROFILE:-sec-qa}"
AWS_REGION="${AWS_REGION:-us-east-1}"
TF_DIR="${TF_DIR:-infrastructure/portfolio}"
ARTIFACT_PREFIX="${API_ARTIFACT_PREFIX:-runtime/api}"
CORPUS_PATH="${QA_CORPUS_PATH:-data/retrieval/sec_chunks.jsonl}"
EMBEDDINGS_PATH="${QA_EMBEDDING_CACHE_PATH:-data/retrieval/titan_v2_512_embeddings.jsonl}"

export AWS_PROFILE AWS_REGION

for path in "$CORPUS_PATH" "$EMBEDDINGS_PATH"; do
  if [[ ! -f "$path" ]]; then
    echo "Missing runtime artifact: $path" >&2
    exit 1
  fi
done

BUCKET="$(terraform -chdir="$TF_DIR" output -raw curated_bucket_name)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
MANIFEST="$TMP_DIR/manifest.json"

python - "$CORPUS_PATH" "$EMBEDDINGS_PATH" "$ARTIFACT_PREFIX" "$MANIFEST" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

corpus = Path(sys.argv[1])
embeddings = Path(sys.argv[2])
prefix = sys.argv[3].strip("/")
manifest_path = Path(sys.argv[4])


def describe(path: Path, key: str) -> dict[str, object]:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return {
        "key": key,
        "sha256": digest.hexdigest(),
        "bytes": path.stat().st_size,
    }

payload = {
    "schema_version": 1,
    "corpus": describe(corpus, f"{prefix}/sec_chunks.jsonl"),
    "embeddings": describe(
        embeddings,
        f"{prefix}/titan_v2_512_embeddings.jsonl",
    ),
}
manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY

aws s3 cp "$CORPUS_PATH" "s3://$BUCKET/$ARTIFACT_PREFIX/sec_chunks.jsonl" \
  --only-show-errors
aws s3 cp "$EMBEDDINGS_PATH" \
  "s3://$BUCKET/$ARTIFACT_PREFIX/titan_v2_512_embeddings.jsonl" \
  --only-show-errors
# Upload the manifest last so a task never observes it before both files exist.
aws s3 cp "$MANIFEST" "s3://$BUCKET/$ARTIFACT_PREFIX/manifest.json" \
  --content-type application/json \
  --only-show-errors

printf 'Uploaded Day 12 runtime artifacts to s3://%s/%s/\n' "$BUCKET" "$ARTIFACT_PREFIX"
cat "$MANIFEST"
