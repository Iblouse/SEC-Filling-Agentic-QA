# Day 2: AWS foundation

## Objective

Create one reproducible AWS portfolio environment for ingestion and future application deployment.

## Tasks

- [ ] Install or confirm Terraform and AWS CLI.
- [ ] Confirm the AWS identity with `aws sts get-caller-identity`.
- [ ] Copy the Day 2 patch into the repository.
- [ ] Review `terraform.tfvars.example` and create `terraform.tfvars`.
- [ ] Run `terraform init`.
- [ ] Run `terraform fmt -recursive`.
- [ ] Run `terraform validate`.
- [ ] Review `terraform plan` before applying.
- [ ] Apply the stack.
- [ ] Save Terraform outputs under the ignored `data/` directory.
- [ ] Verify bucket security, versioning, encryption, queue redrive configuration, and ECR settings.
- [ ] Upload and retrieve one smoke-test object.
- [ ] Send one valid ingestion message to SQS.
- [ ] Commit configuration, documentation, and `.terraform.lock.hcl`, but not state or credentials.

## Completion criterion

Day 2 is complete when the infrastructure can be created from a clean checkout, all Terraform validation steps pass, the two S3 buckets accept a smoke-test object, the SQS queue accepts a filing message, and no Terraform state or credentials are tracked by Git.

## Evidence to retain

- `terraform plan` summary
- Terraform output names, without credentials
- Screenshot of the AWS resource tags
- Screenshot of the SQS redrive policy
- Screenshot or saved output of S3 versioning and public-access settings
- Git commit hash
