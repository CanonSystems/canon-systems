# NOT wired into infra/terraform/main.tf (Precedent §1 cloud_execution_deferred waiver).

variable "name_prefix" {
  type        = string
  description = "Prefix for synthesized resource names."
  default     = ""
}

variable "vault_bucket_arn" {
  type        = string
  description = "ARN of the synthesis-vault bucket (read-only policy)."
  default     = ""
}

variable "vault_bucket_name" {
  type        = string
  description = "Bucket name for SYNTHESIS_WEB_BUCKET."
  default     = ""
}

variable "vault_prefix" {
  type        = string
  description = "S3 prefix for vault roots (SYNTHESIS_WEB_PREFIX)."
  default     = "vault"
}

variable "company_shorthash" {
  type        = string
  description = "Optional 8-char hex scope for ListBucket condition (may be empty for all-tenant)."
  default     = ""
}

variable "repo_shorthash" {
  type        = string
  description = "Optional 8-char hex scope paired with company_shorthash."
  default     = ""
}

variable "domain" {
  type        = string
  description = "Optional future custom domain (not wired in this stub)."
  default     = ""
}

variable "lambda_package_path" {
  type        = string
  description = "Path to deployment zip for aws_lambda_function.filename."
  default     = ""
}

variable "lambda_package_hash" {
  type        = string
  description = "Source code hash for aws_lambda_function.source_code_hash."
  default     = ""
}
