resource "aws_dynamodb_table" "api_feedback" {
  name         = "${var.project_name}-feedback"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "request_id"
  range_key    = "feedback_id"

  attribute {
    name = "request_id"
    type = "S"
  }

  attribute {
    name = "feedback_id"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = var.api_feedback_enable_pitr
  }

  server_side_encryption {
    enabled = true
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-feedback"
  })
}

data "aws_iam_policy_document" "api_feedback_write" {
  statement {
    sid       = "WriteUserFeedback"
    effect    = "Allow"
    actions   = ["dynamodb:PutItem"]
    resources = [aws_dynamodb_table.api_feedback.arn]
  }
}

resource "aws_iam_role_policy" "api_feedback_write" {
  name   = "${var.project_name}-api-feedback-write"
  role   = aws_iam_role.api_task.id
  policy = data.aws_iam_policy_document.api_feedback_write.json
}
