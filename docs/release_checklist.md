# v1.0 Release Checklist

## Repository hygiene

- [ ] `sec-venv/` is removed from Git tracking.
- [ ] `.env`, local data, Terraform state, `terraform.tfvars`, plans, credentials, and API keys are not tracked.
- [ ] `git status -sb` is clean.
- [ ] The repository name and description use the intended spelling of `Filing`.

## Quality

- [ ] `make check` passes.
- [ ] Terraform formatting passes.
- [ ] Terraform validation passes.
- [ ] The production Docker image builds.
- [ ] GitHub CI passes on the release commit.

## Infrastructure recovery

- [ ] Terraform refresh detects the current AWS state.
- [ ] The ECS cluster exists.
- [ ] The ECS service exists and is `ACTIVE`.
- [ ] The service is at desired count zero before deployment.
- [ ] CloudFront, ALB, target group, feedback table, secret, log group, ECR repository, and deployment role exist.

## Secure deployment

- [ ] The GitHub `production` Environment contains required variables and API-key secret.
- [ ] The OIDC deployment workflow succeeds.
- [ ] An unauthenticated answer request returns 401.
- [ ] A protected Bank of America request returns a non-abstained answer with citations.
- [ ] Feedback returns HTTP 201 and is present in DynamoDB.
- [ ] CloudWatch records the request ID and metrics.
- [ ] The accepted image tag is stored in SSM.
- [ ] The workflow returns ECS desired count to zero.

## Portfolio evidence

- [ ] README architecture renders correctly.
- [ ] Evaluation metrics match machine-readable summary files.
- [ ] Known limitations are visible.
- [ ] Three-minute demo succeeds.
- [ ] Resume bullets and interview walkthrough are reviewed.

## Release

- [ ] Commit message: `Package SEC QA portfolio release`.
- [ ] The commit is pushed to `main`.
- [ ] CI and deployment workflow both show success.
- [ ] Annotated tag `v1.0.0` is created and pushed.
- [ ] Repository visibility is changed only after the security review is complete.
