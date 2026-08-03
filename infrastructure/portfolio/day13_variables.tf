variable "api_feedback_ttl_days" {
  description = "Days before DynamoDB automatically expires feedback records."
  type        = number
  default     = 90

  validation {
    condition     = var.api_feedback_ttl_days >= 1 && var.api_feedback_ttl_days <= 365
    error_message = "api_feedback_ttl_days must be between 1 and 365."
  }
}

variable "api_feedback_enable_pitr" {
  description = "Enable DynamoDB point-in-time recovery for the feedback table."
  type        = bool
  default     = false
}

variable "api_metrics_namespace" {
  description = "CloudWatch namespace for SEC QA embedded metrics."
  type        = string
  default     = "SECQA"
}

variable "api_environment" {
  description = "Low-cardinality environment dimension for API metrics."
  type        = string
  default     = "portfolio"
}

variable "api_alarm_sns_topic_arn" {
  description = "Optional SNS topic ARN for CloudWatch alarm notifications."
  type        = string
  default     = ""
}
