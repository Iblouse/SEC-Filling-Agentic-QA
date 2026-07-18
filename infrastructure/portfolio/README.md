# Portfolio AWS foundation

This Terraform stack creates the first shared AWS infrastructure slice:

- Raw and curated S3 buckets
- S3 public-access blocking, versioning, ownership enforcement, and explicit SSE-S3 encryption
- SQS ingestion queue and dead-letter queue
- ECR repository with immutable tags and scan-on-push
- CloudWatch log groups
- ECS execution role
- Minimum-permission ingestion task role
- Optional monthly AWS budget

It intentionally does not create OpenSearch, Bedrock resources, ECS services, Cognito, or Step Functions yet.

## Prerequisites

- AWS CLI configured with an IAM identity permitted to create these resources
- Terraform 1.9 or later
- One AWS portfolio environment

## Deploy

```bash
cd infrastructure/portfolio
cp terraform.tfvars.example terraform.tfvars

aws sts get-caller-identity
terraform init
terraform fmt -recursive
terraform validate
terraform plan -out=portfolio.tfplan
terraform apply portfolio.tfplan
```

Save the output values:

```bash
terraform output
terraform output -json > ../../data/infrastructure-outputs.json
```

The output file belongs in `data/`, which is excluded from Git.

## Verify

```bash
RAW_BUCKET=$(terraform output -raw raw_bucket_name)
CURATED_BUCKET=$(terraform output -raw curated_bucket_name)
QUEUE_URL=$(terraform output -raw ingestion_queue_url)
ECR_URL=$(terraform output -raw ecr_repository_url)

aws s3api get-public-access-block --bucket "$RAW_BUCKET"
aws s3api get-bucket-versioning --bucket "$RAW_BUCKET"
aws s3api get-bucket-encryption --bucket "$RAW_BUCKET"

aws s3api get-public-access-block --bucket "$CURATED_BUCKET"
aws s3api get-bucket-versioning --bucket "$CURATED_BUCKET"

aws sqs get-queue-attributes \
  --queue-url "$QUEUE_URL" \
  --attribute-names All

aws ecr describe-repositories \
  --repository-names sec-filing-agentic-qa
```

## Smoke test storage and queue

```bash
printf '{"status":"day-02-smoke-test"}\n' > /tmp/sec-qa-smoke.json
aws s3 cp /tmp/sec-qa-smoke.json "s3://$RAW_BUCKET/smoke/day-02.json"
aws s3 cp "s3://$RAW_BUCKET/smoke/day-02.json" -

aws sqs send-message \
  --queue-url "$QUEUE_URL" \
  --message-body '{"cik":"0000019617","forms":["10-K","10-Q","8-K"]}'
```

## Destroy

```bash
terraform plan -destroy -out=destroy.tfplan
terraform apply destroy.tfplan
```

The portfolio defaults allow Terraform to delete non-empty buckets. Change `force_destroy_buckets` to `false` when you no longer need fast teardown.
