output "api_public_base_url" {
  value = (
    var.api_edge_enabled
    ? "https://${aws_cloudfront_distribution.api[0].domain_name}"
    : "http://${aws_lb.api.dns_name}"
  )
}

output "api_cloudfront_distribution_id" {
  value = (
    var.api_edge_enabled
    ? aws_cloudfront_distribution.api[0].id
    : null
  )
}

output "api_key_secret_arn" {
  value = aws_secretsmanager_secret.api_key.arn
}

output "github_deploy_role_arn" {
  value = (
    var.github_actions_enabled
    ? aws_iam_role.github_deploy[0].arn
    : null
  )
}

output "api_image_tag_parameter_name" {
  value = aws_ssm_parameter.api_image_tag.name
}

