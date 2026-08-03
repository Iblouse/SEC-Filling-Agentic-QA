output "api_feedback_table_name" {
  value = aws_dynamodb_table.api_feedback.name
}

output "api_metrics_namespace" {
  value = var.api_metrics_namespace
}

output "api_dashboard_name" {
  value = aws_cloudwatch_dashboard.api.dashboard_name
}

output "project_name" {
  value = var.project_name
}
