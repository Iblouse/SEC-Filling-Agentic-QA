# Security and Cost Controls

## Authentication and secret handling

- Protected API routes require `X-API-Key`.
- The key is generated locally, stored in AWS Secrets Manager, and injected into ECS through the task-definition `secrets` field.
- The key is not stored in Terraform variables, Git history, image layers, or task-definition plaintext environment fields.
- Updating a secret requires a new ECS task because running containers do not reload secret values automatically.

## Network boundary

- CloudFront is the public HTTPS endpoint.
- The ALB accepts origin-facing CloudFront traffic.
- The Fargate task accepts only ALB traffic on the container port.
- Health and readiness endpoints remain unauthenticated for infrastructure checks.
- Answer and feedback routes are protected.

## CI/CD identity

- GitHub Actions requests a short-lived AWS session through OIDC.
- The role trust is restricted to the configured repository and `production` GitHub Environment.
- The deployment role can push to the project ECR repository, register task definitions, update the project ECS service, pass only the API roles, and update the project image-tag parameter.
- The workflow does not use permanent AWS access keys.

## Cost controls

- `api_desired_count` defaults to zero.
- The deployment workflow starts one Fargate task for validation and returns it to zero unless `leave_running=true` is explicitly selected.
- `scripts/demo.sh` installs a cleanup trap that attempts to return the service to zero even when a smoke test fails.
- DynamoDB uses on-demand billing and TTL.
- Runtime artifacts remain in S3 and container images remain in ECR.

## Resources that may still charge while ECS is paused

- Application Load Balancer hourly and LCU charges
- Public IPv4 addresses
- Secrets Manager secret storage
- CloudWatch logs, custom metrics, dashboard, and alarms
- S3 and ECR storage
- DynamoDB storage and requests
- CloudFront requests and data transfer
- Bedrock model requests when the API or evaluation commands are used

## Operational rule

Before ending a demo or deployment session, verify:

```text
desired: 0
running: 0
pending: 0
```
