variable "api_edge_enabled" {
  description = "Expose the API through CloudFront HTTPS and restrict the ALB to CloudFront origins."
  type        = bool
  default     = true
}

variable "api_disable_docs" {
  description = "Disable Swagger, ReDoc, and OpenAPI routes in the deployed API."
  type        = bool
  default     = true
}

variable "api_key_recovery_window_days" {
  description = "Secrets Manager recovery window for the API-key secret."
  type        = number
  default     = 7

  validation {
    condition = (
      var.api_key_recovery_window_days == 0 ||
      (
        var.api_key_recovery_window_days >= 7 &&
        var.api_key_recovery_window_days <= 30
      )
    )
    error_message = "api_key_recovery_window_days must be 0 or between 7 and 30."
  }
}

variable "github_actions_enabled" {
  description = "Create the GitHub Actions OIDC provider and deployment role."
  type        = bool
  default     = false
}

variable "github_repository" {
  description = "GitHub repository in OWNER/REPOSITORY format."
  type        = string
  default     = ""

  validation {
    condition = (
      !var.github_actions_enabled ||
      can(regex("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", var.github_repository))
    )
    error_message = "github_repository must use OWNER/REPOSITORY format when GitHub Actions is enabled."
  }
}

variable "github_environment" {
  description = "GitHub Environment allowed to assume the AWS deployment role."
  type        = string
  default     = "production"
}

variable "github_oidc_provider_arn" {
  description = "Existing GitHub OIDC provider ARN. Leave empty to create one."
  type        = string
  default     = ""
}
