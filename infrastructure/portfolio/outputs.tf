output "raw_bucket_name" {
  description = "Immutable raw SEC filing bucket."
  value       = aws_s3_bucket.raw.bucket
}

output "curated_bucket_name" {
  description = "Parsed and enriched filing bucket."
  value       = aws_s3_bucket.curated.bucket
}

output "ingestion_queue_url" {
  description = "URL of the EDGAR ingestion queue."
  value       = aws_sqs_queue.ingestion.url
}

output "ingestion_dlq_url" {
  description = "URL of the ingestion dead-letter queue."
  value       = aws_sqs_queue.ingestion_dlq.url
}

output "ecr_repository_url" {
  description = "Container repository URL."
  value       = aws_ecr_repository.application.repository_url
}

output "ecs_task_execution_role_arn" {
  value = aws_iam_role.ecs_task_execution.arn
}

output "ingestion_task_role_arn" {
  value = aws_iam_role.ingestion_task.arn
}
