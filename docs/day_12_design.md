# Day 12 design: ECR, ECS/Fargate, ALB, CloudWatch, and S3 runtime artifacts

## Deployment path

1. Upload the corpus and Titan embedding cache to the existing versioned curated S3 bucket.
2. Upload a manifest last. It records the S3 keys, byte counts, and SHA-256 digests.
3. Build a Linux/AMD64 image and push it to the existing immutable ECR repository.
4. Terraform creates a dedicated VPC, two public subnets, an internet-facing ALB, an ECS cluster, a Fargate task definition, and an ECS service.
5. At startup, the API task downloads exactly the files named in the manifest and verifies both checksums before loading the retrieval indexes.
6. The ALB calls `/readyz`; traffic reaches the task only after the corpus, embedding cache, and AWS clients initialize successfully.

## IAM separation

- The ECS task execution role lets the Fargate agent pull from ECR and publish container logs to CloudWatch.
- The API task role is available to application code. It can read only the runtime-artifact prefix from the curated S3 bucket and call the required Bedrock embedding, reranking, and Nova inference resources.

## Networking and cost tradeoff

The portfolio deployment uses public subnets and assigns a public IP to the Fargate task. The task security group accepts port 8080 only from the ALB security group. This avoids the recurring cost of a NAT gateway while preserving a controlled inbound path. A production enterprise deployment would normally use private subnets and VPC endpoints or NAT according to organizational requirements.

## Artifact consistency

The manifest is uploaded after both data files. The container downloads each file to a temporary path, validates byte count and SHA-256, and atomically renames it. A mismatch leaves the API not ready rather than silently serving stale or mixed retrieval artifacts.

## Availability scope

Day 12 maintains one task for cost control and uses two subnets so the ALB spans two Availability Zones. A higher-availability deployment should run at least two tasks and should add HTTPS through ACM before public use.
