# Day 13 Completion Checklist

- [ ] Day 13 patch applied without overwriting local retrieval artifacts
- [ ] `make check` passes
- [ ] Terraform formatting and validation pass
- [ ] DynamoDB feedback table exists in `PAY_PER_REQUEST` mode
- [ ] DynamoDB TTL is enabled on `expires_at`
- [ ] API task role can call `dynamodb:PutItem` only on the feedback table
- [ ] New Docker image is pushed to ECR
- [ ] Terraform deploys the new task definition and CloudWatch alarms
- [ ] `/v1/answer` returns a non-abstained Bank of America answer with citations
- [ ] `/v1/feedback` returns HTTP 201 and `status=accepted`
- [ ] Feedback item is visible in DynamoDB
- [ ] CloudWatch receives request, answer, and feedback EMF metrics
- [ ] CloudWatch dashboard exists
- [ ] Alarm resources exist; metric alarms begin receiving data after test traffic
- [ ] `pause_day13_api.sh` produces desired=0 and running=0
- [ ] Day 13 changes are committed and pushed
