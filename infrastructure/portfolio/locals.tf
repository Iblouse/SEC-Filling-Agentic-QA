locals {
  account_id = data.aws_caller_identity.current.account_id
  region     = var.aws_region
  name_base  = "${var.project_name}-${local.account_id}-${local.region}"

  common_tags = {
    Project     = var.project_name
    Environment = "portfolio"
    Owner       = var.owner
    ManagedBy   = "terraform"
  }
}
