resource "aws_ssm_parameter" "api_image_tag" {
  name        = "/${var.project_name}/api/image-tag"
  description = "Latest image tag accepted by the SEC QA deployment smoke test."
  type        = "String"
  value       = var.api_image_tag

  lifecycle {
    ignore_changes = [value]
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-api-image-tag"
  })
}

data "aws_ssm_parameter" "api_image_tag" {
  name       = aws_ssm_parameter.api_image_tag.name
  depends_on = [aws_ssm_parameter.api_image_tag]
}
