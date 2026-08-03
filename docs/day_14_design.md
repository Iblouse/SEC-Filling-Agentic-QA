# Day 14 Design: CI/CD and Public API Security

## Security boundary

The public API is exposed through the CloudFront default HTTPS domain.
CloudFront forwards dynamic API requests without caching. The Application
Load Balancer security group accepts port 80 only from the AWS-managed
CloudFront origin-facing prefix list, preventing direct public access to the
ALB.

`/healthz` and `/readyz` remain unauthenticated for container, ALB, and
deployment checks. `/v1/answer` and `/v1/feedback` require `X-API-Key`.

The API key is stored in AWS Secrets Manager and injected into the ECS
container through the task definition `secrets` field. It is not present in
Terraform variables, Git history, task-definition environment fields, or
Docker image layers.

## Delivery boundary

Pull requests and pushes run Python checks, Terraform validation, and a
production Docker build.

Production deployment is manual through a protected GitHub Environment.
GitHub exchanges an OIDC token for short-lived AWS credentials. The role
trust policy accepts only the configured repository and environment.

The latest successfully smoke-tested image tag is recorded in one SSM
Parameter Store parameter. This prevents a later Terraform apply from
reverting the service to an older image tag.

The deployment role can push to the project ECR repository, register an ECS
task definition, update the project ECS service, and pass only the API task
and execution roles. It cannot administer IAM or deploy unrelated services.

## Cost behavior

Terraform keeps `api_desired_count = 0`. A deployment workflow starts one
task for validation and returns the service to zero unless the operator
explicitly selects `leave_running`.
