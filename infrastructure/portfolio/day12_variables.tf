



variable "api_image_tag" {
  description = "Immutable ECR image tag deployed by the API service."
  type        = string
  default     = "day12"
}

variable "api_artifact_prefix" {
  description = "Curated-bucket prefix containing the API runtime manifest and files."
  type        = string
  default     = "runtime/api"
}

variable "api_vpc_cidr" {
  description = "CIDR block for the portfolio API VPC."
  type        = string
  default     = "10.42.0.0/16"
}

variable "api_ingress_cidrs" {
  description = "IPv4 CIDRs allowed to reach the public HTTP listener."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "api_container_port" {
  description = "FastAPI container and target-group port."
  type        = number
  default     = 8080
}

variable "api_cpu" {
  description = "Fargate task CPU units."
  type        = number
  default     = 1024
}

variable "api_memory" {
  description = "Fargate task memory in MiB."
  type        = number
  default     = 2048
}

variable "api_desired_count" {
  description = "Number of API tasks maintained by ECS."
  type        = number
  default     = 1
}

variable "api_candidate_k" {
  description = "Hybrid candidates generated for each API question."
  type        = number
  default     = 20
}

variable "api_rerank_candidates" {
  description = "Hybrid candidates sent to Bedrock reranking."
  type        = number
  default     = 10
}

variable "api_evidence_k" {
  description = "Final SEC evidence chunks passed to the QA workflow."
  type        = number
  default     = 5
}

variable "api_enable_container_insights" {
  description = "Enable ECS Container Insights. Disabled by default for cost control."
  type        = bool
  default     = false
}
