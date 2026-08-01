output "api_cluster_name" {
  value = aws_ecs_cluster.api.name
}

output "api_service_name" {
  value = aws_ecs_service.api.name
}

output "api_task_role_arn" {
  value = aws_iam_role.api_task.arn
}

output "api_load_balancer_dns_name" {
  value = aws_lb.api.dns_name
}

output "api_base_url" {
  value = "http://${aws_lb.api.dns_name}"
}

output "api_artifact_manifest_s3_uri" {
  value = "s3://${aws_s3_bucket.curated.bucket}/${var.api_artifact_prefix}/manifest.json"
}

output "api_target_group_arn" {
  value = aws_lb_target_group.api.arn
}

output "api_task_definition_arn" {
  value = aws_ecs_task_definition.api.arn
}
