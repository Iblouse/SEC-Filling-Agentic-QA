variable "aws_region" {
  description = "AWS Region for the portfolio environment."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Lowercase project identifier used in resource names."
  type        = string
  default     = "sec-filing-agentic-qa"

  validation {
    condition     = can(regex("^[a-z0-9-]{3,32}$", var.project_name))
    error_message = "project_name must contain 3 to 32 lowercase letters, numbers, or hyphens."
  }
}

variable "owner" {
  description = "Resource owner tag."
  type        = string
  default     = "ibrahima"
}

variable "log_retention_days" {
  description = "CloudWatch log retention period."
  type        = number
  default     = 14

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365], var.log_retention_days)
    error_message = "Use a CloudWatch-supported retention value."
  }
}

variable "force_destroy_buckets" {
  description = "Allow Terraform destroy to remove non-empty portfolio buckets."
  type        = bool
  default     = true
}

variable "enable_monthly_budget" {
  description = "Create an AWS monthly cost budget and email alerts."
  type        = bool
  default     = false
}

variable "monthly_budget_usd" {
  description = "Monthly budget threshold in USD."
  type        = number
  default     = 25
}

variable "budget_email" {
  description = "Email address for budget alerts. Required when enable_monthly_budget is true."
  type        = string
  default     = ""

  validation {
    condition     = !var.enable_monthly_budget || can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", var.budget_email))
    error_message = "Provide a valid budget_email when enable_monthly_budget is true."
  }
}
