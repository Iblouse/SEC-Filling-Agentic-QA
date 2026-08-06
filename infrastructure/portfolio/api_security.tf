resource "aws_secretsmanager_secret" "api_key" {
  name                    = "${var.project_name}/api/key"
  description             = "API key used to protect SEC QA answer and feedback endpoints."
  recovery_window_in_days = var.api_key_recovery_window_days

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-api-key"
  })
}

data "aws_iam_policy_document" "api_execution_secret_read" {
  statement {
    sid       = "ReadApiKeySecret"
    effect    = "Allow"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [aws_secretsmanager_secret.api_key.arn]
  }
}

resource "aws_iam_role_policy" "api_execution_secret_read" {
  name   = "${var.project_name}-api-secret-read"
  role   = aws_iam_role.ecs_task_execution.id
  policy = data.aws_iam_policy_document.api_execution_secret_read.json
}
