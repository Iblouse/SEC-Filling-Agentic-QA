# Infrastructure

Terraform will be added after the local ingestion vertical slice works.

Planned modules:

```text
infrastructure/
  modules/
    storage/
    queue/
    container_service/
    search/
    identity/
    monitoring/
  environments/
    dev/
    prod/
```

The first deployed slice will create S3 raw and curated buckets, an SQS work queue and dead-letter queue, an ECR repository, CloudWatch logs, and minimum-permission IAM roles.
