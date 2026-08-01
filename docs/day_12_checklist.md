# Day 12 completion checklist

- [ ] Day 11 tests and `make check` pass.
- [ ] Runtime corpus and embedding cache have equal line counts.
- [ ] Runtime files and manifest are uploaded to the curated S3 bucket.
- [ ] A unique Linux/AMD64 API image is pushed to ECR.
- [ ] `terraform fmt -check` and `terraform validate` pass.
- [ ] Terraform creates the VPC, ALB, ECS cluster, task definition, and service.
- [ ] The ECS service reaches steady state with one running task.
- [ ] The ALB target reports healthy.
- [ ] `/healthz` and `/readyz` return HTTP 200 through the ALB.
- [ ] A real Citigroup question succeeds through the ALB.
- [ ] The response contains citations from CIK 0000831001.
- [ ] CloudWatch contains startup and request logs with request IDs.
- [ ] The task definition uses separate execution and task roles.
- [ ] The task role can read only the runtime S3 prefix and invoke required Bedrock APIs.
- [ ] No AWS profile, credentials, corpus, or embeddings are baked into the image.
- [ ] Deployment cost and teardown commands are documented.
- [ ] Day 12 code and Terraform are committed and pushed.
