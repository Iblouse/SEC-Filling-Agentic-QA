# Apply Day 13

From the repository root, copy the Day 13 patch contents into the repository, then run:

```bash
chmod +x scripts/pause_day13_api.sh \
  scripts/resume_day13_api.sh \
  scripts/status_day13_api.sh \
  scripts/smoke_test_day13.sh

python -m pip install -e ".[dev]"
ruff check src tests --fix
ruff format src tests
make check

terraform -chdir=infrastructure/portfolio fmt
terraform -chdir=infrastructure/portfolio init
terraform -chdir=infrastructure/portfolio validate
```

The ECS service may remain at desired count zero while the new image and infrastructure are deployed. Resume it only for validation.
