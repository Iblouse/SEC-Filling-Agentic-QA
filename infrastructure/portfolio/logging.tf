resource "aws_cloudwatch_log_group" "ingestion" {
  name              = "/${var.project_name}/ingestion"
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_group" "application" {
  name              = "/${var.project_name}/application"
  retention_in_days = var.log_retention_days
}
