#!/usr/bin/env bash
set -euo pipefail

python -m edgar_qa.semantic_cli verify-bedrock
python -m edgar_qa.semantic_cli build-embeddings
python -m edgar_qa.semantic_cli evaluate
python -m edgar_qa.semantic_cli compare
