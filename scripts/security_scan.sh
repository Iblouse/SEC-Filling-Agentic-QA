#!/usr/bin/env bash
set -euo pipefail

patterns='AKIA[0-9A-Z]{16}|aws_secret_access_key|BEGIN (RSA|OPENSSH|EC) PRIVATE KEY|QA_API_KEY=|SEC_QA_API_KEY='

if git ls-files sec-venv .venv | grep -q .; then
  echo "FAIL: a local virtual environment is tracked." >&2
  exit 1
fi

if git ls-files | grep -Eq '(^|/)(\.env|terraform\.tfstate|terraform\.tfvars|api-key|credentials)$'; then
  echo "FAIL: a local secret or Terraform state file is tracked." >&2
  exit 1
fi

if git grep -nEI "$patterns" -- . ':!docs' ':!*.example' ':!scripts/security_scan.sh'; then
  echo "FAIL: review potential credential material above." >&2
  exit 1
fi

echo "PASS: no obvious tracked credentials or local environments found."
