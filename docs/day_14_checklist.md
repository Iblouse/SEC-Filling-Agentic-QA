# Day 14 Completion Checklist

- [ ] Python API-key tests pass.
- [ ] Terraform formatting and validation pass.
- [ ] CloudFront distribution is deployed.
- [ ] ALB ingress is restricted to the CloudFront origin-facing prefix list.
- [ ] Secrets Manager contains an API-key version.
- [ ] ECS task definition injects `QA_API_KEY` through `secrets`.
- [ ] Direct ALB access fails.
- [ ] CloudFront `/healthz` and `/readyz` return 200.
- [ ] `/v1/answer` without a key returns 401.
- [ ] `/v1/answer` with a valid key returns cited Bank of America evidence.
- [ ] `/v1/feedback` with a valid key returns 201.
- [ ] GitHub OIDC role trust is repository-and-environment scoped.
- [ ] The accepted image tag is recorded in SSM Parameter Store.
- [ ] GitHub CI succeeds.
- [ ] Manual GitHub deployment succeeds.
- [ ] Deployment returns ECS desired count to zero.
- [ ] Day 14 changes are committed and pushed.
